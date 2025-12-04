from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.contrib import messages
from django.db.models import Max, Q 
from django.utils import timezone 
from django.contrib.auth import logout # <-- Importación necesaria para cerrar sesión

# Importaciones necesarias para el proyecto (Asumiendo que existen)
from .models import Receipt, CustomUser 
from .decorators import admin_required
from .forms import UploadFileForm, CustomUserCreationForm, AdminPasswordChangeForm, ReceiptForm 
# Asegúrate de que todas estas funciones de utilidad estén disponibles
from .utils import clean, is_marked, format_date_for_db, generate_receipt_pdf, process_uploaded_excel, get_next_receipt_number 
import pandas as pd
import io 
from datetime import datetime

# Número inicial para la secuencia de recibos si no hay ninguno en la DB
INITIAL_RECEIPT_NUMBER = 10000000

# ====================================================================
# Funciones Auxiliares
# ====================================================================

def get_next_receipt_number():
    """Calcula el siguiente número de recibo consecutivo."""
    max_number_query = Receipt.objects.aggregate(Max('receipt_number'))['receipt_number__max']
    
    try:
        if max_number_query:
            # Asegura la conversión y suma
            last_number = int(max_number_query)
            return str(last_number + 1)
        else:
            return str(INITIAL_RECEIPT_NUMBER)
    except ValueError:
        # En una vista real, se usaría messages.error(request, ...)
        print("Error en la secuencia de recibos. Se restablecerá al número inicial.")
        return str(INITIAL_RECEIPT_NUMBER)

def apply_filters(request, queryset):
    """
    FASE 4.1: Aplica todos los filtros (búsqueda, rango de fechas, estado, categorías) al queryset.
    """
    
    # --- Búsqueda de Texto Parcial (Q objects: ILIKE) ---
    search_query = request.GET.get('q', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(client_name__icontains=search_query) |
            Q(client_id__icontains=search_query) |
            Q(transaction_number__icontains=search_query) |
            Q(receipt_number__icontains=search_query)
        )

    # --- Filtrado por Rango de Fechas ---
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')
    
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            queryset = queryset.filter(payment_date__gte=date_from)
        except ValueError:
            messages.error(request, "Formato de fecha de inicio inválido.")

    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
            # Se suma un día para hacer el rango inclusivo hasta el final del día 'date_to'
            date_to_inclusive = date_to + timezone.timedelta(days=1)
            queryset = queryset.filter(payment_date__lt=date_to_inclusive)
        except ValueError:
            messages.error(request, "Formato de fecha final inválido.")

    # --- Filtrado por Estado (Activo/Anulado) ---
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        queryset = queryset.filter(anulado=False)
    elif status_filter == 'anulated':
        queryset = queryset.filter(anulado=True)

    # --- Filtrado por Categorías (Booleanas) ---
    for i in range(1, 11):
        cat_field = f'categoria{i}'
        cat_value = request.GET.get(cat_field)
        
        # Evalúa si la categoría está marcada ('on' o '1' son valores comunes de GET)
        if cat_value in ['on', '1']: 
            queryset = queryset.filter(**{cat_field: True})
            
    return queryset


# ====================================================================
# 1. Vistas de Recibos y Archivos (FASE 1, 3, y 4)
# ====================================================================

@admin_required # Solo administradores pueden subir archivos masivos
def upload_file_view(request):
    """
    [FASE 1] Carga de archivo Excel y procesamiento de recibos.
    """
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['file']
            
            # Llamar a la función de utilidad para procesar el Excel
            success_count, error_count = process_uploaded_excel(excel_file, request.user)
            
            if success_count > 0:
                messages.success(request, f"¡Carga completada! Se procesaron {success_count} recibos exitosamente.")
            
            if error_count > 0:
                messages.warning(request, f"Se encontraron {error_count} errores al procesar algunos recibos. Por favor, revise el archivo.")
            
            # Redirige a la lista principal después de la carga
            return redirect('recibos:receipt_list')
        else:
            messages.error(request, "Error en el formulario de carga. Por favor, revise el tipo de archivo.")
    else:
        form = UploadFileForm()
    
    context = {'form': form, 'page_title': 'Cargar Archivo de Recibos'}
    return render(request, 'recibos/upload_file.html', context)


@admin_required
def receipt_create_view(request):
    """
    [FASE 3.2] Vista para la creación manual de un nuevo recibo.
    """
    if request.method == 'POST':
        form = ReceiptForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    receipt = form.save(commit=False)
                    
                    # Asignar campos que no están en el formulario
                    receipt.created_by = request.user
                    
                    # Asignar número de recibo consecutivo
                    receipt.receipt_number = get_next_receipt_number() 
                    
                    receipt.save()
                    messages.success(request, f"El Recibo N° {receipt.receipt_number} ha sido creado exitosamente.")
                    return redirect('recibos:receipt_list')
            except Exception as e:
                # Se recomienda loguear el error para depuración
                print(f"Error durante la creación de recibo: {e}") 
                messages.error(request, f"Error al guardar el recibo. Detalle: {e}")
        else:
            messages.error(request, "Error en el formulario. Por favor, revise los campos.")
    else:
        # GET request: prepara el formulario
        form = ReceiptForm()
        
    context = {
        'form': form,
        'page_title': 'Crear Nuevo Recibo Manual',
    }
    # Reutilizamos la plantilla de edición
    return render(request, 'recibos/receipt_edit.html', context)


@login_required(login_url='login')
def receipt_list_view(request):
    """
    [FASE 4.1] Vista para listar todos los recibos y aplicar filtrado avanzado.
    """
    receipts_query = Receipt.objects.all()
    
    # Mostrar solo los recibos creados por el usuario, si no es admin
    if not request.user.is_admin:
        receipts_query = receipts_query.filter(created_by=request.user)
    
    # Aplicar Filtros (Búsqueda, Fechas, Categorías)
    receipts_query = apply_filters(request, receipts_query)
    
    # Ordenar y Ejecutar
    receipts = receipts_query.order_by('-payment_date', '-receipt_number')
    
    # Obtener los parámetros de búsqueda actuales para mantenerlos en el formulario
    current_filters = {k: v for k, v in request.GET.items()}

    context = {
        'receipts': receipts,
        'current_filters': current_filters,
        # Indica si se ha aplicado algún filtro (útil para mostrar mensajes de "resultados filtrados")
        'is_filtered_view': bool(current_filters) 
    }
    return render(request, 'recibos/receipt_list.html', context)


@login_required(login_url='login')
def receipt_edit_view(request, receipt_id):
    """
    [FASE 3.1] Vista para editar un recibo existente.
    """
    receipt = get_object_or_404(Receipt, pk=receipt_id)
    
    # Restricción de permisos: solo Admin o Creador puede editar
    if not request.user.is_admin and request.user != receipt.created_by:
        messages.error(request, "No tienes permiso para editar este recibo.")
        return redirect('recibos:receipt_list')

    # No se puede editar un recibo anulado
    if receipt.anulado:
        messages.warning(request, "No se puede editar un recibo que ha sido anulado.")
        return redirect('recibos:receipt_list')
        
    if request.method == 'POST':
        form = ReceiptForm(request.POST, instance=receipt)
        if form.is_valid():
            form.save()
            messages.success(request, f"Recibo N° {receipt.receipt_number} actualizado correctamente.")
            return redirect('recibos:receipt_list')
    else:
        form = ReceiptForm(instance=receipt)

    context = {
        'form': form,
        'receipt': receipt,
        'page_title': f'Editar Recibo N° {receipt.receipt_number}',
    }
    return render(request, 'recibos/receipt_edit.html', context)


@admin_required
def receipt_anulate_view(request, receipt_id):
    """
    [FASE 3.3] Vista para anular o reactivar un recibo. Requiere permisos de Admin.
    """
    receipt = get_object_or_404(Receipt, pk=receipt_id)

    # El cambio de estado ocurre solo si es POST
    if request.method == 'POST':
        # Determinar la nueva acción
        if receipt.anulado:
            # Reactivar: setear anulado a False y limpiar campos de anulación
            receipt.anulado = False
            receipt.usuario_anulo = None
            receipt.fecha_anulacion = None
            message = f"Recibo N° {receipt.receipt_number} ha sido reactivado."
        else:
            # Anular: setear anulado a True y registrar usuario/fecha
            receipt.anulado = True
            receipt.usuario_anulo = request.user
            receipt.fecha_anulacion = timezone.now()
            message = f"Recibo N° {receipt.receipt_number} ha sido ANULADO."

        try:
            # Usamos transaction.atomic() para asegurar que el cambio se guarde correctamente
            with transaction.atomic():
                receipt.save()
            messages.success(request, message)
        except Exception as e:
            messages.error(request, f"Error al guardar el cambio: {e}")

        return redirect('recibos:receipt_list')
    
    # Renderizar la página de confirmación (si es GET)
    context = {
        'receipt': receipt,
        'action': 'Reactivar' if receipt.anulado else 'Anular',
    }
    return render(request, 'recibos/receipt_anulate_confirm.html', context)


@admin_required
def anulated_receipts_view(request):
    """
    [FASE 3.4] Vista de auditoría: Lista solo los recibos ANULADOS.
    """
    anulated_receipts = Receipt.objects.filter(anulado=True).order_by('-fecha_anulacion', '-receipt_number')
    
    context = {
        'receipts': anulated_receipts,
        'page_title': 'Historial de Recibos Anulados',
    }
    return render(request, 'recibos/receipt_list.html', context)


@login_required(login_url='login')
def generate_pdf_view(request, receipt_id):
    """
    [FASE 1] Genera el PDF de un recibo específico.
    """
    receipt = get_object_or_404(Receipt, pk=receipt_id)

    # Restricción de permisos: solo Admin o Creador puede generar el PDF
    if not request.user.is_admin and request.user != receipt.created_by:
        messages.error(request, "No tienes permiso para descargar este recibo.")
        return redirect('recibos:receipt_list')

    try:
        # Asegúrate de que 'generate_receipt_pdf' devuelve el contenido binario del PDF
        pdf_file = generate_receipt_pdf(receipt)
        
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f"Recibo_{receipt.receipt_number}.pdf"
        # Usar 'attachment' para forzar la descarga en lugar de mostrar en el navegador
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, f"Error al generar el PDF: {e}")
        return redirect('recibos:receipt_list')


# ====================================================================
# 2. Vista de Reporte Consolidado (FASE 4.3)
# ====================================================================

@login_required(login_url='login')
def generate_consolidated_report(request):
    """
    [FASE 4.3] Genera un archivo Excel consolidado basado en los filtros de la URL.
    """
    receipts_query = Receipt.objects.all()
    
    if not request.user.is_admin:
        receipts_query = receipts_query.filter(created_by=request.user)
        
    # Aplicar Filtros de la URL
    filtered_receipts = apply_filters(request, receipts_query)

    # Generar DataFrame a partir de los datos filtrados
    data = list(filtered_receipts.values(
        'receipt_number', 'transaction_number', 'payment_date', 'client_id', 'client_name',
        'amount', 'concept', 'client_address', 'created_by__username', 
        'anulado', 'usuario_anulo__username', 'fecha_anulacion',
        'categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5',
        'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10'
    ))
    
    # Es recomendable verificar si hay datos antes de crear el DataFrame
    if not data:
        messages.warning(request, "No se encontraron recibos para los filtros seleccionados.")
        return redirect('recibos:receipt_list')
        
    df = pd.DataFrame(data)

    # Renombrar columnas para el reporte final (Español)
    df = df.rename(columns={
        'receipt_number': 'Nº Recibo',
        'transaction_number': 'Nº Transferencia',
        'payment_date': 'Fecha de Pago',
        'client_id': 'RIF/CI',
        'client_name': 'Nombre del Cliente',
        'amount': 'Monto',
        'concept': 'Concepto',
        'client_address': 'Dirección',
        'created_by__username': 'Creado Por',
        'anulado': 'Anulado',
        'usuario_anulo__username': 'Anulado Por',
        'fecha_anulacion': 'Fecha Anulación',
    })
    
    # Formatear datos y columnas booleanas
    df['Anulado'] = df['Anulado'].apply(lambda x: 'Sí' if x else 'No')
    df['Monto'] = df['Monto'].round(2)
    
    # Renombrar columnas de categorías y asignar valores 'X'
    for i in range(1, 11):
        col_name = f'categoria{i}'
        df[col_name] = df[col_name].apply(lambda x: 'X' if x else '')
        df.rename(columns={col_name: f'Cat{i}'}, inplace=True)

    # Generar respuesta HTTP con el archivo Excel
    output = io.BytesIO()
    # Usar el manejador de contexto de ExcelWriter
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Reporte de Recibos', index=False)
        
    output.seek(0)
    
    response = HttpResponse(
        output.read(), 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    filename = f"Reporte_Recibos_Consolidado_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ====================================================================
# 3. Vistas de Gestión de Usuarios (FASE 2)
# ====================================================================

@admin_required
def user_management_view(request):
    """
    [FASE 2.4] Lista todos los usuarios (excluyendo el Admin Principal) para su gestión.
    """
    users = CustomUser.objects.exclude(is_superuser=True).order_by('username')
    return render(request, 'recibos/user_management.html', {'users': users})

@admin_required
def user_create_view(request):
    """
    [FASE 2.4] Creación de nuevos usuarios.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Usuario '{user.username}' creado exitosamente.")
            return redirect('recibos:user_management')
    else:
        form = CustomUserCreationForm()
    
    context = {'form': form, 'page_title': 'Crear Nuevo Usuario'}
    return render(request, 'recibos/user_form.html', context)


@admin_required
def user_toggle_active_view(request, user_id):
    """
    [FASE 2.4] Activar/Desactivar un usuario.
    """
    user_to_toggle = get_object_or_404(CustomUser, pk=user_id)
    
    if user_to_toggle.is_superuser:
        messages.error(request, "No puedes desactivar al superusuario principal.")
        return redirect('recibos:user_management')
        
    if request.method == 'POST':
        # Usar transaction.atomic() para garantizar la atomicidad
        with transaction.atomic():
            user_to_toggle.is_active = not user_to_toggle.is_active
            user_to_toggle.save()
        
        status = "activado" if user_to_toggle.is_active else "desactivado"
        messages.success(request, f"Usuario '{user_to_toggle.username}' ha sido {status}.")
    
    return redirect('recibos:user_management')


@admin_required
def user_password_change_view(request, user_id):
    """
    [FASE 2.5] Cambio de contraseña de un usuario por el Admin.
    """
    user_to_change = get_object_or_404(CustomUser, pk=user_id)
    
    if request.method == 'POST':
        form = AdminPasswordChangeForm(user_to_change, request.POST)
        if form.is_valid():
            # La función save() del formulario ya actualiza la contraseña hasheada
            form.save()
            
            messages.success(request, f"Contraseña del usuario '{user_to_change.username}' actualizada exitosamente.")
            return redirect('recibos:user_management')
    else:
        form = AdminPasswordChangeForm(user_to_change)

    context = {
        'form': form, 
        'page_title': f"Cambiar Contraseña: {user_to_change.username}"
    }
    return render(request, 'recibos/user_form.html', context)


# ====================================================================
# 4. Vistas de Autenticación (FASE 5)
# ====================================================================

def user_logout_view(request):
    """
    [FASE 5.1] Cierra la sesión del usuario y lo redirige a la página de inicio de sesión.
    """
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "Has cerrado sesión correctamente.")
    
    # Redirige a la URL de login. Asume que el nombre de tu URL de login es 'login'.
    # Si tienes la URL de login dentro de la app 'recibos' (ej. 'recibos:login'), usa ese nombre.
    return redirect('login')