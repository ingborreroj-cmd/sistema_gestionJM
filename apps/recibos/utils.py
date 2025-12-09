import pandas as pd
from django.db import transaction
from django.db.models import Max
from decimal import Decimal, InvalidOperation
from datetime import date 
import logging
import re
from .models import Recibo 

logger = logging.getLogger(__name__)

# --- FUNCIONES DE UTILIDAD ---

def to_boolean(value):
    """Convierte valores comunes de Excel (NaN, SI, X, 1, etc.) a Booleano."""
    if pd.isna(value):
        return False
    # La X es la marca principal, debe estar aquí.
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

# --- FUNCIÓN PRINCIPAL DE IMPORTACIÓN ---

def importar_recibos_desde_excel(archivo_excel):
    
    RIF_COL = 'rif_cedula_identidad'

    try:
        # 1. Nombres Canónicos (la lista fija de 22 elementos)
        COLUMNAS_CANONICAS = [
            'estado', 'nombre', RIF_COL, 'direccion_inmueble', 'ente_liquidado',
            'categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5',
            'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10',
            'gastos_administrativos', 'tasa_dia', 'total_monto_bs', 
            'numero_transferencia', 'conciliado', 'fecha', 'concepto' 
        ]
        
        # 2. LECTURA SIMPLE y robusta (Ignorando encabezado)
        df_temp = pd.read_excel(
            archivo_excel, 
            sheet_name='Hoja2', 
            header=None,         
            nrows=2 # Leer solo la Fila 1 (encabezado) y la Fila 2 (datos)
        )
        
        # 3. Extracción de la Fila 2 (el índice 1)
        if len(df_temp) < 2:
            return False, "Error: El archivo Excel debe contener al menos dos filas (Encabezado y Datos)."

        fila_datos = df_temp.iloc[1] 
        
        # 4. Verificación de 22 columnas
        if len(fila_datos) != len(COLUMNAS_CANONICAS):
             return False, f"Error: La Fila 2 tiene {len(fila_datos)} columnas, pero se esperaban {len(COLUMNAS_CANONICAS)}. El archivo Excel está reportando datos hasta la Columna K (11 columnas). Realice la limpieza rigurosa del Excel."
             
        fila_mapeada = dict(zip(COLUMNAS_CANONICAS, fila_datos.tolist()))
        
        # --- FILTRO Y VALIDACIÓN DEL RIF ---
        rif_cedula_raw = str(fila_mapeada.get(RIF_COL, '')).strip()
        
        if not rif_cedula_raw:
            return False, "El registro de la Fila 2 no tiene RIF/Cédula y no se puede procesar."
            
        logger.info(f"ÉXITO EN LECTURA: Se encontró el registro con RIF: {rif_cedula_raw}")
        
        data_a_insertar = {}
        
        # --- B. TRANSACCIÓN Y MAPEO DE DATOS ---
        with transaction.atomic():
            # Obtener y asignar nuevo número de recibo
            ultimo_recibo = Recibo.objects.aggregate(Max('numero_recibo'))['numero_recibo__max']
            data_a_insertar['numero_recibo'] = (ultimo_recibo or 0) + 1
            
            # Mapeo y Normalización de Texto
            data_a_insertar['estado'] = str(fila_mapeada.get('estado', '')).strip().upper() 
            data_a_insertar['nombre'] = str(fila_mapeada.get('nombre', '')).strip().title()
            data_a_insertar['rif_cedula_identidad'] = str(rif_cedula_raw).strip().replace('.', '').replace('-', '').replace(' ', '').upper()
            
            data_a_insertar['direccion_inmueble'] = str(fila_mapeada.get('direccion_inmueble', 'DIRECCION NO ESPECIFICADA')).strip().title()
            data_a_insertar['ente_liquidado'] = str(fila_mapeada.get('ente_liquidado', 'ENTE NO ESPECIFICADO')).strip().title()
            data_a_insertar['numero_transferencia'] = str(fila_mapeada.get('numero_transferencia', '')).strip().upper()
            data_a_insertar['concepto'] = str(fila_mapeada.get('concepto', '')).strip().title()
            
            # 🛑 CATEGORÍAS MAPEADAS COMO BOOLEANO (Segun la instruccion 'X' = True)
            data_a_insertar['categoria1'] = to_boolean(fila_mapeada.get('categoria1'))
            data_a_insertar['categoria2'] = to_boolean(fila_mapeada.get('categoria2'))
            data_a_insertar['categoria3'] = to_boolean(fila_mapeada.get('categoria3'))
            data_a_insertar['categoria4'] = to_boolean(fila_mapeada.get('categoria4'))
            data_a_insertar['categoria5'] = to_boolean(fila_mapeada.get('categoria5'))
            data_a_insertar['categoria6'] = to_boolean(fila_mapeada.get('categoria6'))
            data_a_insertar['categoria7'] = to_boolean(fila_mapeada.get('categoria7'))
            data_a_insertar['categoria8'] = to_boolean(fila_mapeada.get('categoria8'))
            data_a_insertar['categoria9'] = to_boolean(fila_mapeada.get('categoria9'))
            data_a_insertar['categoria10'] = to_boolean(fila_mapeada.get('categoria10'))
            
            # Conciliado (Booleano)
            data_a_insertar['conciliado'] = to_boolean(fila_mapeada.get('conciliado'))

            # Conversión a Decimal
            data_a_insertar['gastos_administrativos'] = limpiar_y_convertir_decimal(fila_mapeada.get('gastos_administrativos', 0))
            data_a_insertar['tasa_dia'] = limpiar_y_convertir_decimal(fila_mapeada.get('tasa_dia', 0))
            data_a_insertar['total_monto_bs'] = limpiar_y_convertir_decimal(fila_mapeada.get('total_monto_bs', 0))

            # Conversión a Fecha
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
                raise ValueError(f"Formato de fecha no reconocido para el valor: {fecha_excel}. Use formatos estándar como DD/MM/AAAA o AAAA-MM-DD.")


            # Creación del Recibo
            recibo_creado = Recibo.objects.create(**data_a_insertar)
            
            return True, f"Se generó el recibo N° {recibo_creado.numero_recibo} para {data_a_insertar['nombre']} exitosamente. Listo para PDF."

    except Exception as e:
        logger.error(f"FALLO DE VALIDACIÓN en el registro: {e}")
        return False, f"Fallo en la carga: Error de validación de datos (revisar consola): {str(e)}"