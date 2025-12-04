from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Receipt, Rol
from .forms import CustomUserCreationForm, CustomUserChangeForm

# ====================================================================
# Configuración para CustomUser
# ====================================================================

# Registraremos CustomUser con un UserAdmin personalizado.
class CustomUserAdmin(UserAdmin):
    """
    Define cómo se muestra y edita CustomUser en el panel de administración.
    """
    # 1. Especificar los formularios a usar para crear y cambiar usuarios
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    
    # 2. Definir los campos que se muestran en la tabla de lista
    list_display = (
        "username", 
        "email", 
        "first_name", 
        "last_name", 
        "rol", # Mostramos el rol en la lista
        "is_staff",
        "is_active"
    )
    
    # 3. Campos para la vista de edición/detalle del usuario
    fieldsets = UserAdmin.fieldsets + (
        # Añadir el campo 'rol' al final de la sección 'Permissions'
        ("Roles y Permisos Adicionales", {"fields": ("rol",)}),
    )
    
    # 4. Campos para la vista de creación de usuario
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Roles", {"fields": ("rol",)}),
    )
    
    # 5. Permite filtrar por rol
    list_filter = UserAdmin.list_filter + ('rol',)


# ====================================================================
# Configuración para Receipt
# ====================================================================

class ReceiptAdmin(admin.ModelAdmin):
    """
    Configuración simple para el modelo Recibo.
    """
    list_display = (
        'receipt_number', 
        'client_name', 
        'amount', 
        'status', 
        'anulado', 
        'created_by', 
        'payment_date'
    )
    list_filter = ('status', 'anulado', 'payment_date', 'created_at')
    search_fields = ('receipt_number', 'client_name', 'client_id', 'concept')
    ordering = ('-created_at',)
    
    # Agrupación de campos en la vista de detalle
    fieldsets = (
        ('Información Principal', {
            'fields': ('receipt_number', 'status', 'anulado', 'payment_date', 'concept')
        }),
        ('Detalles del Cliente', {
            'fields': ('client_name', 'client_id', 'client_address')
        }),
        ('Detalles Financieros', {
            'fields': ('amount', 'transaction_number')
        }),
        ('Categorías (Regularización)', {
            'fields': ('categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5', 'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10')
        }),
        ('Auditoría', {
            'fields': ('created_by', 'usuario_anulo', 'fecha_anulacion')
        }),
    )
    
    # Auto-completar el campo created_by con el usuario actual
    def save_model(self, request, obj, form, change):
        if not obj.pk: # Solo si es un objeto nuevo
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ====================================================================
# Registro de Modelos
# ====================================================================

# 1. Registrar el usuario personalizado con la configuración CustomUserAdmin
admin.site.register(CustomUser, CustomUserAdmin)

# 2. Registrar el modelo Recibo
admin.site.register(Receipt, ReceiptAdmin)