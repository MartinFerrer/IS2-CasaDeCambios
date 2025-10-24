"""Módulo de cálculo de comisiones para transacciones.

Este módulo contiene funciones unificadas para calcular comisiones
de pago y cobro en transacciones de cambio de divisas.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Optional, Tuple


def calculate_commission(
    tipo_operacion: str, metodo_pago: str, monto: Decimal, comisiones_config: Dict[str, Any]
) -> Tuple[Decimal, str]:
    """Módulo calculate_commission - Cálculo unificado de comisiones.

    Calcula la comisión aplicable según el tipo de operación y método de pago,
    unificando la lógica previamente duplicada en _get_payment_commission
    y _get_collection_commission.

    Args:
        tipo_operacion (str): 'compra' o 'venta'
        metodo_pago (str): Método de pago/cobro usado
        monto (Decimal): Monto base para calcular comisión
        comisiones_config (Dict): Configuración de comisiones del sistema

    Retorna:
        Tuple[Decimal, str]: (monto_comision, metodo_usado)

    Ejemplos:
        >>> config = {'tarjeta_credito': 3.5, 'cuenta_bancaria': 1.0}
        >>> calculate_commission('compra', 'tarjeta_credito', Decimal('1000'), config)
        (Decimal('35.00'), 'tarjeta_credito')

    """
    # Mapeo de métodos a configuraciones
    metodo_mapping = {
        "tarjeta_credito": "tarjeta_credito",
        "tarjeta_debito": "tarjeta_debito",
        "cuenta_bancaria": "cuenta_bancaria",
        "cuenta_corriente": "cuenta_corriente",
        "billetera_digital": "billetera_digital",
        "billetera_electronica": "billetera_electronica",
    }

    # Obtener configuración de comisión
    metodo_config = metodo_mapping.get(metodo_pago)
    if not metodo_config or metodo_config not in comisiones_config:
        return Decimal("0.00"), metodo_pago

    # Calcular comisión como porcentaje
    porcentaje_comision = Decimal(str(comisiones_config[metodo_config]))
    comision = (monto * porcentaje_comision / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return comision, metodo_config


def get_payment_commission(metodo_pago: str, monto: Decimal) -> Decimal:
    """Módulo get_payment_commission - Comisión de métodos de pago.

    Calcula la comisión para métodos de pago en operaciones de compra,
    refactorizado para usar la lógica unificada de calculate_commission.

    Args:
        metodo_pago (str): Método de pago utilizado
        monto (Decimal): Monto base de la transacción

    Retorna:
        Decimal: Monto de comisión a aplicar

    """
    # Configuración específica para métodos de pago
    comisiones_pago = {
        "tarjeta_credito": 3.5,  # 3.5%
        "tarjeta_debito": 2.0,  # 2.0%
        "cuenta_bancaria": 1.0,  # 1.0%
        "cuenta_corriente": 1.5,  # 1.5%
        "billetera_digital": 2.5,  # 2.5%
        "billetera_electronica": 2.5,  # 2.5%
    }

    comision, _ = calculate_commission("compra", metodo_pago, monto, comisiones_pago)
    return comision


def get_collection_commission(metodo_cobro: str, monto: Decimal) -> Decimal:
    """Módulo get_collection_commission - Comisión de métodos de cobro.

    Calcula la comisión para métodos de cobro en operaciones de venta,
    refactorizado para usar la lógica unificada de calculate_commission.

    Args:
        metodo_cobro (str): Método de cobro utilizado
        monto (Decimal): Monto base de la transacción

    Retorna:
        Decimal: Monto de comisión a aplicar

    """
    # Configuración específica para métodos de cobro
    comisiones_cobro = {
        "tarjeta_credito": 3.0,  # 3.0%
        "tarjeta_debito": 1.8,  # 1.8%
        "cuenta_bancaria": 0.8,  # 0.8%
        "cuenta_corriente": 1.2,  # 1.2%
        "billetera_digital": 2.2,  # 2.2%
        "billetera_electronica": 2.2,  # 2.2%
    }

    comision, _ = calculate_commission("venta", metodo_cobro, monto, comisiones_cobro)
    return comision


def get_commission_breakdown(tipo_operacion: str, metodo: str, monto: Decimal) -> Dict[str, Any]:
    """Módulo get_commission_breakdown - Desglose detallado de comisión.

    Proporciona un desglose completo del cálculo de comisión incluyendo
    porcentajes, montos y detalles del método utilizado.

    Args:
        tipo_operacion (str): 'compra' o 'venta'
        metodo (str): Método de pago/cobro
        monto (Decimal): Monto base

    Retorna:
        Dict[str, Any]: Desglose completo con porcentajes y cálculos

    Ejemplo de retorno:
        {
            'monto_base': Decimal('1000.00'),
            'metodo': 'tarjeta_credito',
            'porcentaje': Decimal('3.5'),
            'comision': Decimal('35.00'),
            'monto_neto': Decimal('965.00'),
            'tipo_operacion': 'compra'
        }

    """
    if tipo_operacion == "compra":
        comision = get_payment_commission(metodo, monto)
        config = {
            "tarjeta_credito": 3.5,
            "tarjeta_debito": 2.0,
            "cuenta_bancaria": 1.0,
            "cuenta_corriente": 1.5,
            "billetera_digital": 2.5,
            "billetera_electronica": 2.5,
        }
    else:  # venta
        comision = get_collection_commission(metodo, monto)
        config = {
            "tarjeta_credito": 3.0,
            "tarjeta_debito": 1.8,
            "cuenta_bancaria": 0.8,
            "cuenta_corriente": 1.2,
            "billetera_digital": 2.2,
            "billetera_electronica": 2.2,
        }

    porcentaje = Decimal(str(config.get(metodo, 0)))
    monto_neto = monto - comision

    return {
        "monto_base": monto,
        "metodo": metodo,
        "porcentaje": porcentaje,
        "comision": comision,
        "monto_neto": monto_neto,
        "tipo_operacion": tipo_operacion,
        "descripcion": f"Comisión {porcentaje}% por {metodo.replace('_', ' ')}",
    }


def validate_commission_calculation(tipo_operacion: str, metodo: str, monto: Decimal) -> Optional[str]:
    """Módulo validate_commission_calculation - Validación de parámetros.

    Valida que los parámetros para el cálculo de comisión sean válidos
    y estén dentro de los rangos esperados.

    Args:
        tipo_operacion (str): 'compra' o 'venta'
        metodo (str): Método de pago/cobro
        monto (Decimal): Monto base

    Retorna:
        Optional[str]: Mensaje de error si hay problemas, None si es válido

    """
    # Validar tipo de operación
    if tipo_operacion not in ["compra", "venta"]:
        return f"Tipo de operación inválido: {tipo_operacion}"

    # Validar método
    metodos_validos = [
        "tarjeta_credito",
        "tarjeta_debito",
        "cuenta_bancaria",
        "cuenta_corriente",
        "billetera_digital",
        "billetera_electronica",
    ]
    if metodo not in metodos_validos:
        return f"Método inválido: {metodo}"

    # Validar monto
    if monto <= 0:
        return f"Monto debe ser positivo: {monto}"

    if monto > Decimal("1000000"):  # Límite arbitrario de seguridad
        return f"Monto excede límite máximo: {monto}"

    return None  # Todo válido
