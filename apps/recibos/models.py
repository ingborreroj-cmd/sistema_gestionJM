from django.db import models
from django.contrib.auth.models import AbstractUser # Importamos AbstractUser para extenderlo
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone # Importado para usar en la señal si es necesario

# ====================================================================
# 1. Modelo de Usuario Personalizado (CustomUser)
# ====================================================================

# Constantes para definir los roles del sistema
class Rol(models.TextChoices):
    ADMIN = 'ADMIN', _('Administrador')
    USER = 'USER', _('Usuario Estándar')
    # Opcional: Si quieres un rol intermedio que acceda al admin site pero no sea superuser
    # EDITOR = 'EDITOR', _('Editor de Datos') 

class CustomUser(AbstractUser):
    """
    Modelo de Usuario que extiende AbstractUser para añadir el campo 'rol'.
    Este es el modelo que se debe usar para AUTH_USER_MODEL ('recibos.CustomUser').
    """
    rol = models.CharField(
        _('Rol'),
        max_length=10,
        choices=Rol.choices,
        default=Rol.USER, # El rol por defecto es 'Usuario Estándar'
        help_text=_("Define el nivel de acceso y permisos del usuario.")
    )
    
    class Meta:
        verbose_name = _('Usuario Personalizado')
        verbose_name_plural = _('Usuarios Personalizados')

    @property
    def is_admin(self):
        """Propiedad para verificar si el usuario tiene el rol Administrador."""
        return self.rol == Rol.ADMIN

    def save(self, *args, **kwargs):
        """
        [CORRECCIÓN CLAVE]: Método save() para sincronizar permisos.
        Asegura que un superusuario mantiene el rol ADMIN y sincroniza is_staff/is_superuser.
        """
        
        # 1. Sincronización de permisos a rol (Prioridad para el Admin/Superuser)
        # Si Django ya lo marcó como staff o superuser, forzamos el rol a ADMIN.
        if self.is_superuser or self.is_staff:
            self.rol = Rol.ADMIN

        # 2. El rol define el is_staff/is_superuser (Lógica de control)
        if self.rol == Rol.ADMIN:
            self.is_staff = True
            self.is_superuser = True
        elif self.rol == Rol.USER:
            self.is_staff = False
            self.is_superuser = False
        
        # Si agregaste el rol EDITOR, este sería el lugar:
        # elif self.rol == Rol.EDITOR:
        #     self.is_staff = True # Puede acceder al Admin Site
        #     self.is_superuser = False
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

# ====================================================================
# 2. Modelo del Recibo (Receipt)
# ====================================================================

# Referencia a tu modelo de usuario (usando el formato app_label.ModelName)
CUSTOM_USER_MODEL_PATH = 'recibos.CustomUser' 

class Receipt(models.Model):
    """
    Modelo que representa un registro de recibo de pago.
    """
    # Constantes para el campo 'status'
    STATUS_CHOICES = [
        ('PAGADO', 'Pagado'),
        ('ANULADO', 'Anulado'),
        ('PENDIENTE', 'Pendiente'),
    ]

    # 1. Información Principal y Estado
    receipt_number = models.CharField(max_length=50, unique=True, verbose_name="Nº Recibo")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PAGADO', verbose_name="Estado")
    # Nuevo campo 'anulado' para soft delete, crucial para la gestión
    anulado = models.BooleanField(default=False, verbose_name="Anulado")
    
    # 2. Información del Cliente
    client_name = models.CharField(max_length=255, verbose_name="Nombre Cliente")
    client_id = models.CharField(max_length=50, verbose_name="Cédula/RIF", blank=True, null=True) # Hacemos opcional
    client_address = models.TextField(verbose_name="Dirección", blank=True, null=True)

    # 3. Información Financiera/Transacción
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Monto (Bs.)")
    transaction_number = models.CharField(max_length=100, verbose_name="Nº Transferencia", blank=True, null=True)
    payment_date = models.DateField(verbose_name="Fecha de Pago")
    concept = models.TextField(verbose_name="Concepto")

    # 4. Categorías / Descripción de Regularización (10 campos booleanos)
    categoria1 = models.BooleanField(default=False, verbose_name="Cat. 1")
    categoria2 = models.BooleanField(default=False, verbose_name="Cat. 2")
    categoria3 = models.BooleanField(default=False, verbose_name="Cat. 3")
    categoria4 = models.BooleanField(default=False, verbose_name="Cat. 4")
    categoria5 = models.BooleanField(default=False, verbose_name="Cat. 5")
    categoria6 = models.BooleanField(default=False, verbose_name="Cat. 6")
    categoria7 = models.BooleanField(default=False, verbose_name="Cat. 7")
    categoria8 = models.BooleanField(default=False, verbose_name="Cat. 8")
    categoria9 = models.BooleanField(default=False, verbose_name="Cat. 9")
    categoria10 = models.BooleanField(default=False, verbose_name="Cat. 10")
    
    # 5. Información de Auditoría
    # Uso de la referencia corta a CustomUser
    created_by = models.ForeignKey(
        CUSTOM_USER_MODEL_PATH, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Creado por",
        related_name='recibos_creados_por' 
    )
    # Uso de la referencia corta a CustomUser
    usuario_anulo = models.ForeignKey(
        CUSTOM_USER_MODEL_PATH, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='recibos_anulados', 
        verbose_name="Anulado Por"
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Anulación")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")
    
    class Meta:
        verbose_name = "Recibo"
        verbose_name_plural = "Recibos"
        ordering = ['-receipt_number', '-created_at']

    def __str__(self):
        """Devuelve una representación legible del objeto Recibo."""
        return f"Recibo {self.receipt_number} - {self.client_name}"

    def get_categories_dict(self):
        """Método auxiliar para retornar las categorías como un diccionario."""
        return {
            f'categoria{i}': getattr(self, f'categoria{i}') for i in range(1, 11)
        }

# ====================================================================
# 3. Señales (Signals)
# ====================================================================

@receiver(pre_save, sender=Receipt)
def update_receipt_status(sender, instance, **kwargs):
    """
    Asegura que el campo 'status' refleje el estado 'anulado'.
    También establece la fecha de anulación si se marca como anulado por primera vez.
    """
    
    # Comprobar si se está creando una nueva instancia (pk is None)
    if instance.pk:
        # Si el objeto ya existe, lo cargamos para comparar el estado 'anulado' previo
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            was_anulado = old_instance.anulado
        except sender.DoesNotExist:
            was_anulado = False
    else:
        was_anulado = False
        
    # Lógica de Anulación
    if instance.anulado and instance.status != 'ANULADO':
        instance.status = 'ANULADO'
        # Si se anula ahora, y antes no lo estaba, registramos la fecha de anulación
        if not was_anulado:
            instance.fecha_anulacion = timezone.now()
            # Nota: el campo usuario_anulo debe ser llenado en la vista/formulario
            
    elif not instance.anulado and instance.status == 'ANULADO':
        # Si se 'des-anula' y estaba en ANULADO, lo regresamos a PAGADO
        instance.status = 'PAGADO'
        instance.fecha_anulacion = None
        instance.usuario_anulo = None # Limpiamos el usuario de anulación