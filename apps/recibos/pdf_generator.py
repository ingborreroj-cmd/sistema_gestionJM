from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import black, HexColor
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import os
import io

# --- Configuración Estándar ---
# Definición de fuentes y estilos (usamos fuentes estándar de ReportLab)
styles = getSampleStyleSheet()
style_normal = styles['Normal']

# Coordenadas y Dimensiones del Documento
WIDTH, HEIGHT = letter # 612 x 792 puntos (8.5 x 11 pulgadas)
MARGIN = 40
USABLE_WIDTH = WIDTH - 2 * MARGIN
USABLE_HEIGHT = HEIGHT - 2 * MARGIN

# --- Constantes de Diseño y Texto ---
HEADER_HEIGHT = 120 # Altura de la imagen de encabezado
LINE_SPACE = 14 # Espaciado vertical entre líneas de texto

# Información fija del pie de página (Receptor/Institución)
RECEIVER_INFO = [
    "PRESLEY ORTEGA",
    "GERENTE DE ADMINISTRACIÓN Y SERVICIOS",
    "GACETA OFICIAL N° 40.758 DEL 02/10/2015",
]

# Descripciones de las categorías (Para replicar el comportamiento de checkboxes)
CATEGORIA_DESCRIPTIONS = {
    'categoria1': "Descripción Detallada de Categoría 1.",
    'categoria2': "Descripción Detallada de Categoría 2.",
    'categoria3': "Descripción Detallada de Categoría 3.",
    'categoria4': "Descripción Detallada de Categoría 4.",
    'categoria5': "Descripción Detallada de Categoría 5.",
    'categoria6': "Descripción Detallada de Categoría 6.",
    'categoria7': "Descripción Detallada de Categoría 7.",
    'categoria8': "Descripción Detallada de Categoría 8.",
    'categoria9': "Descripción Detallada de Categoría 9.",
    'categoria10': "Descripción Detallada de Categoría 10.",
}

# ====================================================================
# Funciones de Utilidad (Replicando utils.py y funciones de formato)
# ====================================================================

def format_currency(amount):
    """
    Formatea un número al formato de moneda venezolano (punto como separador de miles,
    coma como separador decimal).
    Ejemplo: 1234567.89 -> 1.234.567,89
    """
    try:
        amount = float(amount)
        # Formato estándar de Python: 1,234,567.89 (coma para miles, punto para decimales)
        formatted = f"{amount:,.2f}"
        
        # Invertir separadores para el formato local:
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        
        return formatted
    except (ValueError, TypeError):
        return "0,00"

def draw_wrapped_text(c, text, x, y, max_width, font_name="Helvetica", font_size=10, align='LEFT'):
    """
    Dibuja texto multilinea dentro de un ancho máximo (max_width).
    Reemplaza la lógica original de draw_wrapped_text.
    """
    c.setFont(font_name, font_size)
    p = Paragraph(text, style_normal)
    
    # Calcular altura requerida
    w, h = p.wrapOn(c, max_width, HEIGHT)
    
    if align == 'CENTER':
        x = x + (max_width - w) / 2
    elif align == 'RIGHT':
        x = x + (max_width - w)
    
    p.drawOn(c, x, y - h)
    return h # Retorna la altura que consumió

# ====================================================================
# Función Principal de Generación de PDF
# ====================================================================

def generar_pdf_completo(data):
    """
    Genera el recibo de pago completo en formato PDF utilizando ReportLab.

    Args:
        data (dict): Diccionario con todos los datos del recibo, incluyendo:
                     nombre, rif_cedula_identidad, total_monto_bs, fecha,
                     concepto, numero_recibo, usuario_creador, y los 10 booleanos
                     de las categorías.
    
    Returns:
        io.BytesIO: Buffer de Bytes con el contenido del PDF.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setAuthor(data.get('usuario_creador', 'Sistema de Recibos'))

    # Inicialización de la posición Y para el dibujo
    current_y = HEIGHT - MARGIN
    
    # --- 1. CABECERA Y METADATOS (Replicando el diseño original) ---
    
    # Placeholder de Imagen de Encabezado (HEADER_IMAGE). 
    # Como no podemos cargar archivos locales, usamos un rectángulo como placeholder.
    c.setFillColor(HexColor('#003366')) # Color azul oscuro
    c.rect(MARGIN, current_y - HEADER_HEIGHT, USABLE_WIDTH, HEADER_HEIGHT, fill=True)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(WIDTH / 2, current_y - 30, "LOGO DE LA INSTITUCIÓN / MEMBRETE")
    c.setFont("Helvetica", 10)
    c.drawCentredString(WIDTH / 2, current_y - 50, "Sistema de Gestión de Recibos de Pago")
    
    current_y -= (HEADER_HEIGHT + 15)
    
    # Título "RECIBO DE PAGO"
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN, current_y, "RECIBO DE PAGO")
    
    # Nº Recibo y Estado (Parte superior derecha)
    c.setFont("Helvetica", 12)
    c.drawString(MARGIN, current_y - 20, f"Nº Recibo: {data['numero_recibo']}")
    
    status_text = "ANULADO" if data.get('anulado', False) else "ACTIVO"
    status_color = HexColor('#FF0000') if data.get('anulado', False) else HexColor('#006600')
    c.setFillColor(status_color)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(WIDTH - MARGIN, current_y - 20, f"ESTADO: {status_text}")
    c.setFillColor(black) # Volver al color negro para el texto normal
    
    current_y -= 50

    # --- 2. DATOS DEL CLIENTE Y TRANSACCIÓN ---

    # Fecha y Nombre
    c.setFont("Helvetica", 11)
    c.drawString(MARGIN, current_y, f"Fecha: {data['fecha']}")
    current_y -= LINE_SPACE
    c.drawString(MARGIN, current_y, f"Recibí de: {data['nombre']}")
    current_y -= LINE_SPACE
    c.drawString(MARGIN, current_y, f"Identificación (RIF/Cédula): {data['rif_cedula_identidad']}")
    
    # Monto Total
    monto_formateado = format_currency(data['total_monto_bs'])
    current_y -= LINE_SPACE * 2
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN, current_y, "MONTO TOTAL RECIBIDO (Bs):")
    c.setFillColor(HexColor('#333333'))
    c.drawRightString(WIDTH - MARGIN, current_y, monto_formateado)
    c.setFillColor(black)
    
    # Número de Transferencia
    current_y -= LINE_SPACE * 2
    c.setFont("Helvetica", 11)
    num_transf_text = data.get('numero_transferencia', 'N/A')
    c.drawString(MARGIN, current_y, f"Nº de Transferencia/Referencia: {num_transf_text}")

    # Concepto
    current_y -= LINE_SPACE * 2
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, current_y, "CONCEPTO/DETALLE DEL PAGO:")
    current_y -= 5
    c.line(MARGIN, current_y, WIDTH - MARGIN, current_y) # Línea divisoria
    current_y -= LINE_SPACE
    
    c.setFont("Helvetica", 10)
    # Dibujar el concepto usando draw_wrapped_text
    consumed_height = draw_wrapped_text(c, data.get('concepto', 'Sin concepto detallado.'), MARGIN, current_y, USABLE_WIDTH, font_size=10)
    current_y -= (consumed_height + LINE_SPACE)

    # --- 3. SECCIÓN DE CATEGORÍAS (Checkboxes) ---
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, current_y, "REGULARIZACIÓN DEL PAGO:")
    current_y -= LINE_SPACE

    categories_start_y = current_y

    for key, description in CATEGORIA_DESCRIPTIONS.items():
        if data.get(key, False):
            # Dibujar la descripción de la categoría
            c.setFont("Helvetica", 10)
            c.drawString(MARGIN + 15, current_y, description)

            # Dibujar el "Checkbox" marcado (X)
            c.setFont("Helvetica-Bold", 12)
            c.drawRightString(WIDTH - MARGIN - 5, current_y, "X")
            
            # Dibujar un pequeño cuadrado (simulación de checkbox)
            c.rect(MARGIN + 2, current_y, 10, 10)

            current_y -= LINE_SPACE
        
        # Lógica de paginación básica: si queda poco espacio, pasar a la siguiente página.
        if current_y < 200:
            c.showPage()
            current_y = HEIGHT - MARGIN - 20 # Reiniciar Y en la nueva página
            c.setFont("Helvetica-Bold", 10)
            c.drawString(MARGIN, current_y, f"Continuación Recibo N° {data['numero_recibo']}")
            current_y -= LINE_SPACE * 2


    # --- 4. SECCIÓN DE FIRMAS Y PIE DE PÁGINA ---
    
    # Asegurarse de que las firmas estén al menos a 150pt del borde inferior
    if current_y > 150:
        current_y = 150
    else:
        # Si la sección de categorías empujó current_y demasiado abajo, pasamos de página
        c.showPage()
        current_y = 150
    
    # 4.1. Líneas de Firma
    FIRM_Y = current_y + 10
    FIRM_WIDTH = USABLE_WIDTH / 2 - 30
    
    # Firma del Cliente (Izquierda)
    c.line(MARGIN, FIRM_Y, MARGIN + FIRM_WIDTH, FIRM_Y)
    c.setFont("Helvetica", 10)
    c.drawCentredString(MARGIN + FIRM_WIDTH / 2, FIRM_Y - 15, "FIRMA DEL CLIENTE")
    
    # Nombre del Cliente (Draw Wrapped Name - Simulación)
    client_name_y = FIRM_Y - 30
    c.setFont("Helvetica-Bold", 10)
    draw_wrapped_text(c, data['nombre'], MARGIN, client_name_y, FIRM_WIDTH, align='CENTER')

    # Firma del Receptor/Institución (Derecha)
    RECEIVER_X = WIDTH - MARGIN - FIRM_WIDTH
    c.line(RECEIVER_X, FIRM_Y, WIDTH - MARGIN, FIRM_Y)
    c.setFont("Helvetica", 10)
    c.drawCentredString(RECEIVER_X + FIRM_WIDTH / 2, FIRM_Y - 15, "FIRMA DEL RECEPTOR")
    
    # 4.2. Información Fija del Receptor
    info_y = FIRM_Y - 30
    c.setFont("Helvetica", 8)
    for line in RECEIVER_INFO:
        draw_wrapped_text(c, line, RECEIVER_X, info_y, FIRM_WIDTH, font_size=8, align='CENTER')
        info_y -= 10


    # Finalizar el PDF
    c.showPage()
    c.save()
    
    # Rewind the buffer (IMPORTANTE)
    buffer.seek(0)
    return buffer