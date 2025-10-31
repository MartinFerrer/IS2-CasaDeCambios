"""Módulo de utilidades para transacciones.

Este paquete contiene utilidades comunes para el manejo de transacciones,
incluyendo cálculo de comisiones, validaciones y helpers.
"""

from .calculos_tasas_comisiones import (
    # Funciones de comisiones efectivas
    calcular_comision_efectiva,
    calcular_comision_medio_cobro,
    calcular_comision_medio_pago,
    # Funciones de comisiones de medios
    calcular_comision_porcentual,
    # Función principal
    calcular_simulacion_completa,
    # Funciones de tasas base
    calcular_tasa_compra_base,
    calcular_tasa_compra_efectiva,
    calcular_tasa_venta_base,
    calcular_tasa_venta_efectiva,
    # Funciones de totales
    calcular_total_compra,
    calcular_total_venta,
    # Funciones de conversión
    convertir_a_pyg,
    convertir_compra_a_pyg,
    convertir_venta_a_pyg,
    obtener_comision_entidad,
    obtener_comision_fija_stripe_pyg,
    obtener_comision_medio_completa,
    obtener_comision_medio_generico,
    # Funciones auxiliares BD
    obtener_datos_tasa_cambio,
    obtener_descuento_cliente,
)

__all__ = [
    # Funciones de tasas base
    "calcular_tasa_compra_base",
    "calcular_tasa_venta_base",
    # Funciones de comisiones efectivas
    "calcular_comision_efectiva",
    "calcular_tasa_compra_efectiva",
    "calcular_tasa_venta_efectiva",
    # Funciones de conversión
    "convertir_a_pyg",
    "convertir_compra_a_pyg",
    "convertir_venta_a_pyg",
    # Funciones de comisiones de medios
    "calcular_comision_porcentual",
    "obtener_comision_fija_stripe_pyg",
    "calcular_comision_medio_pago",
    "calcular_comision_medio_cobro",
    # Funciones de totales
    "calcular_total_compra",
    "calcular_total_venta",
    # Funciones auxiliares BD
    "obtener_datos_tasa_cambio",
    "obtener_descuento_cliente",
    "obtener_comision_entidad",
    "obtener_comision_medio_generico",
    "obtener_comision_medio_completa",
    # Función principal
    "calcular_simulacion_completa",
]
