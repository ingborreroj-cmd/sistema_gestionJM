from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Página principal - redirige al login
    path('', auth_views.LoginView.as_view(template_name='registration/login.html'), name='home'),
    
    # URLs de autenticación
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Admin de Django
    path('admin/', admin.site.urls),
    
    # Tu app de clientes
    # path('clientes/', include('apps.clientes.urls')),
]

# Para archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)