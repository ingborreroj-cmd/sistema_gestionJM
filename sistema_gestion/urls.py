from django.contrib import admin
from django.urls import path, include

# 1. Importación de la vista global del proyecto (landing_page_view).
# Esta línea ahora funciona gracias a la creación de sistema_gestion/views.py.
from . import views 

# Nota: Eliminamos 'from django.views.generic.base import RedirectView' 
# porque ya no se utiliza en ninguna parte.

urlpatterns = [
    # *****************************************************************
    # 1. RUTA RAÍZ PÚBLICA (Menú de Aplicaciones)
    # CRÍTICO: Debe ser la primera para evitar la redirección al login.
    # *****************************************************************
    path('', views.landing_page_view, name='landing'), 

    # 2. Rutas del Administrador
    path('admin/', admin.site.urls),

    # *****************************************************************
    # 3. RUTAS MODULARIZADAS DE LA APP 'RECIBOS'
    # Delega todo el tráfico bajo '/recibos/' a su propio archivo.
    # *****************************************************************
    path('recibos/', include('apps.recibos.urls', namespace='recibos')), 

    # *****************************************************************
    # 4. RUTAS DE AUTENTICACIÓN (UNIFICADAS Y MODULARIZADAS)
    # Incluye /login/, /logout/, /password_change/, etc.
    # *****************************************************************
    # IMPORTANTE: Esta regla incluye la ruta raíz ('') pero es evaluada 
    # DESPUÉS de la regla de 'landing', por lo que solo se activa 
    # cuando Django necesita resolver una URL de autenticación.
    path('', include('django.contrib.auth.urls')),
]