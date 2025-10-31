/**
 * Módulo de validación de inputs para transacciones
 *
 * Este módulo contiene funciones para validar inputs numéricos,
 * manejar errores de validación y aplicar estilos de DaisyUI.
 */

/**
 * Módulo validateIntegerInput - Validación de números enteros en inputs
 *
 * Valida que un input contenga solo números enteros y maneja la
 * visualización de errores usando componentes de DaisyUI.
 *
 * Args:
 *   inputElement (HTMLElement): Elemento input a validar
 *   errorElement (HTMLElement): Elemento para mostrar mensaje de error
 *   value (string): Valor actual del input
 *
 * Retorna:
 *   boolean: true si es válido, false si hay error
 *
 * Efectos secundarios:
 *   - Modifica clases CSS del input (input-bordered/input-error)
 *   - Muestra/oculta mensaje de error
 */
function validateIntegerInput(inputElement, errorElement, value) {
    // Validar si es un número entero usando regex más estricta
    const isValid = !value || /^[0-9]+$/.test(value);

    if (!isValid) {
        // Mostrar error y cambiar estilo del input
        errorElement.classList.remove('hidden');
        inputElement.classList.remove('input-bordered');
        inputElement.classList.add('input-error');
        return false;
    } else {
        // Ocultar error y restaurar estilo normal
        errorElement.classList.add('hidden');
        inputElement.classList.remove('input-error');
        inputElement.classList.add('input-bordered');
        return true;
    }
}

/**
 * Módulo validateIntegerInputAdvanced - Validación avanzada con Number.isInteger
 *
 * Validación alternativa usando Number.isInteger para mayor precisión
 * en la detección de números enteros vs decimales.
 *
 * Args:
 *   inputElement (HTMLElement): Elemento input a validar
 *   errorElement (HTMLElement): Elemento para mostrar mensaje de error
 *   value (string): Valor actual del input
 *
 * Retorna:
 *   boolean: true si es válido, false si hay error
 */
function validateIntegerInputAdvanced(inputElement, errorElement, value) {
    // Validar si es un número entero usando Number.isInteger
    const isValid = !value || Number.isInteger(parseFloat(value));

    if (!isValid) {
        // Mostrar error y cambiar estilo del input
        errorElement.classList.remove('hidden');
        inputElement.classList.remove('input-bordered');
        inputElement.classList.add('input-error');
        return false;
    } else {
        // Ocultar error y restaurar estilo normal
        errorElement.classList.add('hidden');
        inputElement.classList.remove('input-error');
        inputElement.classList.add('input-bordered');
        return true;
    }
}

/**
 * Módulo setupIntegerValidation - Configuración automática de validación
 *
 * Configura automáticamente la validación de enteros para un input,
 * incluyendo event listeners y elementos de error.
 *
 * Args:
 *   inputId (string): ID del elemento input
 *   errorId (string): ID del elemento de error
 *   validationMethod (string): 'regex' o 'advanced' para tipo de validación
 *   onValidChange (function): Callback opcional cuando cambia validez
 *
 * Retorna:
 *   object: Objeto con métodos para controlar la validación
 *
 * Ejemplos:
 *   setupIntegerValidation('monto-input', 'monto-error', 'regex', () => performSimulation())
 */
function setupIntegerValidation(inputId, errorId, validationMethod = 'regex', onValidChange = null) {
    const inputElement = document.getElementById(inputId);
    const errorElement = document.getElementById(errorId);

    if (!inputElement || !errorElement) {
        console.error(`Elementos no encontrados: ${inputId} o ${errorId}`);
        return null;
    }

    const validateFunction = validationMethod === 'advanced' ?
        validateIntegerInputAdvanced : validateIntegerInput;

    let isCurrentlyValid = true;

    function handleInput(e) {
        const value = e.target.value;
        const wasValid = isCurrentlyValid;
        isCurrentlyValid = validateFunction(inputElement, errorElement, value);

        // Llamar callback solo si la validez cambió
        if (onValidChange && wasValid !== isCurrentlyValid) {
            onValidChange(isCurrentlyValid, value);
        }

        // Siempre llamar callback si es válido (para actualizaciones en tiempo real)
        if (onValidChange && isCurrentlyValid) {
            onValidChange(true, value);
        }
    }

    inputElement.addEventListener('input', handleInput);

    return {
        isValid: () => isCurrentlyValid,
        validate: () => validateFunction(inputElement, errorElement, inputElement.value),
        destroy: () => inputElement.removeEventListener('input', handleInput)
    };
}

// Exportar funciones para uso en otros módulos
window.TransaccionesValidators = {
    validateIntegerInput,
    validateIntegerInputAdvanced,
    setupIntegerValidation
};
