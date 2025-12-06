# recibos/urls.py

from django.urls import path
from . import views # Asume que tus vistas están en recibos/views.py

urlpatterns = [
    # 1. Rutas Principales de CRUD
    path('', views.dashboard_view, name='dashboard'), # Dashboard/Listado principal
    path('crear/', views.recibo_create_view, name='recibo_create'),
    # Usa <int:pk> para identificar el recibo en la URL
    path('<int:pk>/', views.recibo_detail_view, name='recibo_detail'),
    
    # 2. Rutas de Documentos Individuales
    # Esta URL usa el ID del recibo para generar el PDF.
    path('<int:pk>/pdf/', views.recibo_pdf_view, name='recibo_pdf'), 

    # 3. Rutas de Procesamiento y Reportes Masivos
    path('cargar/excel/', views.cargar_excel_view, name='cargar_excel'),
    path('reportes/excel/', views.reporte_excel_view, name='reporte_excel'),
    path('reportes/pdf/', views.reporte_pdf_view, name='reporte_pdf'),
]