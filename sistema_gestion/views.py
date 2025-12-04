from django.shortcuts import render

# La única vista que pertenece al proyecto principal (no a una app específica).

def landing_page_view(request):
    """
    Renderiza la página principal del sistema, que ahora contiene 
    directamente el menú de aplicaciones, ya que base.html es la única plantilla usada.
    """
    # Renderiza 'base.html'. Dado que base.html contiene todo el menú, 
    # esta es la vista de la página de inicio.
    return render(request, 'base.html')