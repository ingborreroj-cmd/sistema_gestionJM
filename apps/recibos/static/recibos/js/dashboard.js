// =================================================================
// 1. VARIABLES GLOBALES Y UTILIDADES
// =================================================================

// Elementos del Modal
const modal = document.getElementById('confirmation-modal');
const modalContent = document.getElementById('modal-content');
const modalTitle = document.getElementById('modal-title');
const modalMessage = document.getElementById('modal-message');
const confirmButton = document.getElementById('confirm-action-button');

// Elementos de Carga
const fileInput = document.getElementById('excel-file-input');
const uploadStatus = document.getElementById('upload-status');
const triggerUploadButton = document.getElementById('trigger-upload-button');
const uploadForm = document.getElementById('upload-form');
const logDisplay = document.getElementById('log-display');

// Formularios Ocultos
const anularForm = document.getElementById('anular-form');
const clearLogsForm = document.getElementById('clear-logs-form'); 

// Nuevo Botón de Logs Visuales
const clearVisualLogsButton = document.getElementById('clear-visual-logs-button');

let currentFormToSubmit = null; // Variable para rastrear qué formulario debe enviarse

// =================================================================
// 2. FUNCIONES DEL MODAL (Hechas globales para acceso en HTML)
// =================================================================

window.showModal = function(title, messageHtml, confirmText, targetAction, confirmColor) {
    modalTitle.textContent = title;

    // Formatear mensaje para negritas
    const formattedMessage = messageHtml.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    modalMessage.innerHTML = formattedMessage;
    confirmButton.textContent = confirmText;

    // Aplicar color y resetear clases
    confirmButton.className = 'px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white transition duration-150';
    if (confirmColor === 'red') {
        confirmButton.classList.add('bg-red-600', 'hover:bg-red-700');
    } else if (confirmColor === 'gray') {
        confirmButton.classList.add('bg-gray-500', 'hover:bg-gray-600');
    } else if (confirmColor === 'yellow') {
        confirmButton.classList.add('bg-yellow-600', 'hover:bg-yellow-700');
    } else if (confirmColor === 'indigo') {
        confirmButton.classList.add('bg-indigo-600', 'hover:bg-indigo-700');
    }

    // Asignar la acción para el manejador unificado de click
    confirmButton.setAttribute('data-action-type', targetAction);

    // Lógica para deshabilitar o cambiar texto si es "solo informativo"
    const isInfoOnly = (targetAction === 'info'); // Corregido: usa targetAction
    confirmButton.disabled = isInfoOnly;

    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.style.opacity = '1';
        modalContent.classList.remove('scale-95', 'opacity-0');
        modalContent.classList.add('scale-100', 'opacity-100');
    }, 10);

    modal.onclick = function(event) {
        if (event.target === modal) {
            window.hideModal();
        }
    };
}

window.hideModal = function() {
    modalContent.classList.remove('scale-100', 'opacity-100');
    modalContent.classList.add('scale-95', 'opacity-0');
    modal.style.opacity = '0';
    setTimeout(() => {
        modal.classList.add('hidden');
        currentFormToSubmit = null; // Limpiar la referencia al formulario
    }, 300);
}

// =================================================================
// 3. MANEJO DE ESTADO DE CARGA (FEEDBACK VISUAL)
// =================================================================

function setLoadingState(isLoading, fileName = '') {
    if (isLoading) {
        // Guardar el HTML original
        triggerUploadButton.dataset.originalHtml = triggerUploadButton.innerHTML;

        // Cambiar a estado de carga
        triggerUploadButton.disabled = true;
        triggerUploadButton.classList.add('opacity-75', 'cursor-wait');
        triggerUploadButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Procesando...';
        
        // Agregar log
        if (logDisplay) {
            logDisplay.innerHTML += `<p class="text-yellow-700">[${new Date().toLocaleTimeString()}] Iniciando carga y procesamiento de ${fileName}...</p>`;
            logDisplay.scrollTop = logDisplay.scrollHeight;
        }

    } else {
        // Restaurar estado normal
        // Ya no es necesario manejar el estado de disabled aquí, lo hace updateUploadButtonState
        triggerUploadButton.classList.remove('opacity-75', 'cursor-wait');

        // Restaurar el texto original si existe
        if (triggerUploadButton.dataset.originalHtml) {
            triggerUploadButton.innerHTML = triggerUploadButton.dataset.originalHtml;
        }
        
        // Sincronizar estado del botón con el archivo actual
        updateUploadButtonState(fileInput.files.length > 0);
    }
}

function updateUploadButtonState(hasFile) {
    if (hasFile) {
        triggerUploadButton.disabled = false;
        triggerUploadButton.classList.remove('bg-yellow-600', 'hover:bg-yellow-700');
        triggerUploadButton.classList.add('bg-indigo-600', 'hover:bg-indigo-700');
        triggerUploadButton.innerHTML = '<i class="fas fa-upload mr-2"></i> **CARGAR** Datos Excel';
    } else {
        triggerUploadButton.disabled = true;
        triggerUploadButton.classList.remove('bg-indigo-600', 'hover:bg-indigo-700');
        triggerUploadButton.classList.add('bg-yellow-600', 'hover:bg-yellow-700');
        triggerUploadButton.innerHTML = '<i class="fas fa-arrow-up mr-2"></i> Cargar Datos Excel'; //Texto original
    }
}


// =================================================================
// 4. EVENTOS (DOMContentLoaded)
// =================================================================

document.addEventListener('DOMContentLoaded', function() {

    // --- A. Inicialización y Limpieza de Estado ---
    setLoadingState(false); 
    updateUploadButtonState(fileInput.files.length > 0);

    const hasErrorMessages = document.querySelector('.bg-red-100');
    if (hasErrorMessages && fileInput) {
        fileInput.value = ''; 
        updateUploadButtonState(false);
        uploadStatus.textContent = 'Ningún archivo seleccionado.';
        uploadStatus.classList.remove('text-indigo-600', 'font-semibold');
        uploadStatus.classList.add('text-gray-500');
    }
    
    // --- B. Manejo de Carga de Archivos ---
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const hasFile = e.target.files.length > 0;
            if (hasFile) {
                uploadStatus.textContent = 'Archivo listo para cargar: ' + e.target.files[0].name;
                uploadStatus.classList.remove('text-gray-500');
                uploadStatus.classList.add('text-indigo-600', 'font-semibold');
            } else {
                uploadStatus.textContent = 'Ningún archivo seleccionado.';
                uploadStatus.classList.remove('text-indigo-600', 'font-semibold');
                uploadStatus.classList.add('text-gray-500');
            }
            updateUploadButtonState(hasFile);
        });
    }

    // --- C. Clic en Botón de Carga (triggerUploadButton) ---
    if (triggerUploadButton && uploadForm) {
        triggerUploadButton.addEventListener('click', function() {
            if (fileInput.files.length > 0) {
                currentFormToSubmit = uploadForm;
                
                // Muestra modal de confirmación antes de enviar
                window.showModal(
                    'Confirmación de Carga Masiva',
                    `¿Estás seguro que deseas **cargar los recibos del archivo Excel "${fileInput.files[0].name}"**? Esto creará nuevos registros de forma masiva.`,
                    'Sí, Cargar Excel',
                    'upload', // Identificador de acción
                    'indigo'
                );
            } else {
                // Mensaje informativo (Función pendiente)
                window.showModal(
                    'Acción Inválida',
                    'Por favor, selecciona un archivo Excel primero. (La creación/modificación individual se maneja en la tabla de resultados).',
                    'Entendido',
                    'info',
                    'yellow'
                );
            }
        });
    }

    // --- D. Clic en Botón Anular Recibo (Tabla) ---
    document.querySelectorAll('.anular-recibo-btn').forEach(button => {
        button.addEventListener('click', function() {
            const reciboId = this.getAttribute('data-recibo-id');
            document.getElementById('anular-recibo-id').value = reciboId;
            currentFormToSubmit = anularForm; // Referencia al formulario oculto

            window.showModal(
                'Confirmar Anulación',
                this.getAttribute('data-message'),
                this.getAttribute('data-confirm-text'),
                'anular', // Identificador de acción
                this.getAttribute('data-color')
            );
        });
    });

    // --- F. Clic en Botón Limpiar Logs (Visual) ---
    if (clearVisualLogsButton) {
        clearVisualLogsButton.addEventListener('click', function() {
            window.showModal(
                'Confirmar Limpieza de Logs',
                this.dataset.message,
                this.dataset.confirmText,
                'clear_visual_logs', // Identificador de acción
                this.dataset.color
            );
        });
    }

    // --- G. Manejo de Filtros Automáticos ---
    document.querySelectorAll('#estado, #fecha_inicio, #fecha_fin').forEach(element => {
        element.addEventListener('change', function() {
            document.getElementById('filter-form').submit();
        });
    });

    // --- H. Auto-descarte de Mensajes de Éxito ---
    const successMessages = document.querySelectorAll('.bg-green-100');
    successMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transition = 'opacity 0.5s ease-out';
            setTimeout(() => {
                message.remove();
            }, 500);
        }, 5000); 
    });

});

// =================================================================
// 5. MANEJADOR ÚNICO DE CLICK EN EL BOTÓN DE CONFIRMACIÓN DEL MODAL
// =================================================================

confirmButton.addEventListener('click', function() {
    const actionType = this.getAttribute('data-action-type');

    if (actionType === 'clear_visual_logs') {
        // Limpieza de logs visuales (no necesita submit de formulario)
        if (logDisplay) {
            logDisplay.innerHTML = `<p class="text-gray-400">[${new Date().toLocaleTimeString()}] Logs visuales limpiados.</p>`;
            logDisplay.scrollTop = 0;
        }
        window.hideModal();
    } 
    else if (actionType === 'info') {
        // Botón 'Entendido' (solo es informativo)
        window.hideModal();
    }
    else if (currentFormToSubmit && !this.disabled) {
        // Acciones que requieren envío de formulario (Anular, Limpiar BD, Carga Excel)
        
        if (actionType === 'upload') {
            // Lógica especial para la carga de Excel: feedback visual ANTES de submit
            const fileName = fileInput.files.length > 0 ? fileInput.files[0].name : '';
            window.hideModal(); // Ocultar antes de submit para ver el spinner
            setLoadingState(true, fileName);
            
            // Retraso pequeño para asegurar que el DOM se actualice (spinner/log) antes de la navegación
            setTimeout(() => {
                currentFormToSubmit.submit();
            }, 50); 
        } else {
            // Anular
            currentFormToSubmit.submit();
            window.hideModal(); 
        }
    }
});

// 🛑 Bloque G de Modificar eliminado, se asume que se usa un <a> en el HTML.