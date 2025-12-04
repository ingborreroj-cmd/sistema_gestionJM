from django.shortcuts import redirect
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# ====================================================================
# Decorador de Requerimiento de Administrador
# ====================================================================

def admin_required(view_func):
    """
    Decorador para restringir el acceso a una vista solo a usuarios
    que tengan la propiedad 'is_admin' en True.
    
    Requiere que el usuario esté autenticado.
    """
    
    @login_required(login_url='login')
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Asume que el modelo de usuario tiene la propiedad is_admin
        if request.user.is_admin:
            return view_func(request, *args, **kwargs)
        else:
            # Mensaje para el usuario no autorizado
            messages.error(request, "Acceso denegado. Se requiere un rol de Administrador para esta función.")
            # Redirigir a una página segura (por ejemplo, la lista de recibos)
            return redirect('recibos:receipt_list')

    return _wrapped_view