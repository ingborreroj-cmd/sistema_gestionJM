from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from django.contrib.auth import views as auth_views
from apps.recibos import views

# Esta configuración es correcta para enlazar los nombres de URL de settings.py
# (LOGIN_URL = 'login') con las vistas de autenticación de Django.

urlpatterns = [
    # 1. Ruta de Administración de Django
    path('admin/', admin.site.urls),

    # 2. Rutas de la Aplicación Principal 'recibos'
    # Esta ruta raíz redirige a la URL con nombre 'recibos:receipt_list'.
    # Si el usuario NO está logueado, esta redirección disparará el @login_required
    # de la vista, llevándolo a '/login/'.
    path('', RedirectView.as_view(pattern_name='recibos:receipt_list', permanent=False)),
    path('recibos/', include('apps.recibos.urls')), 

    # 3. Rutas de Autenticación de Django
    # Usa las plantillas en templates/auth/
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # 4. Rutas de cambio de contraseña para el usuario regular
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='auth/password_change_form.html',
        success_url='/password_change/done/' 
    ), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='auth/password_change_done.html'
    ), name='password_change_done'),
    path('logout/', views.user_logout_view, name='logout'), # <-- ¡Añade esto!  
]