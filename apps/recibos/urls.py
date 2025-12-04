from django.urls import path
from . import views

# Define el namespace de la app 'recibos'
app_name = 'recibos'

urlpatterns = [
    # ------------------------------------------------------------------
    # 1. Rutas de Recibos y Archivos
    # ------------------------------------------------------------------
    
    # Lista de recibos activos y búsqueda (Ruta principal)
    path('', views.receipt_list_view, name='receipt_list'), 
    
    # Creación manual de un nuevo recibo
    path('create/', views.receipt_create_view, name='receipt_create'),
    
    # Carga de archivo Excel
    path('upload/', views.upload_file_view, name='upload_file'),
    
    # Generación y descarga de PDF
    path('pdf/<int:receipt_id>/', views.generate_pdf_view, name='generate_pdf'),
    
    # Rutas CRUD y Soft Delete de Recibos
    path('edit/<int:receipt_id>/', views.receipt_edit_view, name='receipt_edit'),
    path('anulate/<int:receipt_id>/', views.receipt_anulate_view, name='receipt_anulate'),
    path('anulated/', views.anulated_receipts_view, name='anulated_receipts'), 
    
    # NUEVA RUTA DE REPORTE CONSOLIDADO
    path('report/consolidated/', views.generate_consolidated_report, name='consolidated_report'),
    
    # ------------------------------------------------------------------
    # 2. Rutas de Gestión de Usuarios - ADMINISTRADORES
    # ------------------------------------------------------------------
    
    path('users/', views.user_management_view, name='user_management'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:user_id>/toggle/', views.user_toggle_active_view, name='user_toggle_active'), 
    path('users/<int:user_id>/password/', views.user_password_change_view, name='user_password_change'),
    path('upload/', views.upload_file_view, name='upload_file'),
]
