from django import template
from decimal import Decimal

# La variable 'register' debe existir.
register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Permite acceder a un elemento de un diccionario usando una clave variable
    en el template (ej. {{ request.GET|get_item:'parametro' }}).
    """
    # Usamos .get() para evitar KeyError si la clave no existe
    return dictionary.get(key)


@register.filter
def sum_amounts(receipts):
    """
    Calcula la suma del campo 'amount' a través de una lista de recibos 
    (QuerySet o lista de objetos).
    """
    total = Decimal('0.00')

    if not receipts:
        return total

    for receipt in receipts:
        try:
            amount = getattr(receipt, 'amount', 0)
            
            if isinstance(amount, (int, float)):
                total += Decimal(str(amount))
            elif isinstance(amount, Decimal):
                total += amount
            
        except Exception as e:
            # En un entorno de desarrollo esto es útil
            print(f"Error procesando monto para recibo. Error: {e}")
            continue

    return total


@register.filter
def remove_page(query_string):
    """
    Elimina el parámetro 'page' de una cadena de consulta (query string) 
    codificada (ej. 'q=search&page=5&date=today'). 
    Se usa para construir enlaces de paginación que mantengan los filtros.
    """
    # Si la cadena está vacía, devuelve una cadena vacía
    if not query_string:
        return ""

    # Divide la cadena en parámetros individuales
    params = query_string.split('&')
    
    # Filtra los parámetros, excluyendo cualquier cosa que empiece con 'page='
    filtered_params = [
        param for param in params 
        if not param.startswith('page=')
    ]
    
    # Reúne los parámetros restantes en una sola cadena
    return '&'.join(filtered_params)