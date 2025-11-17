from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    context = {
        'titulo': 'Dashboard Principal - Desarrollo',
        'modulos': [
            {'nombre': 'Clientes', 'url': 'clientes:index', 'icono': 'users'},
            {'nombre': 'Sellos Dorados', 'url': 'sellos:index', 'icono': 'stamp'},
            {'nombre': 'Contratos', 'url': 'contratos:index', 'icono': 'file-contract'},
            {'nombre': 'Seguimiento Pagos', 'url': 'pagos:index', 'icono': 'money-bill-wave'},
            {'nombre': 'Recibos', 'url': 'recibos:index', 'icono': 'receipt'},
            {'nombre': 'Expedientes', 'url': 'expedientes:index', 'icono': 'folder'},
        ]
    }
    return render(request, 'dashboard.html', context)

def dashboard(request):
    return HttpResponse("""
    <h1>¡Sistema de Gestión Documental funcionando!</h1>
    <p>El servidor Django está ejecutándose correctamente.</p>
    <ul>
        <li><a href="/admin/">Panel de Administración</a></li>
        <li><a href="/">Página Principal</a></li>
    </ul>
    """)