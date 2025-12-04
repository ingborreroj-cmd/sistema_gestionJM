from django import template
from decimal import Decimal

# La variable 'register' debe estar definida a nivel de módulo 
# para registrar tags y filtros de plantilla
register = template.Library()

@register.filter
def sum_amounts(receipts):
    """
    Calcula la suma del campo 'amount' a través de una lista de recibos 
    (ya sea un QuerySet o una lista de objetos).

    Uso en la plantilla:
    {% with page_total=receipts|sum_amounts %}
        {{ page_total|floatformat:2 }}
    {% endwith %}
    """
    total = Decimal('0.00')

    # Asegurarse de que la lista de recibos es iterable y no está vacía
    if not receipts:
        return total

    for receipt in receipts:
        # Asumimos que el campo 'amount' existe y es un tipo numérico 
        try:
            amount = getattr(receipt, 'amount', 0)
            
            # Convertir a Decimal para una suma precisa (evitando errores de punto flotante)
            if isinstance(amount, (int, float)):
                total += Decimal(str(amount))
            elif isinstance(amount, Decimal):
                total += amount
            
        except Exception as e:
            # En un entorno real, se recomienda usar logging
            print(f"Advertencia: No se pudo procesar el monto para el recibo {receipt}. Error: {e}")
            continue

    return total