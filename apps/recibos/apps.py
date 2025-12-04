from django.apps import AppConfig

class RecibosConfig(AppConfig):
    # Nombre de la aplicación que usaremos internamente (el nombre de la carpeta)
    name = 'apps.recibos' 
    # Etiqueta corta para referencias (usado en las tablas: recibos_...)
    label = 'recibos' 
    verbose_name = 'Gestión de Recibos'