# recibos/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile # No se usa, pero se puede dejar.
from datetime import date
from decimal import Decimal
import io

# Importación de librería externa
import openpyxl # <-- Se mueve al inicio

# Importaciones de Django
from django.db.models import Q 

# Importaciones relativas de la aplicación
from recibos.utils import procesar_excel_sync, obtener_recibos_filtrados
from recibos.models import Recibo 

User = get_user_model()


# ====================================================================
# --- 1. PRUEBAS DE PROCESAMIENTO DE EXCEL (utils.procesar_excel_sync)
# ====================================================================

class ReciboUtilsTests(TestCase):
    def setUp(self):
        # 1. Creamos un usuario de prueba
        self.user = User.objects.create_user(username='testuser', password='password123')
        
        # 2. Preparamos un archivo Excel de prueba en memoria (BytesIO)
        self.output = io.BytesIO()
        self.workbook = openpyxl.Workbook()
        self.hoja = self.workbook.active
        
        # 3. Encabezado del archivo (Debe coincidir con utils.py)
        self.hoja.append([
            'N° Recibo', 'Estado', 'Nombre', 'RIF/Cédula', 'Dirección', 
            'Ente Liquidado', 'Gastos Adm', 'Tasa Día', 'Total Monto (Bs)', 
            'N° Transferencia', 'Conciliado', 'Fecha', 'Concepto', 
            'Categoría 1', 'Categoría 2', 'Categoría 3', 'Categoría 4'
        ])
        
        # 4. Datos de prueba para una CREACIÓN (R1000)
        self.hoja.append([
            'R1000', 'Pagado', 'Juan Perez', '12345678', 'Av Principal', 
            'ENTE A', 10.00, 35.50, 1000.00, 
            'TRANSF123', 'Sí', date(2023, 10, 15), 'Pago de servicio', 
            'Sí', 'No', 1, 0
        ])
        
        # 5. Datos de prueba para una ACTUALIZACIÓN (R1001)
        self.hoja.append([
            'R1001', 'Pendiente', 'Maria López', '98765432', 'Calle 5', 
            'ENTE B', 5.00, 36.00, 500.00, 
            'TRANSF456', 'No', date(2023, 10, 16), 'Abono inicial', 
            'No', 'Sí', 'No', 'Sí'
        ])
        
        # Creamos R1001 ANTES para que la carga lo actualice (update_or_create)
        Recibo.objects.create(
            numero_recibo='R1001',
            nombre='Maria López (Old)',
            total_monto_bs=Decimal('400.00'),
            tasa_dia=Decimal('30.00'),
            usuario_creador=self.user,
            fecha=date(2023, 1, 1),
        )

        # Guardar y mover el puntero al inicio
        self.workbook.save(self.output)
        self.output.seek(0)

    def test_excel_processing_creates_and_updates_recibos(self):
        """Verifica que el procesador cree R1000 y actualice R1001 correctamente."""
        resumen = procesar_excel_sync(self.output.read(), self.user)
        
        self.assertEqual(resumen['total_procesados'], 2)
        self.assertEqual(resumen['nuevos_recibos'], 1, "Solo R1000 debe ser creado, R1001 actualizado.")
        
        # 1. Verificación de CREACIÓN (R1000)
        r1000 = Recibo.objects.get(numero_recibo='R1000')
        self.assertEqual(r1000.nombre, 'Juan Perez')
        self.assertEqual(r1000.total_monto_bs, Decimal('1000.00'))
        self.assertEqual(r1000.gastos_administrativos, Decimal('10.00'))
        self.assertTrue(r1000.categoria1)
        self.assertFalse(r1000.categoria4) 
        
        # 2. Verificación de ACTUALIZACIÓN (R1001)
        r1001 = Recibo.objects.get(numero_recibo='R1001')
        self.assertEqual(r1001.nombre, 'Maria López') # Actualizado
        self.assertEqual(r1001.total_monto_bs, Decimal('500.00')) # Actualizado
        self.assertEqual(r1001.fecha, date(2023, 10, 16)) # Actualizado
        self.assertTrue(r1001.categoria2)
        self.assertTrue(r1001.categoria4)


# ====================================================================
# --- 2. PRUEBAS DE FILTRADO (utils.obtener_recibos_filtrados)
# ====================================================================

class ReciboFiltradoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        
        # Creación de datos base
        self.r001 = Recibo.objects.create(numero_recibo='R001', estado='Pagado', fecha=date(2023, 10, 1), 
                              categoria1=True, categoria2=False, anulado=False, 
                              total_monto_bs=Decimal('100'), usuario_creador=self.user)
                              
        self.r002 = Recibo.objects.create(numero_recibo='R002', estado='Conciliado', fecha=date(2023, 10, 15), 
                              categoria1=False, categoria2=True, categoria3=True, anulado=False,
                              total_monto_bs=Decimal('200'), usuario_creador=self.user)
                              
        self.r003 = Recibo.objects.create(numero_recibo='R003', estado='Pagado', fecha=date(2023, 10, 30), 
                              categoria1=False, categoria2=False, anulado=True,
                              total_monto_bs=Decimal('300'), usuario_creador=self.user)

    def test_filtro_rango_fechas(self):
        """Verifica el filtro por fecha (debe excluir R003)."""
        qs = obtener_recibos_filtrados(
            fecha_inicio=date(2023, 10, 1), 
            fecha_fin=date(2023, 10, 15), 
            estado_filtro=None, 
            categorias_filtro=None
        )
        self.assertEqual(qs.count(), 2)
        self.assertTrue(qs.filter(numero_recibo='R001').exists())

    def test_filtro_estado_anulado(self):
        """Verifica que el filtro 'anulado' retorne solo R003."""
        qs = obtener_recibos_filtrados(None, None, 'anulado', None)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().numero_recibo, 'R003')

    def test_filtro_estado_especifico(self):
        """Verifica que el filtro 'Pagado' retorne solo R001 (excluye R003 por ser anulado)."""
        qs = obtener_recibos_filtrados(None, None, 'Pagado', None)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().numero_recibo, 'R001')

    def test_filtro_categorias_or(self):
        """Verifica la lógica OR en las categorías (Cat 1 O Cat 3)."""
        qs = obtener_recibos_filtrados(None, None, None, ['1', '3']) 
        self.assertEqual(qs.count(), 2)
        self.assertTrue(qs.filter(numero_recibo='R001').exists())
        self.assertTrue(qs.filter(numero_recibo='R002').exists())

    def test_filtro_combinado(self):
        """Verifica un filtro complejo: Activo AND Fecha AND (Cat 1 O Cat 3)."""
        qs = obtener_recibos_filtrados(
            fecha_inicio=None, 
            fecha_fin=date(2023, 10, 15), 
            estado_filtro='activo', # No anulado
            categorias_filtro=['1', '3']
        )
        # R001 (Activo, 01/10, Cat 1) - OK
        # R002 (Activo, 15/10, Cat 3) - OK
        # R003 (Anulado) - Falla
        self.assertEqual(qs.count(), 2)