from django.urls import path
from . import views

app_name = 'recibos'

urlpatterns = [
    # 1. RUTA PRINCIPAL (Única)
    # 🛑 CORRECCIÓN: Usamos la función que SÍ existe y que unifica toda la lógica.
    # El 'name' de la URL debe ser 'dashboard' porque es la referencia que usaste en tu HTML.
    path('', views.crear_recibo_desde_excel, name='dashboard'), 
    
    # 🛑 NOTA: Eliminamos las rutas duplicadas e innecesarias (dashboard, upload, crear-recibo)
    # Si realmente necesitas otras rutas, confírmalo, pero para tu objetivo principal, esta es la única necesaria.
]