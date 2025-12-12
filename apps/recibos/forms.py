# apps/recibos/forms.py

from django import forms
from .models import Recibo 

# Clases base de Tailwind para reutilización
TAILWIND_CLASS = 'form-input w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
DATE_INPUT_CLASS = 'form-input w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'


class ReciboForm(forms.ModelForm):
    """
    Formulario utilizado para la Modificación (y posiblemente la Creación) 
    de instancias del modelo Recibo.
    """
    class Meta:
        model = Recibo
        
        # Incluye todos los campos que el usuario puede cambiar.
        # Excluye los campos de control (numero_recibo, fecha_creacion, anulado)
        fields = [
            'estado',
            'nombre',
            'rif_cedula_identidad',
            'direccion_inmueble',
            'ente_liquidado',
            'categoria1',
            'categoria2',
            'categoria3',
            'categoria4',
            'categoria5',
            'categoria6',
            'categoria7',
            'categoria8',
            'categoria9',
            'categoria10',
            'gastos_administrativos',
            'tasa_dia',
            'total_monto_bs',
            'numero_transferencia',
            'conciliado',
            'fecha',
            'concepto',
        ]
        
        # Personalización de Widgets para Tailwind y UX
        widgets = {
            # 1. Datos del Cliente
            'estado': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            'nombre': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            'rif_cedula_identidad': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            'direccion_inmueble': forms.Textarea(attrs={'class': TAILWIND_CLASS, 'rows': 2}),
            'ente_liquidado': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            
            # 2. Categorías (Usan checkbox por defecto, solo mejoramos la clase si es necesario)
            # Nota: Los booleanos usan CheckboxInput por defecto.

            # 3. Montos (Aseguramos que sean campos de entrada numérica con 2 decimales)
            'gastos_administrativos': forms.NumberInput(attrs={'class': TAILWIND_CLASS, 'step': '0.01'}),
            'tasa_dia': forms.NumberInput(attrs={'class': TAILWIND_CLASS, 'step': '0.0001'}), # 4 decimales
            'total_monto_bs': forms.NumberInput(attrs={'class': TAILWIND_CLASS, 'step': '0.01'}),
            
            # 4. Conciliación
            'numero_transferencia': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': DATE_INPUT_CLASS}), # Selector de calendario
            'concepto': forms.Textarea(attrs={'class': TAILWIND_CLASS, 'rows': 2}),
        }