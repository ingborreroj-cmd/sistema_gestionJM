# Configuración de login
LOGIN_REDIRECT_URL = '/clientes/'  # Donde va después de login
LOGOUT_REDIRECT_URL = '/accounts/login/'  # Donde va después de logout
LOGIN_URL = '/accounts/login/'

# Para desarrollo - quitar en producción
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'