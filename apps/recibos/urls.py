from django.urls import path
from . import views # Asegúrese de que views.py contenga la clase ReciboListView

app_name = 'recibos'

urlpatterns = [
    # 1. Dashboard Principal
    # AHORA USA ReciboListView.as_view()
    path(
        '', 
        views.ReciboListView.as_view(), 
        name='dashboard'
    ),

    # 2. Generación de Reportes Masivos
    path(
        'generar-reporte/', 
        views.generar_reporte_view, 
        name='generar_reporte'
    ),

    # 3. Flujo de Descarga Individual de PDF 
    path(
        'descargar-init/<int:pk>/',
        views.init_download_and_refresh,
        name='init_download'
    ),

    # 4. Generación y Envío del PDF Individual Puro
    path(
        'generar-pdf/<int:pk>/',
        views.generar_pdf_recibo,
        name='generar_pdf_recibo'
    ),
]