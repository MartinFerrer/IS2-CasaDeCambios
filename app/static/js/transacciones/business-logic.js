/**
 * Módulo de lógica de negocio para transacciones
 *
 * Este módulo contiene funciones para manejar la lógica específica
 * del negocio de cambio de divisas, incluyendo tipos de operación,
 * actualización de etiquetas y carga de divisas.
 */

/**
 * Módulo getTipoOperacion - Determinación del tipo de operación
 *
 * Determina el tipo de operación (compra/venta) basado en las divisas
 * seleccionadas por el usuario en el formulario.
 *
 * Args:
 *   divisaOrigenId (string): ID de la divisa de origen
 *   divisaDestinoId (string): ID de la divisa de destino
 *
 * Retorna:
 *   string: 'compra' si se compra USD con PYG, 'venta' si se vende USD por PYG
 *
 * Lógica de negocio:
 *   - Compra: PYG → USD (cliente entrega guaraníes, recibe dólares)
 *   - Venta: USD → PYG (cliente entrega dólares, recibe guaraníes)
 */
function getTipoOperacion(divisaOrigenId, divisaDestinoId) {
    const divisaOrigen = document.getElementById(divisaOrigenId).value;
    const divisaDestino = document.getElementById(divisaDestinoId).value;

    // Lógica específica: PYG a USD = compra, USD a PYG = venta
    if (divisaOrigen === 'PYG' && divisaDestino === 'USD') {
        return 'compra';
    } else if (divisaOrigen === 'USD' && divisaDestino === 'PYG') {
        return 'venta';
    }

    // Fallback para otros casos (aunque actualmente solo manejamos PYG/USD)
    return 'compra';
}

/**
 * Módulo updateLabels - Actualización dinámica de etiquetas del formulario
 *
 * Actualiza las etiquetas de los campos de formulario basándose en el
 * tipo de operación y las divisas seleccionadas.
 *
 * Args:
 *   tipoOperacion (string): 'compra' o 'venta'
 *   divisaOrigen (string): Código de la divisa origen (ej: 'PYG', 'USD')
 *   divisaDestino (string): Código de la divisa destino
 *   labelElements (object): Objeto con referencias a elementos de etiquetas
 *
 * Retorna:
 *   void: Función de efecto secundario que modifica DOM
 *
 * Ejemplos:
 *   updateLabels('compra', 'PYG', 'USD', {
 *     montoLabel: document.getElementById('monto-label'),
 *     resultadoLabel: document.getElementById('resultado-label')
 *   })
 */
function updateLabels(tipoOperacion, divisaOrigen, divisaDestino, labelElements) {
    const {
        montoLabel,
        resultadoLabel,
        tipoOperacionLabel,
        comisionLabel
    } = labelElements;

    // Actualizar etiqueta del tipo de operación
    if (tipoOperacionLabel) {
        tipoOperacionLabel.textContent = tipoOperacion.charAt(0).toUpperCase() + tipoOperacion.slice(1);
    }

    // Actualizar etiqueta del monto según divisa origen
    if (montoLabel) {
        montoLabel.textContent = `Monto en ${divisaOrigen}:`;
    }

    // Actualizar etiqueta del resultado según divisa destino
    if (resultadoLabel) {
        resultadoLabel.textContent = `Recibirás en ${divisaDestino}:`;
    }

    // Actualizar etiqueta de comisión
    if (comisionLabel) {
        const accionComision = tipoOperacion === 'compra' ? 'pago' : 'cobro';
        comisionLabel.textContent = `Comisión de ${accionComision}:`;
    }
}

/**
 * Módulo loadDivisas - Carga de divisas disponibles
 *
 * Carga la lista de divisas disponibles desde el servidor y actualiza
 * los elementos select del formulario.
 *
 * Args:
 *   selectElements (array): Array de elementos select a actualizar
 *   apiEndpoint (string): URL del endpoint para obtener divisas
 *   defaultValues (object): Valores por defecto para cada select
 *
 * Retorna:
 *   Promise<boolean>: Promise que resuelve true si carga exitosa, false si error
 *
 * Efectos secundarios:
 *   - Actualiza opciones de elementos select
 *   - Establece valores por defecto
 *   - Dispara eventos 'change' en selects actualizados
 */
async function loadDivisas(selectElements, apiEndpoint = '/api/divisas/', defaultValues = {}) {
    try {
        const response = await fetch(apiEndpoint);

        if (!response.ok) {
            throw new Error(`Error HTTP: ${response.status}`);
        }

        const divisas = await response.json();

        // Actualizar cada elemento select
        selectElements.forEach((selectElement, index) => {
            if (!selectElement) return;

            // Limpiar opciones existentes
            selectElement.innerHTML = '';

            // Agregar opción por defecto
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = 'Selecciona una divisa';
            defaultOption.disabled = true;
            defaultOption.selected = true;
            selectElement.appendChild(defaultOption);

            // Agregar opciones de divisas
            divisas.forEach(divisa => {
                const option = document.createElement('option');
                option.value = divisa.codigo;
                option.textContent = `${divisa.codigo} - ${divisa.nombre}`;
                selectElement.appendChild(option);
            });

            // Establecer valor por defecto si se proporciona
            const defaultKey = selectElement.id;
            if (defaultValues[defaultKey]) {
                selectElement.value = defaultValues[defaultKey];
                selectElement.dispatchEvent(new Event('change'));
            }
        });

        return true;

    } catch (error) {
        console.error('Error cargando divisas:', error);

        // Mostrar mensaje de error en los selects
        selectElements.forEach(selectElement => {
            if (!selectElement) return;

            selectElement.innerHTML = '<option disabled>Error cargando divisas</option>';
        });

        return false;
    }
}

/**
 * Módulo calculateExchangeAmount - Cálculo de monto de cambio
 *
 * Calcula el monto resultante del cambio de divisas aplicando
 * la tasa de cambio y las comisiones correspondientes.
 *
 * Args:
 *   montoOrigen (number): Monto en divisa origen
 *   tasaCambio (number): Tasa de cambio aplicable
 *   tipoOperacion (string): 'compra' o 'venta'
 *   comisiones (object): Objeto con porcentajes de comisión
 *
 * Retorna:
 *   object: {
 *     montoDestino: number,
 *     comisionTotal: number,
 *     tasaEfectiva: number,
 *     detalles: object
 *   }
 */
function calculateExchangeAmount(montoOrigen, tasaCambio, tipoOperacion, comisiones = {}) {
    if (!montoOrigen || !tasaCambio) {
        return {
            montoDestino: 0,
            comisionTotal: 0,
            tasaEfectiva: 0,
            detalles: {}
        };
    }

    // Calcular comisión total
    const comisionPorcentaje = comisiones[tipoOperacion] || 0;
    const comisionTotal = montoOrigen * (comisionPorcentaje / 100);

    // Calcular monto neto después de comisión
    const montoNeto = montoOrigen - comisionTotal;

    // Aplicar tasa de cambio
    const montoDestino = montoNeto * tasaCambio;

    // Calcular tasa efectiva (incluyendo comisión)
    const tasaEfectiva = montoDestino / montoOrigen;

    return {
        montoDestino: Math.round(montoDestino * 100) / 100,
        comisionTotal: Math.round(comisionTotal * 100) / 100,
        tasaEfectiva: Math.round(tasaEfectiva * 10000) / 10000,
        detalles: {
            montoOriginal: montoOrigen,
            montoNeto: Math.round(montoNeto * 100) / 100,
            comisionPorcentaje,
            tasaCambio
        }
    };
}

// Exportar funciones para uso en otros módulos
window.TransaccionesBusinessLogic = {
    getTipoOperacion,
    updateLabels,
    loadDivisas,
    calculateExchangeAmount
};
