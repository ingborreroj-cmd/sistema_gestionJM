import pandas as pd
from django.db import transaction
from django.db.models import Max, Sum
from decimal import Decimal, InvalidOperation
from datetime import date 
import logging
import re
import io
import os
from django.http import HttpResponse
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from django.conf import settings

# Asegúrate de que este archivo exista en tu estructura de carpetas:
from .constants import CATEGORY_CHOICES_MAP 
from .models import Recibo # Importación local necesaria para importar_recibos_desde_excel

logger = logging.getLogger(__name__)


# --- Funciones Auxiliares de Conversión ---

def to_boolean(value):
    """Convierte valores comunes de Excel (NaN, SI, X, 1, etc.) a Booleano."""
    if pd.isna(value):
        return False
    return str(value).strip().lower() in ['sí', 'si', 'true', '1', 'x', 'y'] 

def limpiar_y_convertir_decimal(value):
    """Limpia cualquier carácter no numérico y convierte a Decimal."""
    if pd.isna(value) or value is None:
        return Decimal(0)
    
    s = str(value).strip()
    if not s or s in ['-', 'n/a', 'no aplica']:
        return Decimal(0)

    s_limpio = re.sub(r'[^\d,\.]', '', s) 
    s_final = s_limpio.replace(',', '.')
    
    if s_final.count('.') > 1:
        partes = s_final.rsplit('.', 1) 
        s_final = partes[0].replace('.', '') + '.' + partes[1] 
    
    try:
        if not s_final:
            return Decimal(0)
        
        return Decimal(s_final)
    except InvalidOperation:
        logger.error(f"Error fatal de conversión de Decimal: '{s_final}' (original: '{value}')")
        return Decimal(0)

def format_currency(amount):
    """Formatea el monto como moneda (ej: 1.234,56)."""
    try:
        amount_decimal = Decimal(amount)
        # Formatea a 2 decimales, usa 'X' temporalmente para la coma, luego reemplaza
        return "{:,.2f}".format(amount_decimal).replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00" 

# --- Función de Carga/Importación (Se mantiene igual) ---

def importar_recibos_desde_excel(archivo_excel):
    # Ya importamos Recibo arriba
    RIF_COL = 'rif_cedula_identidad'

    try:
        COLUMNAS_CANONICAS = [
            'estado', 'nombre', RIF_COL, 'direccion_inmueble', 'ente_liquidado',
            'categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5',
            'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10',
            'gastos_administrativos', 'tasa_dia', 'total_monto_bs', 
            'numero_transferencia', 'conciliado', 'fecha', 'concepto' 
        ]
        
        df = pd.read_excel(
            archivo_excel, 
            sheet_name='Hoja2', 
            header=3, 
            nrows=1 
        )
        
        if df.empty:
             return False, "Error: El archivo Excel está vacío o la hoja 'Hoja2' no contiene datos en el rango esperado (Fila 5).", None

        fila_datos = df.iloc[0] 
        
        if len(fila_datos) != len(COLUMNAS_CANONICAS):
            return False, f"Error: Se encontraron {len(fila_datos)} valores, pero se esperaban {len(COLUMNAS_CANONICAS)}. El Excel tiene columnas vacías.", None
            
        fila_mapeada = dict(zip(COLUMNAS_CANONICAS, fila_datos.tolist()))
        
        rif_cedula_raw = str(fila_mapeada.get(RIF_COL, '')).strip()
        
        if not rif_cedula_raw:
             return False, "El registro no tiene RIF/Cédula y no se puede procesar.", None
            
        logger.info(f"ÉXITO EN LECTURA: Se encontró el registro con RIF: {rif_cedula_raw}")
        
        data_a_insertar = {}
        
        with transaction.atomic():
            ultimo_recibo = Recibo.objects.aggregate(Max('numero_recibo'))['numero_recibo__max']
            data_a_insertar['numero_recibo'] = (ultimo_recibo or 0) + 1
            
            data_a_insertar['estado'] = str(fila_mapeada.get('estado', '')).strip().upper() 
            data_a_insertar['nombre'] = str(fila_mapeada.get('nombre', '')).strip().title()
            data_a_insertar['rif_cedula_identidad'] = str(rif_cedula_raw).strip().replace('.', '').replace('-', '').replace(' ', '').upper()
            data_a_insertar['direccion_inmueble'] = str(fila_mapeada.get('direccion_inmueble', 'DIRECCION NO ESPECIFICADA')).strip().title()
            data_a_insertar['ente_liquidado'] = str(fila_mapeada.get('ente_liquidado', 'ENTE NO ESPECIFICADO')).strip().title()
            data_a_insertar['numero_transferencia'] = str(fila_mapeada.get('numero_transferencia', '')).strip().upper()
            data_a_insertar['concepto'] = str(fila_mapeada.get('concepto', '')).strip().title()
            
            for i in range(1, 11):
                 key = f'categoria{i}'
                 data_a_insertar[key] = to_boolean(fila_mapeada.get(key))

            data_a_insertar['conciliado'] = to_boolean(fila_mapeada.get('conciliado'))

            data_a_insertar['gastos_administrativos'] = limpiar_y_convertir_decimal(fila_mapeada.get('gastos_administrativos', 0))
            data_a_insertar['tasa_dia'] = limpiar_y_convertir_decimal(fila_mapeada.get('tasa_dia', 0))
            data_a_insertar['total_monto_bs'] = limpiar_y_convertir_decimal(fila_mapeada.get('total_monto_bs', 0))
            
            fecha_excel = fila_mapeada.get('fecha')
            
            if pd.isna(fecha_excel) or str(fecha_excel).strip() == "":
                 raise ValueError("El campo 'FECHA' es obligatorio y está vacío.") 
            
            if isinstance(fecha_excel, str) and fecha_excel.strip().upper() == 'FECHA':
                 raise ValueError("El campo 'FECHA' contiene la palabra 'FECHA'. Por favor, ingrese una fecha válida.")

            try:
                fecha_objeto = pd.to_datetime(fecha_excel, errors='raise')

                if pd.isna(fecha_objeto):
                    raise ValueError("Formato de fecha inválido.")
                
                data_a_insertar['fecha'] = fecha_objeto.date()
                
            except Exception as e:
                logger.error(f"Error al convertir fecha '{fecha_excel}': {e}")
                raise ValueError(f"Formato de fecha no reconocido para el valor: {fecha_excel}. Use formatos estándar.")


            recibo_creado = Recibo.objects.create(**data_a_insertar)
            
            return True, f"Se generó el recibo N° {recibo_creado.numero_recibo} para {data_a_insertar['nombre']} exitosamente. Listo para PDF.", recibo_creado.pk

    except Exception as e:
        logger.error(f"FALLO DE VALIDACIÓN en el registro: {e}")
        return False, f"Fallo en la carga: Error de validación de datos (revisar consola): {str(e)}", None
    
# --- Generador de Reporte Excel (Final y Corregido) ---

def generar_reporte_excel(request_filters, queryset, filtros_aplicados): 
    """
    Genera un reporte Excel (.xlsx) con dos hojas: 'Recibos' (datos detallados, sin totales) e 
    'info_reporte' (metadatos de filtrado y totales).
    """
    # 1. Preparar la Hoja 'Recibos' (Datos Detallados)
    data = []
    
    # 9 Columnas requeridas: Concepto y Categorías separadas
    headers = [
        'Número Recibo', 
        'Nombre', 
        'Cédula/RIF', 
        'Fecha', 
        'Estado', 
        'Monto Total (Bs.)',       
        'N° Transferencia', 
        'Concepto',                
        'Categorías'               
    ]
    
    for recibo in queryset:
        
        # Obtiene los nombres legibles de las categorías activas
        categoria_detalle_nombres = []
        for i in range(1, 11):
            field_name = f'categoria{i}'
            
            if getattr(recibo, field_name):
                 nombre_categoria = CATEGORY_CHOICES_MAP.get(field_name, f'Categoría {i} (Desconocida)')
                 categoria_detalle_nombres.append(nombre_categoria)
        
        categorias_concatenadas = ', '.join(categoria_detalle_nombres)

        row = [
            recibo.numero_recibo,
            recibo.nombre,
            recibo.rif_cedula_identidad,
            recibo.fecha.strftime('%Y-%m-%d'),
            recibo.estado,
            recibo.total_monto_bs,             
            recibo.numero_transferencia,
            recibo.concepto.strip(),           
            categorias_concatenadas            
        ]
        data.append(row)

    # 2. Preparar la Hoja 'info_reporte' (Metadatos y Totales)
    
    total_registros = queryset.count()
    total_monto_bs = queryset.aggregate(total=Sum('total_monto_bs'))['total'] or Decimal(0)
    
    info_data = [
        ['Fecha de Generación', timezone.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['Período del Reporte', filtros_aplicados.get('periodo', 'Todos los períodos')],
        ['Estado Filtrado', filtros_aplicados.get('estado', 'Todos los estados')],
        ['Categorías Filtradas', filtros_aplicados.get('categorias', 'Todas las categorías')],
        ['Total de Registros', total_registros],
        ['Monto Total (Bs)', total_monto_bs], 
    ]
    info_df = pd.DataFrame(info_data, columns=['Parámetro', 'Valor'])

    # 3. Generar el Archivo Excel
    
    df_recibos = pd.DataFrame(data, columns=headers)
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # --- Hoja 1: info_reporte ---
        info_df.to_excel(writer, index=False, sheet_name='info_reporte')
        
        # --- Hoja 2: Recibos ---
        df_recibos.to_excel(writer, index=False, sheet_name='Recibos', startrow=0, header=True)
        
        # --- Aplicar Formato a la Hoja 'Recibos' ---
        workbook = writer.book
        worksheet_recibos = writer.sheets['Recibos']
        
        money_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        bold_format = workbook.add_format({'bold': True, 'bg_color': '#EAEAEA'})
        
        # Ancho de columnas
        worksheet_recibos.set_column('A:A', 15) # 0: Número Recibo
        worksheet_recibos.set_column('B:C', 25) # 1: Nombre, 2: Cédula
        worksheet_recibos.set_column('D:D', 12) # 3: Fecha
        worksheet_recibos.set_column('E:E', 15) # 4: Estado
        worksheet_recibos.set_column('F:F', 18, money_format) # 5: Monto Total (Bs.)
        worksheet_recibos.set_column('G:G', 20) # 6: N° Transferencia
        worksheet_recibos.set_column('H:H', 40) # 7: Concepto
        worksheet_recibos.set_column('I:I', 50) # 8: Categorías
        
        # Formato para el encabezado (reiterar)
        for col_num, value in enumerate(headers):
            worksheet_recibos.write(0, col_num, value, bold_format)
            
        # ❌ Se ha eliminado la sección de 'TOTAL GENERAL' para la hoja Recibos
        
        # --- Aplicar Formato a la Hoja 'info_reporte' ---
        worksheet_info = writer.sheets['info_reporte']
        worksheet_info.set_column('A:A', 30) # Parámetro
        worksheet_info.set_column('B:B', 40) # Valor
        
        # Formato para el encabezado
        worksheet_info.write(0, 0, 'Parámetro', bold_format)
        worksheet_info.write(0, 1, 'Valor', bold_format)
    
    output.seek(0)
    
    # 4. Devolver la Respuesta HTTP
    filename = f"Reporte_Recibos_Masivo_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(
        output, 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# --- Configuración de Imagen para PDF ---

try:
    HEADER_IMAGE = os.path.join(
        settings.BASE_DIR, 
        'apps', 
        'recibos', 
        'static', 
        'recibos', 
        'images', 
        'encabezado.png' 
    )
except AttributeError:
    # Ruta alternativa para desarrollo o entornos sin settings.BASE_DIR
    HEADER_IMAGE = os.path.join(os.path.dirname(__file__), '..', 'static', 'recibos', 'images', 'encabezado.png')


# --- Generador de Reporte PDF (Final y Corregido) ---

# 🚀 CORRECCIÓN CLAVE: Se agregó 'filtros_aplicados' como argumento
def generar_pdf_reporte(queryset, filtros_aplicados):
    """
    Genera un reporte PDF masivo usando ReportLab con la estructura solicitada:
    Encabezado, Título, Filtros, Tabla de Datos y Resumen Final.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=80,  # Espacio para el encabezado/logo
        bottomMargin=36
    )
    
    Story = []
    styles = getSampleStyleSheet()
    
    # 1. Preparación de Datos y Totales
    total_registros = queryset.count()
    total_monto_bs = queryset.aggregate(total=Sum('total_monto_bs'))['total'] or Decimal(0)
    
    # Prepara los datos de la tabla (8 Columnas)
    table_data = []
    table_headers = [
        'Recibo', 'Nombre', 'Cédula/RIF', 'Estado', 'Fecha', 'Monto Total (Bs.)', 
        'N° Transf.', 'Concepto y Cat.' # Combinamos estos campos por limitación de espacio
    ]
    table_data.append(table_headers)
    
    col_widths = [45, 90, 75, 50, 60, 70, 40, 110] 
    
    for recibo in queryset:
        categoria_detalle_nombres = []
        for i in range(1, 11):
            field_name = f'categoria{i}'
            if getattr(recibo, field_name):
                 nombre_categoria = CATEGORY_CHOICES_MAP.get(field_name, f'Cat. {i}')
                 categoria_detalle_nombres.append(nombre_categoria)
        
        categorias_concatenadas = ', '.join(categoria_detalle_nombres)
        
        concepto_final = f"{recibo.concepto.strip()}"
        if categorias_concatenadas:
             concepto_final += f" (Cats: {categorias_concatenadas})"

        table_data.append([
            recibo.numero_recibo,
            recibo.nombre,
            recibo.rif_cedula_identidad,
            recibo.estado,
            recibo.fecha.strftime('%Y-%m-%d'),
            format_currency(recibo.total_monto_bs),
            recibo.numero_transferencia if recibo.numero_transferencia else '',
            concepto_final
        ])

    # 2. Función de Encabezado por Página
    
    def draw_report_header(canvas, doc, filtros_aplicados, total_registros, total_monto_bs):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        width, height = letter

        # --- A. Dibujar Encabezado PNG ---
        current_y = height - 50
        if os.path.exists(HEADER_IMAGE):
             try:
                 img = ImageReader(HEADER_IMAGE)
                 img_width, img_height = img.getSize()
                 scale = min(1.0, 480 / img_width) 
                 draw_width = img_width * scale
                 draw_height = img_height * scale
                 x_center = (width - draw_width) / 2
                 y_top = height - draw_height - 20
                 canvas.drawImage(HEADER_IMAGE, x=x_center, y=y_top, width=draw_width, height=draw_height)
                 current_y = y_top - 30
             except Exception:
                 current_y = height - 50 

        # --- B. Título Centrado ---
        titulo = "REPORTE DE RECIBOS DE PAGO"
        canvas.setFont("Helvetica-Bold", 12)
        text_width = canvas.stringWidth(titulo, "Helvetica-Bold", 12)
        canvas.drawString((width - text_width) / 2, current_y, titulo)
        current_y -= 25

        # --- C. Filtros Aplicados ---
        canvas.setFont('Helvetica-Bold', 10)
        
        # Fila 1: Período
        canvas.drawString(36, current_y, "PERÍODO:")
        canvas.setFont('Helvetica', 10)
        canvas.drawString(100, current_y, filtros_aplicados.get('periodo', 'Todos los períodos'))
        
        # Fila 2: Estado
        current_y -= 15
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(36, current_y, "ESTADO:")
        canvas.setFont('Helvetica', 10)
        canvas.drawString(100, current_y, filtros_aplicados.get('estado', 'Todos los estados'))
        
        # Fila 3: Categorías (Misma línea que Filtro, más corto)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(width / 2, current_y + 15, "CATEGORÍAS:")
        canvas.setFont('Helvetica', 10)
        cat_text = filtros_aplicados.get('categorias', 'Todas')
        if len(cat_text) > 40:
             cat_text = cat_text[:37] + '...' 
        canvas.drawString(width / 2 + 80, current_y + 15, cat_text)
        
        current_y -= 20
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(36, current_y, "Detalle de Recibos:")
        
        canvas.restoreState()
        
    # 3. Creación y Estilo de la Tabla
    
    table = Table(table_data, colWidths=col_widths)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (5, 1), (5, -1), 'RIGHT'), 
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8), 
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    
    Story.append(table)
    Story.append(Spacer(1, 12))

    
    # 4. Resumen Final (Totales del Reporte)
    
    Story.append(Paragraph("--- RESUMEN DEL REPORTE GENERADO ---", styles['h3']))
    Story.append(Spacer(1, 6))
    
    resumen_data = [
        ['Total Recibos:', total_registros],
        ['Monto Total (Bs):', format_currency(total_monto_bs)],
        ['Período:', filtros_aplicados.get('periodo', 'Todos')],
        ['Estado:', filtros_aplicados.get('estado', 'Todos')],
        ['Categorías:', filtros_aplicados.get('categorias', 'Todas')],
        ['Fecha del Reporte:', timezone.now().strftime('%d/%m/%Y %H:%M:%S')],
    ]
    
    resumen_table = Table(resumen_data, colWidths=[120, 420])
    resumen_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
    ]))
    
    Story.append(resumen_table)
    
    
    def my_header_callback(canvas, doc):
        draw_report_header(canvas, doc, filtros_aplicados, total_registros, total_monto_bs)

    doc.build(Story, onFirstPage=my_header_callback, onLaterPages=my_header_callback)
    
    buffer.seek(0)
    
    filename = f"Reporte_Recibos_PDF_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response = HttpResponse(
        buffer.getvalue(), 
        content_type='application/pdf'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response