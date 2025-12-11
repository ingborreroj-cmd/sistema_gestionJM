from django.urls import path
from . import views

app_name = 'recibos'

urlpatterns = [
    # 1. Dashboard Principal (CORREGIDO: Apunta a la clase ReciboListView)
    path(
        '', 
        views.ReciboListView.as_view(), # <--- CORRECCIÓN APLICADA
        name='dashboard'
    ),

    # 2. Generación de Reportes Masivos (Se mantiene la función generar_reporte_view)
    path(
        'generar-reporte/', 
        views.generar_reporte_view, 
        name='generar_reporte'
    ),

    # 3. Flujo de Descarga Individual de PDF (Se mantiene)
    path(
        'descargar-init/<int:pk>/',
        views.init_download_and_refresh,
        name='init_download'
    ),

    # 4. Generación y Envío del PDF Individual Puro (Se mantiene)
    path(
        'generar-pdf/<int:pk>/',
        views.generar_pdf_recibo,
        name='generar_pdf_recibo'
    ),
]