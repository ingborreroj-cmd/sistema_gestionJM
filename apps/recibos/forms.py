from django import forms
from django.contrib.auth import get_user_model
# Importamos todas las bases necesarias de Django para formularios de autenticación
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AdminPasswordChangeForm
from .models import Receipt

# --- Formularios de Usuario para el Admin ---
# Si tu views.py los requiere, deben estar definidos aquí.

class CustomUserCreationForm(UserCreationForm):
    """Formulario para la creación de un nuevo usuario en el Admin."""
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = UserCreationForm.Meta.fields + ('email',) 

class CustomUserChangeForm(UserChangeForm):
    """Formulario para la edición de un usuario existente en el Admin."""
    class Meta:
        model = get_user_model()
        fields = UserChangeForm.Meta.fields
        # Nota: AdminPasswordChangeForm está disponible gracias a la importación.

# --- Formularios de Recibos ---

class UploadFileForm(forms.Form):
    """Formulario simple para subir el archivo Excel."""
    file = forms.FileField(
        label='Archivo Excel (.xlsx o .xls)',
        help_text='Sube el archivo con la data de los recibos.'
    )

class ReceiptForm(forms.ModelForm):
    """Formulario basado en modelo para crear o editar un solo recibo."""
    class Meta:
        model = Receipt
        # Asegúrate de listar aquí todos los campos de tu modelo Receipt
        fields = [
            'transaction_number', 'payment_date', 'client_id', 
            'client_name', 'amount', 'concept', 'client_address',
            'categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5', 
            'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10',
        ]
        widgets = {
            # Se usa 'date' para que el navegador muestre un selector de calendario
            'payment_date': forms.DateInput(attrs={'type': 'date'}), 
        }