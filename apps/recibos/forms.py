# apps/recibos/forms.py

from django import forms
from .models import Recibo 
from django.core.exceptions import ValidationError

# Clases base de Tailwind modificadas:

# CLASE BASE PARA LA MAYORÍA DE LOS INPUTS (CON BORDE LEVE AHORA)
TAILWIND_CLASS = 'form-input w-full rounded-lg border border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 transition duration-150'
DATE_INPUT_CLASS = TAILWIND_CLASS # Reutilizamos la misma clase para la fecha


class ReciboForm(forms.ModelForm):
    """
    Formulario modificado con normalización de datos y estilos de contorno.
    """

    # =======================================================
    # 1. NORMALIZACIÓN DE DATOS (clean methods) - MANTENIDOS
    # =======================================================

    def clean_nombre(self):
        data = self.cleaned_data['nombre'].strip()
        return data.title()

    def clean_rif_cedula_identidad(self):
        data = self.cleaned_data['rif_cedula_identidad'].strip().upper()
        return data.replace(' ', '').replace('-', '')
    
    def clean_ente_liquidado(self):
        data = self.cleaned_data['ente_liquidado'].strip()
        return data.upper()
    
    def clean_estado(self):
        data = self.cleaned_data['estado'].strip()
        return data.title()
    
    def clean_numero_transferencia(self):
        data = self.cleaned_data['numero_transferencia'].strip()
        return data.upper()

    # =======================================================
    # 2. META y WIDGETS - (USANDO TAILWIND_CLASS CON BORDE)
    # =======================================================

    class Meta:
        model = Recibo
        
        fields = [
            'numero_recibo', 
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
        
        widgets = {
            # CAMPO READONLY: Estilo distinto para readonly
            'numero_recibo': forms.TextInput(attrs={
                'readonly': 'readonly', 
                'class': 'mt-1 block w-full rounded-lg border border-gray-300 bg-gray-100 shadow-inner text-gray-700 font-semibold' # Borde añadido aquí también
            }),

            # 1. Datos del Cliente
            'estado': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            'nombre': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            'rif_cedula_identidad': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            'direccion_inmueble': forms.Textarea(attrs={'class': TAILWIND_CLASS, 'rows': 2}),
            'ente_liquidado': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            
            # 2. Montos
            'gastos_administrativos': forms.NumberInput(attrs={'class': TAILWIND_CLASS, 'step': '0.01'}),
            'tasa_dia': forms.NumberInput(attrs={'class': TAILWIND_CLASS, 'step': '0.0001'}),
            'total_monto_bs': forms.NumberInput(attrs={'class': TAILWIND_CLASS, 'step': '0.01'}),
            
            # 3. Conciliación
            'numero_transferencia': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': DATE_INPUT_CLASS}), 
            'concepto': forms.Textarea(attrs={'class': TAILWIND_CLASS, 'rows': 2}),
        }