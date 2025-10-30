"""Módulo de cálculo de tasas y comisiones para transacciones.

Este módulo contiene funciones unificadas para calcular tasas y comisiones
de pago y cobro en transacciones de cambio de divisas.
Reglas:
- Todos los montos en PYG se redondean a enteros
- Las tasas siempre se almacenan en BD como PYG -> Divisa Extranjera
- Casa COMPRA divisa: precio_base - comision_compra
- Casa VENDE divisa: precio_base + comision_venta
"""

from decimal import Decimal
from typing import Dict, Optional, Tuple

from django.conf import settings

# ==============================================================================
# FUNCIONES DE TASAS BASE (SIN DESCUENTO)
# ==============================================================================


def calcular_tasa_compra_base(precio_base: Decimal, comision_compra: Decimal) -> Decimal:
    """Calcula la tasa cuando la casa COMPRA divisa del cliente.

    Cuando el cliente VENDE divisa a la casa, aplicamos comision_compra.
    La casa compra más barato: precio_base - comision_compra

    Args:
        precio_base: Precio base de la tasa de cambio
        comision_compra: Comisión de compra

    Returns:
        Tasa de compra (Decimal)

    """
    return precio_base - comision_compra


def calcular_tasa_venta_base(precio_base: Decimal, comision_venta: Decimal) -> Decimal:
    """Calcula la tasa cuando la casa VENDE divisa al cliente.

    Cuando el cliente COMPRA divisa de la casa, aplicamos comision_venta.
    La casa vende más caro: precio_base + comision_venta

    Args:
        precio_base: Precio base de la tasa de cambio
        comision_venta: Comisión de venta

    Returns:
        Tasa de venta (Decimal)

    """
    return precio_base + comision_venta


# ==============================================================================
# FUNCIONES DE COMISIONES EFECTIVAS (CON DESCUENTO)
# ==============================================================================


def calcular_comision_efectiva(comision_base: Decimal, descuento_porcentaje: Decimal) -> Decimal:
    """Calcula la comisión efectiva aplicando descuento por segmento de cliente.

    Args:
        comision_base: Comisión base (compra o venta)
        descuento_porcentaje: Descuento del segmento del cliente (0-100)

    Returns:
        Comisión efectiva con descuento aplicado (Decimal)

    """
    return comision_base - (comision_base * descuento_porcentaje / Decimal("100"))


def calcular_tasa_compra_efectiva(
    precio_base: Decimal, comision_compra: Decimal, descuento_porcentaje: Decimal
) -> Decimal:
    """Calcula la tasa de compra efectiva con descuento aplicado.

    Args:
        precio_base: Precio base de la tasa
        comision_compra: Comisión de compra base
        descuento_porcentaje: Descuento del cliente (0-100)

    Returns:
        Tasa de compra efectiva (Decimal)

    """
    comision_efectiva = calcular_comision_efectiva(comision_compra, descuento_porcentaje)
    return precio_base - comision_efectiva


def calcular_tasa_venta_efectiva(
    precio_base: Decimal, comision_venta: Decimal, descuento_porcentaje: Decimal
) -> Decimal:
    """Calcula la tasa de venta efectiva con descuento aplicado.

    Args:
        precio_base: Precio base de la tasa
        comision_venta: Comisión de venta base
        descuento_porcentaje: Descuento del cliente (0-100)

    Returns:
        Tasa de venta efectiva (Decimal)

    """
    comision_efectiva = calcular_comision_efectiva(comision_venta, descuento_porcentaje)
    return precio_base + comision_efectiva


# ==============================================================================
# FUNCIONES DE CONVERSIÓN DE MONTOS
# ==============================================================================


def convertir_a_pyg(monto_divisa: Decimal, tasa: Decimal) -> int:
    """Convierte monto de divisa extranjera a PYG usando la tasa dada.

    Args:
        monto_divisa: Cantidad de divisa extranjera
        tasa: Tasa de cambio a aplicar

    Returns:
        Monto en PYG redondeado a entero

    """
    resultado = monto_divisa * tasa
    return round(resultado)


def convertir_compra_a_pyg(
    monto_divisa: Decimal, precio_base: Decimal, comision_venta: Decimal, descuento_porcentaje: Decimal = Decimal("0.0")
) -> Tuple[int, Decimal, Decimal]:
    """Convierte monto cuando el cliente COMPRA divisa (casa VENDE).

    Args:
        monto_divisa: Cantidad de divisa extranjera que el cliente desea comprar
        precio_base: Precio base de la tasa
        comision_venta: Comisión de venta base
        descuento_porcentaje: Descuento del cliente (0-100)

    Returns:
        Tupla (monto_pyg: int, tasa_efectiva: Decimal, comision_efectiva: Decimal)

    """
    comision_efectiva = calcular_comision_efectiva(comision_venta, descuento_porcentaje)
    tasa_efectiva = precio_base + comision_efectiva
    monto_pyg = convertir_a_pyg(monto_divisa, tasa_efectiva)
    return monto_pyg, tasa_efectiva, comision_efectiva


def convertir_venta_a_pyg(
    monto_divisa: Decimal,
    precio_base: Decimal,
    comision_compra: Decimal,
    descuento_porcentaje: Decimal = Decimal("0.0"),
) -> Tuple[int, Decimal, Decimal]:
    """Convierte monto cuando el cliente VENDE divisa (casa COMPRA).

    Args:
        monto_divisa: Cantidad de divisa extranjera que el cliente vende
        precio_base: Precio base de la tasa
        comision_compra: Comisión de compra base
        descuento_porcentaje: Descuento del cliente (0-100)

    Returns:
        Tupla (monto_pyg: int, tasa_efectiva: Decimal, comision_efectiva: Decimal)

    """
    comision_efectiva = calcular_comision_efectiva(comision_compra, descuento_porcentaje)
    tasa_efectiva = precio_base - comision_efectiva
    monto_pyg = convertir_a_pyg(monto_divisa, tasa_efectiva)
    return monto_pyg, tasa_efectiva, comision_efectiva


# ==============================================================================
# FUNCIONES DE COMISIONES DE MEDIOS DE PAGO/COBRO
# ==============================================================================


def calcular_comision_porcentual(monto: Decimal, porcentaje: Decimal) -> int:
    """Calcula comisión porcentual sobre un monto en PYG.

    Args:
        monto: Monto base en PYG
        porcentaje: Porcentaje de comisión (ej: 2.5 para 2.5%)

    Returns:
        Comisión en PYG redondeada a entero

    """
    comision = monto * porcentaje / Decimal("100")
    return round(comision)


def obtener_comision_fija_stripe_pyg() -> int:
    """Obtiene la comisión fija de Stripe convertida a PYG.

    Usa settings.STRIPE_FIXED_FEE_USD y lo convierte a PYG usando la tasa USD actual.

    Returns:
        Comisión fija en PYG redondeada a entero

    Raises:
        ValueError: Si no se encuentra la tasa USD o hay error en la configuración

    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        from apps.operaciones.models import TasaCambio

        # Obtener comisión fija en USD desde settings
        if not hasattr(settings, "STRIPE_FIXED_FEE_USD"):
            logger.error("STRIPE_FIXED_FEE_USD no está configurado en settings")
            raise ValueError("Configuración de Stripe incompleta")

        fixed_fee_usd = Decimal(str(settings.STRIPE_FIXED_FEE_USD))

        # Obtener tasa USD actual
        tasa_usd = TasaCambio.objects.filter(
            divisa_origen__codigo="PYG", divisa_destino__codigo="USD", activo=True
        ).first()

        if not tasa_usd:
            logger.error("No se encontró tasa de cambio activa para USD")
            raise ValueError("No existe tasa de cambio activa para USD")

        # Convertir a PYG
        comision_pyg = fixed_fee_usd * tasa_usd.precio_base
        return round(comision_pyg)

    except Exception as e:
        logger.error(f"Error al obtener comisión fija de Stripe: {e!s}")
        raise


def calcular_comision_medio_pago(monto_pyg: int, porcentaje_comision: Decimal, es_stripe: bool = False) -> int:
    """Calcula la comisión total del medio de pago.

    Args:
        monto_pyg: Monto en PYG sobre el cual calcular comisión
        porcentaje_comision: Porcentaje de comisión del medio
        es_stripe: Si True, agrega comisión fija de Stripe

    Returns:
        Comisión total en PYG redondeada a entero

    """
    comision_porcentual = calcular_comision_porcentual(Decimal(str(monto_pyg)), porcentaje_comision)

    if es_stripe:
        comision_fija = obtener_comision_fija_stripe_pyg()
        return comision_porcentual + comision_fija

    return comision_porcentual


def calcular_comision_medio_cobro(monto_pyg: int, porcentaje_comision: Decimal) -> int:
    """Calcula la comisión del medio de cobro.

    Args:
        monto_pyg: Monto en PYG sobre el cual calcular comisión
        porcentaje_comision: Porcentaje de comisión del medio

    Returns:
        Comisión en PYG redondeada a entero

    """
    return calcular_comision_porcentual(Decimal(str(monto_pyg)), porcentaje_comision)


# ==============================================================================
# FUNCIONES DE TOTALES
# ==============================================================================


def calcular_total_compra(monto_convertido_pyg: int, comision_medio_pago_pyg: int) -> int:
    """Calcula el total a pagar en una operación de COMPRA.

    Args:
        monto_convertido_pyg: Monto convertido a PYG (sin comisión de medio)
        comision_medio_pago_pyg: Comisión del medio de pago en PYG

    Returns:
        Total en PYG a pagar (entero)

    """
    return monto_convertido_pyg + comision_medio_pago_pyg


def calcular_total_venta(monto_convertido_pyg: int, comision_medio_cobro_pyg: int) -> int:
    """Calcula el total a recibir en una operación de VENTA.

    Args:
        monto_convertido_pyg: Monto convertido a PYG (sin comisión de medio)
        comision_medio_cobro_pyg: Comisión del medio de cobro en PYG

    Returns:
        Total en PYG a recibir (entero)

    """
    return monto_convertido_pyg - comision_medio_cobro_pyg


# ==============================================================================
# FUNCIONES AUXILIARES PARA OBTENER DATOS DE BD
# ==============================================================================


def obtener_datos_tasa_cambio(codigo_divisa: str) -> Tuple[Decimal, Decimal, Decimal]:
    """Obtiene los datos de la tasa de cambio desde la BD.

    Args:
        codigo_divisa: Código de la divisa (USD, EUR, BRL, etc.)

    Returns:
        Tupla (precio_base, comision_compra, comision_venta)

    Raises:
        ValueError: Si no se encuentra una tasa de cambio activa para la divisa

    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        from apps.operaciones.models import TasaCambio

        tasa = TasaCambio.objects.filter(
            divisa_origen__codigo="PYG", divisa_destino__codigo=codigo_divisa, activo=True
        ).first()

        if tasa:
            return tasa.precio_base, tasa.comision_compra, tasa.comision_venta

        # No hay tasa activa
        logger.error(f"No se encontró tasa de cambio activa para la divisa {codigo_divisa}")
        raise ValueError(f"No existe tasa de cambio activa para la divisa {codigo_divisa}")

    except Exception as e:
        logger.error(f"Error al obtener tasa de cambio para {codigo_divisa}: {e!s}")
        raise


def obtener_descuento_cliente(cliente) -> Decimal:
    """Obtiene el descuento sobre comisión del segmento del cliente.

    Args:
        cliente: Instancia del modelo Cliente (puede ser None)

    Returns:
        Porcentaje de descuento (0-100)

    """
    if cliente and hasattr(cliente, "tipo_cliente") and cliente.tipo_cliente:
        return cliente.tipo_cliente.descuento_sobre_comision
    return Decimal("0.0")


def obtener_comision_entidad(medio: str, cliente, tipo_operacion: str) -> Optional[Decimal]:
    """Obtiene la comisión de una entidad financiera si existe.

    Args:
        medio: String identificador del medio (ej: "tarjeta_123")
        cliente: Instancia del modelo Cliente
        tipo_operacion: "compra" o "venta"

    Returns:
        Comisión de la entidad o None si no aplica

    """
    if not cliente:
        return None

    try:
        # Importaciones locales para evitar circular imports
        from apps.transacciones.models import BilleteraElectronica, CuentaBancaria, TarjetaCredito

        if medio.startswith("tarjeta_"):
            tarjeta_id = int(medio.split("_")[1])
            tarjeta = TarjetaCredito.objects.get(id=tarjeta_id, cliente=cliente)
            if tarjeta.entidad:
                return tarjeta.entidad.comision_compra if tipo_operacion == "compra" else tarjeta.entidad.comision_venta

        elif medio.startswith("cuenta_"):
            cuenta_id = int(medio.split("_")[1])
            cuenta = CuentaBancaria.objects.get(id=cuenta_id, cliente=cliente)
            if cuenta.entidad:
                return cuenta.entidad.comision_compra if tipo_operacion == "compra" else cuenta.entidad.comision_venta

        elif medio.startswith("billetera_"):
            billetera_id = int(medio.split("_")[1])
            billetera = BilleteraElectronica.objects.get(id=billetera_id, cliente=cliente)
            if billetera.entidad:
                return (
                    billetera.entidad.comision_compra
                    if tipo_operacion == "compra"
                    else billetera.entidad.comision_venta
                )

    except Exception:
        # Captura cualquier error (ValueError, DoesNotExist, ImportError, etc.)
        pass

    return None


def obtener_comision_medio_generico(medio: str, es_pago: bool = True) -> Decimal:
    """Obtiene la comisión de un medio genérico usando el módulo utils.

    Args:
        medio: String identificador del medio
        es_pago: True si es medio de pago, False si es de cobro

    Returns:
        Porcentaje de comisión

    """
    try:
        from utils.commission_calculator import get_collection_commission, get_payment_commission

        # Monto de referencia para el cálculo
        monto_referencia = Decimal("100")

        # Determinar tipo de medio
        if medio.startswith("tarjeta") or "tarjeta" in medio:
            tipo_medio = "tarjeta_credito"
        elif medio.startswith("cuenta") or "cuenta" in medio:
            tipo_medio = "cuenta_bancaria"
        elif medio.startswith("billetera") or "billetera" in medio:
            tipo_medio = "billetera_digital"
        elif medio.startswith("stripe") or medio == "stripe_new":
            return Decimal(str(settings.STRIPE_COMMISSION_RATE))
        else:
            # Efectivo u otro
            return Decimal("0.0")

        # Obtener comisión del módulo utils
        if es_pago:
            return get_payment_commission(tipo_medio, monto_referencia)
        else:
            return get_collection_commission(tipo_medio, monto_referencia)

    except Exception:
        return Decimal("0.0")


def obtener_comision_medio_completa(medio: str, cliente, tipo_operacion: str, es_pago: bool = True) -> Decimal:
    """Obtiene la comisión completa de un medio (entidad o genérico).

    Args:
        medio: String identificador del medio
        cliente: Instancia del modelo Cliente
        tipo_operacion: "compra" o "venta"
        es_pago: True si es medio de pago, False si es de cobro

    Returns:
        Porcentaje de comisión

    """
    # Primero intentar obtener de entidad financiera
    comision_entidad = obtener_comision_entidad(medio, cliente, tipo_operacion)
    if comision_entidad is not None:
        return comision_entidad

    # Si no hay entidad, usar comisión genérica
    return obtener_comision_medio_generico(medio, es_pago)


# ==============================================================================
# FUNCIÓN DE CÁLCULO COMPLETO DE SIMULACIÓN
# ==============================================================================


def calcular_simulacion_completa(
    monto: Decimal, codigo_divisa: str, tipo_operacion: str, medio_pago: str, medio_cobro: str, cliente=None
) -> Dict:
    """Calcula una simulación completa de transacción.

    Args:
        monto: Monto de divisa extranjera
        codigo_divisa: Código de la divisa (USD, EUR, etc.)
        tipo_operacion: "compra" o "venta"
        medio_pago: Identificador del medio de pago
        medio_cobro: Identificador del medio de cobro
        cliente: Instancia del modelo Cliente (opcional)

    Returns:
        Diccionario con todos los datos de la simulación

    """
    # Validaciones
    if tipo_operacion == "compra" and medio_pago == "efectivo":
        raise ValueError("No se permite comprar divisas usando efectivo como medio de pago")

    if tipo_operacion == "venta" and medio_cobro == "efectivo":
        raise ValueError("No se permite vender divisas cobrando en efectivo como medio de cobro")

    # Obtener datos de BD
    precio_base, comision_compra, comision_venta = obtener_datos_tasa_cambio(codigo_divisa)
    descuento = obtener_descuento_cliente(cliente)

    # Determinar si es Stripe
    es_stripe = medio_pago == "stripe_new" or medio_pago.startswith("stripe_")

    # Calcular según tipo de operación
    if tipo_operacion == "compra":
        # Cliente COMPRA divisa (casa VENDE)
        monto_convertido, tasa_efectiva, comision_efectiva = convertir_compra_a_pyg(
            monto, precio_base, comision_venta, descuento
        )

        # Calcular tasa base (sin descuento) para mostrar al usuario
        tasa_base_sin_descuento = calcular_tasa_venta_base(precio_base, comision_venta)

        # Obtener comisión del medio de pago
        porc_comision_pago = obtener_comision_medio_completa(medio_pago, cliente, tipo_operacion, es_pago=True)
        comision_medio_pago = calcular_comision_medio_pago(monto_convertido, porc_comision_pago, es_stripe)

        # Total
        total = calcular_total_compra(monto_convertido, comision_medio_pago)

        # Para compra no hay comisión de cobro
        comision_medio_cobro = 0
        porc_comision_cobro = Decimal("0.0")
        comision_base_usada = comision_venta

    else:  # venta
        # Cliente VENDE divisa (casa COMPRA)
        monto_convertido, tasa_efectiva, comision_efectiva = convertir_venta_a_pyg(
            monto, precio_base, comision_compra, descuento
        )

        # Calcular tasa base (sin descuento) para mostrar al usuario
        tasa_base_sin_descuento = calcular_tasa_compra_base(precio_base, comision_compra)

        # Obtener comisión del medio de cobro
        porc_comision_cobro = obtener_comision_medio_completa(medio_cobro, cliente, tipo_operacion, es_pago=False)
        comision_medio_cobro = calcular_comision_medio_cobro(monto_convertido, porc_comision_cobro)

        # Total
        total = calcular_total_venta(monto_convertido, comision_medio_cobro)

        # Para venta no hay comisión de pago ni Stripe
        comision_medio_pago = 0
        porc_comision_pago = Decimal("0.0")
        es_stripe = False
        comision_base_usada = comision_compra

    # Obtener comisión fija Stripe si aplica
    stripe_fixed_fee = obtener_comision_fija_stripe_pyg() if es_stripe else 0
    stripe_fixed_fee_usd = float(settings.STRIPE_FIXED_FEE_USD) if es_stripe else 0.0

    # Obtener nombre del tipo de cliente
    tipo_cliente_nombre = ""
    if cliente and hasattr(cliente, "tipo_cliente") and cliente.tipo_cliente:
        tipo_cliente_nombre = cliente.tipo_cliente.nombre

    # Construir respuesta
    return {
        "monto_original": float(monto),
        "moneda_origen": codigo_divisa,  # Siempre la divisa extranjera (lo que el cliente desea/tiene)
        "moneda_destino": "PYG",  # Siempre PYG (lo que se paga/recibe)
        "tasa_base": float(tasa_base_sin_descuento),  # Tasa pública sin descuento
        "tasa_cambio": float(tasa_efectiva),  # Tasa con descuento aplicado
        "monto_convertido": monto_convertido,
        "comision_base": float(comision_base_usada),
        "descuento": float(descuento),
        "comision_final": float(comision_efectiva),
        "comision_medio_pago_porcentaje": float(porc_comision_pago),
        "comision_medio_pago_monto": comision_medio_pago,
        "comision_medio_cobro_porcentaje": float(porc_comision_cobro),
        "comision_medio_cobro_monto": comision_medio_cobro,
        "total_antes_comision_medio": monto_convertido,
        "total": total,
        "tipo_operacion": tipo_operacion,
        "metodo_pago": medio_pago,
        "metodo_cobro": medio_cobro,
        "stripe_fixed_fee": stripe_fixed_fee,
        "stripe_fixed_fee_usd": stripe_fixed_fee_usd,
        "tipo_cliente": tipo_cliente_nombre,
    }
