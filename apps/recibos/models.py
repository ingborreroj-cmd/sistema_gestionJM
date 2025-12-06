# recibos/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

# Obtener el modelo de usuario activo (usualmente User de django.contrib.auth)
User = get_user_model()

# --- Mapeo de Categorías (Constantes de Lógica de Negocio) ---

# Esto mapea las 10 columnas booleanas a los nombres descriptivos, 
# esencial para la UI, los reportes y la auditoría.
MAPEO_CATEGORIAS = {
    1: _("Título de Tierra Urbana - Adjudicación en Propiedad"),
    2: _("Título de Tierra Urbana - Adjudicación más Vivienda"),
    3: _("Vivienda - Tierra Municipal"),
    4: _("Vivienda - Tierra Privada"),
    5: _("Vivienda - Tierra INAVI/INTU"),
    6: _("Excedentes - Con título Tierra Urbana"),
    7: _("Excedentes - Título INAVI"),
    8: _("Estudios Técnicos"),
    9: _("Arrendamiento Locales Comerciales"),
    10: _("Arrendamiento de Terrenos")
}

# --- Modelo Principal ---

class Recibo(models.Model):
    # --- Campos de Identificación y Estado (Claves de la BD) ---
    id = models.AutoField(primary_key=True)
    numero_recibo = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Número de Recibo",
        help_text="Número consecutivo asignado al recibo."
    )
    
    # --- Campos de Datos del Cliente y Concepto ---
    nombre = models.CharField(max_length=255, verbose_name="Nombre del Pagador")
    rif_cedula_identidad = models.CharField(max_length=20, verbose_name="Cédula/RIF")
    direccion_inmueble = models.TextField(blank=True, null=True, verbose_name="Dirección del Inmueble")
    ente_liquidado = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ente Liquidado")
    concepto = models.TextField(blank=True, null=True, verbose_name="Concepto de Pago")
    
    # --- Campos de Categorías (10 Columnas Booleanas) ---
    categoria1 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(1))
    categoria2 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(2))
    categoria3 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(3))
    categoria4 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(4))
    categoria5 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(5))
    categoria6 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(6))
    categoria7 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(7))
    categoria8 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(8))
    categoria9 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(9))
    categoria10 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(10))

    # --- Campos Financieros y de Trazabilidad ---
    gastos_administrativos = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Gastos Adm. (Bs)")
    tasa_dia = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tasa del Día (Bs/Divisa)")
    total_monto_bs = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Monto Total (Bs)")
    
    numero_transferencia = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name="Número de Transferencia",
        unique=True, # Importante para la validación de duplicados
    )
    
    fecha = models.DateField(verbose_name="Fecha de Pago/Emisión")
    
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Pagado', 'Pagado'),
        ('En Revisión', 'En Revisión'),
        ('Rechazado', 'Rechazado'),
    ]
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='Pendiente',
        verbose_name="Estado de Pago"
    )
    
    conciliado = models.BooleanField(default=False, verbose_name="Conciliado (Banco)")
    anulado = models.BooleanField(default=False, verbose_name="Anulado")

    # --- Campos de Auditoría (Reemplazando campos de usuario directo) ---
    usuario_creador = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='recibos_creados',
        verbose_name="Usuario Creador"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Creación")
    
    usuario_anulo = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='recibos_anulados',
        verbose_name="Usuario que Anuló"
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Anulación")

    class Meta:
        verbose_name = "Recibo de Pago"
        verbose_name_plural = "Recibos de Pago"
        ordering = ['-fecha', '-numero_recibo'] # Ordenar por fecha más reciente

    def __str__(self):
        return f"Recibo N° {self.numero_recibo} - {self.nombre}"

    def get_categorias_marcadas(self):
        """Devuelve una lista de los nombres de las categorías marcadas."""
        categorias = []
        for i in range(1, 11):
            campo = f'categoria{i}'
            if getattr(self, campo):
                categorias.append(MAPEO_CATEGORIAS.get(i))
        return ", ".join(categorias)