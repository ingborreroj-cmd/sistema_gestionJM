from django import template
from django.utils.text import slugify as django_slugify
from django.template.defaultfilters import capfirst
from ..models import CATEGORY_CHOICES_MAP  # Asegúrate de que esta importación sea correcta
from urllib.parse import urlparse, parse_qs, urlencode
import re
# Ya no necesitamos 'Decimal' porque eliminamos currency_format

# 💡 NOTA IMPORTANTE:
# Si el mapeo de CATEGORY_CHOICES_MAP no se importa correctamente
# desde models.py, DEBES asegurarte de que exista una definición
# funcional para que el filtro 'get_category_label' funcione.

register = template.Library()

# --- FILTROS DE MANEJO DE CADENAS Y LISTAS ---

@register.filter
def split(value, arg):
    """
    Divide una cadena (value) por un delimitador (arg).
    Uso en template: 'cadena,con,comas'|split:','
    Necesario para iterar sobre tamaños de página y categorías en listas de cadenas.
    """
    try:
        return value.split(arg)
    except:
        return [value] # Devuelve una lista con el valor original si falla

@register.filter
def slugify(value):
    """
    Convierte el valor a un 'slug' amigable para URL/ID.
    Necesario para generar IDs limpios para checkboxes de filtro.
    Ej: "Pago Mensual" -> "pago-mensual"
    """
    return django_slugify(value)

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Permite obtener un valor de un diccionario usando la clave.
    Útil si se necesita acceder a valores complejos en el template.
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

# --- FILTROS DE FORMATO ESPECÍFICO ---

@register.filter
def get_category_label(field_name):
    """
    Toma la clave numérica de la categoría (1, 2, 3...) y 
    devuelve la etiqueta legible asociada.
    Necesario para mostrar nombres legibles de categoría en la tabla.
    """
    if field_name is None:
        return ""
    try:
        # Asegura que field_name sea un entero para la búsqueda
        key = int(field_name) 
    except (ValueError, TypeError):
        return 'Concepto Desconocido'
    
    return CATEGORY_CHOICES_MAP.get(key, 'Concepto Desconocido')

# ❌ FILTRO 'currency_format' ELIMINADO

# --- FILTROS DE MANEJO DE URL ---

@register.filter(name='remove_query_param')
def remove_query_param(url_querystring, param_name):
    """
    Elimina un parámetro específico de la query string (cadena de consulta).
    Esencial para mantener los filtros activos (ej: estado, q) al cambiar de página.
    Uso: request.GET.urlencode|remove_query_param:'page'
    """
    if not url_querystring:
        return ''
        
    query_dict = parse_qs(url_querystring, keep_blank_values=True)
    
    # Eliminar el parámetro solicitado
    if param_name in query_dict:
        del query_dict[param_name]
    
    # Reconstruir la query string
    new_querystring = urlencode(query_dict, doseq=True)
    
    # Devuelve la cadena con un '&' inicial si hay otros parámetros, sino una cadena vacía
    return '&' + new_querystring if new_querystring else ''