/**
 * Módulo de formateo de números y monedas para transacciones
 *
 * Este módulo contiene funciones utilitarias para formatear números,
 * tasas de cambio y procesar inputs numéricos en formato latinoamericano.
 */

/**
 * Módulo formatNumber - Formateo de números con separadores de miles y decimales
 *
 * Formatea un número según la divisa especificada usando formato latinoamericano
 * (espacios como separadores de miles, coma como separador decimal).
 * Elimina ceros decimales finales innecesarios.
 *
 * Args:
 *   value (number|string): Valor numérico a formatear
 *   currency (string): Código de divisa (PYG, USD, EUR, BRL) para determinar decimales
 *
 * Retorna:
 *   string: Número formateado con espacios como separadores de miles y coma decimal
 *
 * Ejemplos:
 *   formatNumber(1234567.89, "USD") → "1 234 567,89"
 *   formatNumber(1234567.00, "USD") → "1 234 567"
 *   formatNumber(1234567.50, "USD") → "1 234 567,5"
 *   formatNumber(1234567, "PYG") → "1 234 567"
 */
function formatNumber(value, currency) {
    const isoDecimals = { PYG: 0, USD: 2, EUR: 2, BRL: 2 };
    const dec = isoDecimals[currency] !== undefined ? isoDecimals[currency] : 2;
    const num = Number(value);
    if (!isFinite(num)) return value;

    // Obtener representación con decimales máximos
    let strNum = num.toFixed(dec);

    // Eliminar ceros decimales finales y punto/coma si es necesario
    if (dec > 0) {
        strNum = strNum.replace(/\.?0+$/, '');
    }

    // Separar la parte entera y decimal
    const [integerPart, decimalPart] = strNum.split('.');

    // Formatear parte entera con espacios como separadores de miles
    const formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');

    // Combinar con coma como separador decimal
    if (decimalPart) {
        return `${formattedInteger},${decimalPart}`;
    } else {
        return formattedInteger;
    }
}

/**
 * Módulo formatRate - Formateo de tasas de cambio con precisión optimizada
 *
 * Formatea una tasa de cambio mostrando decimales necesarios y eliminando
 * ceros finales para mayor legibilidad.
 *
 * Args:
 *   rate (number|string): Tasa de cambio a formatear
 *
 * Retorna:
 *   string: Tasa formateada en formato latinoamericano sin ceros finales
 *
 * Ejemplos:
 *   formatRate(7450.00000) → "7 450"
 *   formatRate(7450.123456) → "7 450,123456"
 */
function formatRate(rate) {
    const num = Number(rate);
    if (!isFinite(num)) return rate;

    // Obtener representación con suficientes decimales
    let s = num.toFixed(12);
    // Quitar ceros finales y punto si corresponde
    s = s.replace(/(?:\.0+|(?<=\.[0-9]*?)0+)$/, '');

    // Convertir a formato latinoamericano
    const [integerPart, decimalPart] = s.split('.');
    const formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');

    if (decimalPart) {
        return `${formattedInteger},${decimalPart}`;
    } else {
        return formattedInteger;
    }
}

/**
 * Módulo parseInputNumber - Conversión de input latinoamericano a número
 *
 * Convierte un input en formato latinoamericano (espacios y comas) a un
 * número JavaScript válido para cálculos.
 *
 * Args:
 *   value (string): Valor de input en formato latinoamericano
 *
 * Retorna:
 *   number: Número JavaScript parseado, 0 si no es válido
 *
 * Ejemplos:
 *   parseInputNumber("1 234,56") → 1234.56
 *   parseInputNumber("1234") → 1234
 *   parseInputNumber("") → 0
 */
function parseInputNumber(value) {
    if (!value) return 0;
    // Remover espacios (separadores de miles) y reemplazar coma por punto
    const normalized = value.replace(/\s/g, '').replace(',', '.');
    return parseFloat(normalized) || 0;
}

/**
 * Módulo formatInputNumber - Formateo en tiempo real de inputs numéricos
 *
 * Formatea un input mientras el usuario escribe, aplicando separadores
 * de miles y limitando decimales a 2 dígitos.
 *
 * Args:
 *   value (string): Valor actual del input
 *
 * Retorna:
 *   string: Valor formateado para mostrar en el input
 *
 * Ejemplos:
 *   formatInputNumber("1234567") → "1 234 567"
 *   formatInputNumber("1234,567") → "1 234,56"
 */
function formatInputNumber(value) {
    if (!value) return '';

    // Limpiar valor: solo números y una coma
    let cleanValue = value.replace(/[^\d,]/g, '');

    // Asegurar solo una coma
    const commaIndex = cleanValue.indexOf(',');
    if (commaIndex !== -1) {
        const beforeComma = cleanValue.substring(0, commaIndex);
        const afterComma = cleanValue.substring(commaIndex + 1).replace(/,/g, '');
        cleanValue = beforeComma + ',' + afterComma;
    }

    // Separar parte entera y decimal
    const [integerPart, decimalPart] = cleanValue.split(',');

    // Formatear parte entera con espacios
    const formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');

    // Limitar decimales a 2 dígitos
    if (decimalPart !== undefined) {
        const limitedDecimal = decimalPart.substring(0, 2);
        return `${formattedInteger},${limitedDecimal}`;
    } else {
        return formattedInteger;
    }
}

// Exportar funciones para uso en otros módulos
window.TransaccionesFormatters = {
    formatNumber,
    formatRate,
    parseInputNumber,
    formatInputNumber
};
