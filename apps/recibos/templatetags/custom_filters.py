from django import template

# Crea una instancia de Library para registrar tus tags y filtros
register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Filtro para obtener un elemento de un diccionario (o de un objeto similar 
    a un diccionario, como un formulario de Django) usando una clave de cadena.
    
    Uso en template: {{ form|get_item:"campo_deseado" }}
    """
    try:
        # Intentamos acceder al elemento del 'dictionary' (que en nuestro caso es el form) 
        return dictionary.get(key)
    except AttributeError:
        # Si no tiene un método .get() (ej: es un objeto de diccionario Python simple), 
        # intentamos el acceso directo
        return dictionary[key]