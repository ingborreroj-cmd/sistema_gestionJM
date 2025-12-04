import pandas as pd
import io
import re
from datetime import datetime, date
from django.db import transaction, models
from django.utils import timezone
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.units import inch
from reportlab.lib import colors

# Importaciones del modelo (Asumiendo que están en la misma app)
from .models import Receipt

# ====================================================================
# Funciones Auxiliares para Limpieza y Conversión de Datos
# ====================================================================

def clean(value):
    """Limpia valores de Pandas: convierte NaN a None y maneja tipos."""
    if pd.isna(value) or value is None:
        return None
    # Eliminar espacios extra y convertir a cadena, excepto para números
    if isinstance(value, str):
        return value.strip()
    return value

def is_marked(value):
    """Verifica si un valor en la columna de categoría debe ser True (X, x, 1, True, Yes, etc.)."""
    if clean(value) is None:
        return False
    # Convertir a minúsculas y verificar
    s = str(value).strip().lower()
    return s in ['x', '1', 'true', 'yes', 'si']

def format_date_for_db(date_value):
    """
    Convierte varios formatos de fecha (Excel, datetime, string) a objeto date de Python.
    
    Args:
        date_value: Valor de fecha de la columna Excel.
    
    Returns:
        datetime.date o None.
    """
    if clean(date_value) is None:
        return None
    
    # Caso 1: Ya es un objeto datetime.date/datetime
    if isinstance(date_value, (datetime, date)):
        return date_value
        
    # Caso 2: Es un string, intentar parsear
    if isinstance(date_value, str):
        # Intentar formatos comunes (d/m/y, m/d/y, y-m-d)
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                # split()[0] ignora la hora si está presente
                return datetime.strptime(date_value.split()[0], fmt).date() 
            except (ValueError, TypeError):
                continue

    # Caso 3: Es un número de serie de Excel (float o int)
    if isinstance(date_value, (int, float)):
        try:
            # Excel usa el 1 de enero de 1900 como día 1.
            return (datetime(1899, 12, 30) + timezone.timedelta(days=date_value)).date()
        except OverflowError:
            return None # Fecha fuera de rango

    return None

# ====================================================================
# Funciones de Lógica de Negocio (Movida aquí para evitar circularidad)
# ====================================================================

def get_next_receipt_number():
    """
    Obtiene el siguiente número de recibo consecutivo.
    
    Busca el recibo con el número más alto y devuelve el siguiente.
    Si no hay recibos, comienza en 1.
    """
    try:
        # Se asume que receipt_number es un string que representa un número, 
        # y que se puede ordenar lexicográficamente o se convierte a int.
        # Es mejor convertir a INT si el formato es solo numérico.
        last_receipt = Receipt.objects.aggregate(models.Max('receipt_number'))
        max_number_str = last_receipt['receipt_number__max']
        
        if max_number_str:
            # Asumiendo que el número es puramente numérico (ej: "000001")
            last_number = int(max_number_str)
            next_number = last_number + 1
            # Formatear a 6 dígitos con relleno de ceros
            return f"{next_number:06d}" 
        else:
            # Primer recibo
            return "000001"
            
    except ValueError:
        # Si la conversión a int falla (por ejemplo, si el número incluye letras)
        # Se podría implementar una lógica de parsing más compleja aquí.
        # Para evitar el error, devolvemos un número de inicio por defecto
        # y registramos el error en el log.
        print("ERROR: Los números de recibo no son puramente numéricos. Reiniciando a 1.")
        return "000001"
    except Exception as e:
        print(f"ERROR al obtener el siguiente número de recibo: {e}")
        return "000001"


# ====================================================================
# 1. Procesamiento del Archivo Excel
# ====================================================================

def process_uploaded_excel(excel_file, user):
    """
    Lee el archivo Excel, valida las columnas y crea recibos.

    Args:
        excel_file: Objeto UploadedFile de Django (el archivo excel).
        user: El CustomUser que subió el archivo.

    Returns:
        (int, int): Contador de recibos exitosos y contador de errores.
    """
    
    # Columnas esperadas en el archivo Excel (en minúsculas para coincidir con la limpieza)
    EXPECTED_COLUMNS = [
        'n_transferencia', 'fecha_pago', 'rif_ci', 'nombre_cliente', 
        'monto', 'concepto', 'direccion_cliente',
    ]

    # Añadir las columnas de categoría
    for i in range(1, 11):
        EXPECTED_COLUMNS.append(f'cat_{i}')
        
    success_count = 0
    error_count = 0
    
    try:
        # Leer el archivo excel a un buffer de BytesIO
        excel_data = io.BytesIO(excel_file.read())
        
        # Intentar leer el archivo con Pandas
        df = pd.read_excel(excel_data, sheet_name=0)
        
        # 1. Limpieza de nombres de columnas: convertir a minúsculas y simplificar
        df.columns = df.columns.str.lower().str.strip()
        df.columns = df.columns.str.replace(r'[^a-z0-9_]', '', regex=True)
        df.columns = df.columns.str.replace(r'\s+', '_', regex=True)

        # 2. Renombrar columnas a un formato estándar
        column_mapping = {
            # Asume nombres comunes en español/inglés y mapea al estándar interno
            'n_transferencia': 'transaction_number', 'transferencia': 'transaction_number',
            'fecha_pago': 'payment_date', 'fecha': 'payment_date',
            'rif_ci': 'client_id', 'rif': 'client_id', 'ci': 'client_id', 'id': 'client_id',
            'nombre_cliente': 'client_name', 'cliente': 'client_name', 'nombre': 'client_name',
            'monto': 'amount', 
            'concepto': 'concept',
            'direccion_cliente': 'client_address', 'direccion': 'client_address',
        }
        
        # Mapeo de categorías
        for i in range(1, 11):
            column_mapping[f'cat_{i}'] = f'categoria{i}'
            column_mapping[f'categoria_{i}'] = f'categoria{i}'
            column_mapping[f'cat{i}'] = f'categoria{i}'
            column_mapping[f'c{i}'] = f'categoria{i}'
            
        df.rename(columns=column_mapping, inplace=True)

        # 3. Validar que al menos las columnas críticas existan después del mapeo
        CRITICAL_COLUMNS = ['payment_date', 'client_name', 'amount']
        if not all(col in df.columns for col in CRITICAL_COLUMNS):
            raise ValueError(f"El archivo Excel debe contener las columnas: {', '.join(CRITICAL_COLUMNS)}.")

        # 4. Procesar cada fila en una transacción atómica
        with transaction.atomic():
            
            # NOTA: Se eliminó la importación local de .views para resolver la circularidad.
            
            for index, row in df.iterrows():
                try:
                    # Preparar los datos
                    data = {}
                    
                    # Campos obligatorios y clave
                    # Ahora llama a la función localmente definida en este módulo
                    data['receipt_number'] = get_next_receipt_number() 
                    data['created_by'] = user
                    data['payment_date'] = format_date_for_db(row.get('payment_date'))
                    data['client_name'] = clean(row.get('client_name'))
                    data['amount'] = clean(row.get('amount'))

                    # Validar campos críticos
                    if not all([data['payment_date'], data['client_name'], data['amount']]):
                        raise ValueError("Fila incompleta: Faltan Fecha de Pago, Nombre o Monto.")
                    
                    # Campos opcionales
                    data['transaction_number'] = clean(row.get('transaction_number'))
                    data['client_id'] = clean(row.get('client_id'))
                    data['concept'] = clean(row.get('concept'))
                    data['client_address'] = clean(row.get('client_address'))

                    # Campos de Categoría (booleanos)
                    for i in range(1, 11):
                        field_name = f'categoria{i}'
                        # Usa .get() para manejar si la columna no existe en el archivo
                        data[field_name] = is_marked(row.get(field_name, False))

                    # Crear el objeto Receipt
                    Receipt.objects.create(**data)
                    success_count += 1
                    
                except Exception as e:
                    # Este print registra el error en consola para auditoría
                    print(f"Error al procesar la fila {index + 2}: {e}") # index + 2 (header + 1-based index)
                    error_count += 1
                    
    except Exception as e:
        # Este catch maneja errores de I/O, lectura de Pandas, o validación de encabezados
        print(f"Error fatal al procesar el archivo: {e}")
        # Intentar obtener el número de filas para el error_count si 'df' existe
        error_count = df.shape[0] if 'df' in locals() and not df.empty else 0 
        return (0, error_count) 

    return (success_count, error_count)


# ====================================================================
# 2. Generación de PDF
# ====================================================================

def generate_receipt_pdf(receipt):
    """
    Genera un PDF para el objeto Receipt dado.
    """
    buffer = io.BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # --- Configuración General ---
    padding = inch * 0.5
    line_height = 0.25 * inch
    
    # --- Encabezado ---
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - padding, "COMPROBANTE DE PAGO / RECIBO")

    # --- Título del Recibo (Derecha) ---
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.red)
    c.drawString(width - padding - 2*inch, height - padding - line_height*0.5, f"N° {receipt.receipt_number}")
    c.setFillColor(colors.black)
    
    # --- Datos de la Compañía (Simulado) ---
    c.setFont("Helvetica", 10)
    c.drawString(padding, height - padding - line_height * 0.5, "Nombre de la Empresa S.A.")
    c.drawString(padding, height - padding - line_height * 1.0, "RIF: J-01234567-8")
    c.drawString(padding, height - padding - line_height * 1.5, "Dirección Fiscal: Calle Ficticia, Ciudad, País.")
    
    # --- Bloque de Datos del Cliente (Caja con borde) ---
    box_y = height - padding - line_height * 2.5
    c.rect(padding, box_y - line_height * 2.5, width - 2 * padding, line_height * 3, stroke=1)
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(padding + 0.1 * inch, box_y + line_height * 0.4, "DATOS DEL CLIENTE:")
    
    c.setFont("Helvetica", 10)
    c.drawString(padding + 0.1 * inch, box_y - line_height * 0.2, f"Cliente: {receipt.client_name or 'N/A'}")
    c.drawString(width / 2, box_y - line_height * 0.2, f"Identificación (RIF/CI): {receipt.client_id or 'N/A'}")
    c.drawString(padding + 0.1 * inch, box_y - line_height * 0.7, f"Fecha de Pago: {receipt.payment_date.strftime('%d/%m/%Y') if receipt.payment_date else 'N/A'}")
    c.drawString(width / 2, box_y - line_height * 0.7, f"N° Transferencia: {receipt.transaction_number or 'N/A'}")

    # --- Detalle de Concepto ---
    detail_y = box_y - line_height * 3.5
    c.setFont("Helvetica-Bold", 12)
    c.drawString(padding, detail_y, "CONCEPTO DE PAGO:")
    
    c.setFont("Helvetica", 10)
    # Usar un TextObject para manejar conceptos largos automáticamente
    textobject = c.beginText(padding, detail_y - line_height * 0.5)
    textobject.setFont("Helvetica", 10)
    textobject.setLeading(14)
    # El contenido del concepto debe estar limpio
    concept_text = receipt.concept or "Pago por servicios / productos según detalle."
    textobject.textLines(concept_text)
    c.drawText(textobject)
    
    # --- Monto Total (Gran Destacado) ---
    amount_y = detail_y - line_height * 3.5 
    
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.darkgreen)
    c.drawString(padding, amount_y, "MONTO TOTAL:")
    
    # Formateo de monto
    formatted_amount = f"Bs. {receipt.amount:,.2f}" if isinstance(receipt.amount, (int, float, models.DecimalField)) else "N/A"
    c.setFont("Helvetica-Bold", 24)
    c.drawString(width - padding - 3*inch, amount_y, formatted_amount)
    c.setFillColor(colors.black)
    
    # --- Pie de Página (Estado) ---
    footer_y = padding 
    
    # Info de creación
    created_by_username = receipt.created_by.username if receipt.created_by else 'Sistema'
    c.setFont("Helvetica", 8)
    c.drawString(padding, footer_y + line_height * 0.5, f"Documento generado por {created_by_username} el {receipt.created_at.strftime('%d/%m/%Y %H:%M')}")

    # Marca de ANULADO
    if receipt.anulado:
        c.setFillColor(colors.red)
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(width / 2, height / 2, "ANULADO")
        c.setFont("Helvetica", 10)
        
        anulado_by_username = receipt.usuario_anulo.username if receipt.usuario_anulo else 'N/A'
        fecha_anulacion_str = receipt.fecha_anulacion.strftime('%d/%m/%Y %H:%M') if receipt.fecha_anulacion else 'N/A'
        
        c.drawString(padding, footer_y, f"Anulado por {anulado_by_username} el {fecha_anulacion_str}")
        
    c.showPage()
    c.save()
    
    return buffer.getvalue()