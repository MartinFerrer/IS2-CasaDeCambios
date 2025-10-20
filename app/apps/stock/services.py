"""Servicios para la aplicación de stock.

Este módulo expone funciones de alto nivel que implementan la lógica de
negocio relacionada con la gestión del stock por tauser. 
"""

import json
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import MovimientoStock, MovimientoStockDetalle, StockDivisaTauser


def cargar_denominaciones_divisa():
    """Carga denominaciones desde `staticfiles/currency_denominations.json`.

    Returns:
        dict: {ISO: [denominaciones_int]} o {} en caso de error.

    """
    json_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'currency_denominations.json')

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Convertir a dict por ISO code para fácil lookup
        denominaciones = {}
        for item in data:
            iso = item.get('iso', '')
            if iso and 'denominations' in item:
                # Convertir strings a integers y ordenar descendente
                denoms = sorted([int(d) for d in item['denominations']], reverse=True)
                denominaciones[iso] = denoms

        return denominaciones
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Error cargando denominaciones: {e}")
        return {}


def obtener_stock_tauser(tauser_id):
    """Obtiene el stock de un tauser agrupado por divisa.

    Args:
        tauser_id (int): ID del tauser.

    Returns:
        list[dict]: Lista con campos como 'divisa_codigo', 'denominacion',
                    'stock', 'stock_libre' y 'valor_total'.

    """
    stocks = StockDivisaTauser.objects.filter(
        tauser_id=tauser_id
    ).select_related('divisa').order_by('divisa__codigo', '-denominacion')

    resultado = []
    for stock in stocks:
        resultado.append({
            'id': stock.pk,
            'divisa_codigo': stock.divisa.codigo,
            'divisa_nombre': stock.divisa.nombre,
            'divisa_simbolo': stock.divisa.simbolo,
            'denominacion': stock.denominacion,
            'stock': stock.stock,
            'stock_reservado': stock.stock_reservado,
            'stock_libre': stock.stock_libre,
            'valor_total': stock.stock * stock.denominacion,
        })

    return resultado


def obtener_divisas_con_stock(tauser_id):
    """Obtiene las divisas que tienen stock disponible para un tauser.

    Args:
        tauser_id (int): ID del tauser

    Returns:
        QuerySet[Divisa]: Queryset de objetos `Divisa` ordenados por código.

    """
    from apps.operaciones.models import Divisa

    divisas_con_stock = StockDivisaTauser.objects.filter(
        tauser_id=tauser_id,
        stock__gt=0
    ).values_list('divisa_id', flat=True).distinct()

    return Divisa.objects.filter(codigo__in=divisas_con_stock).order_by('codigo')


def obtener_denominaciones_disponibles(tauser_id, divisa_id):
    """Obtiene las denominaciones disponibles en stock para un tauser y divisa.

    Args:
        tauser_id (int): ID del tauser
        divisa_id (str): Código de la divisa (ej. 'USD')

    Returns:
        list: Lista de dicts con claves: denominacion, stock_disponible, stock_total, stock_reservado

    """
    stocks = StockDivisaTauser.objects.filter(
        tauser_id=tauser_id,
        divisa__codigo=divisa_id,
        stock__gt=0
    ).order_by('-denominacion')

    return [{
        'denominacion': stock.denominacion,
        'stock_disponible': stock.stock_libre,
        'stock_total': stock.stock,
        'stock_reservado': stock.stock_reservado,
    } for stock in stocks]

def monto_valido(divisa_id, monto):
    """Verifica si el monto solicitado puede ser cubierto con las denominaciones definidas.

    Args:
        divisa_id (str): Código de la divisa (ej. 'USD')
        monto (int): Monto solicitado

    Returns:
        bool: True si el monto puede ser cubierto, False en caso contrario.

    """
    # Asegurarse de que el monto es entero no-negativo
    try:
        monto_int = int(monto)
    except (TypeError, ValueError):
        return False

    if monto_int < 0:
        return False

    # Cargar denominaciones globales desde el JSON
    all_denoms = cargar_denominaciones_divisa()
    denoms = all_denoms.get(divisa_id)
    if not denoms:
        # Si no hay definidas denominaciones para la divisa, no es válido
        return False
    # DP: clásico problema de cambio de monedas (unbounded coin change)
    # Usamos una tabla booleana hasta monto_int para saber si se puede formar
    # Para eficiencia, si monto_int es grande, cortamos a un límite razonable (ej. 1000000)
    max_monto_dp = 100_000_000
    if monto_int > max_monto_dp:
        # Evitar consumo excesivo de memoria/CPU; el caller puede usar otra vía
        return False

    reachable = [False] * (monto_int + 1)
    reachable[0] = True

    # Ordenar denominaciones ascendentes para llenar la tabla
    denoms_sorted = sorted({int(d) for d in denoms if int(d) > 0})
    if not denoms_sorted:
        return False

    for coin in denoms_sorted:
        for s in range(coin, monto_int + 1):
            if reachable[s - coin]:
                reachable[s] = True

    return reachable[monto_int]

@transaction.atomic
def depositar_divisas(tauser_id, divisa_id, denominaciones_cantidades, transaccion=None,panel_admin=True):
    """Deposita divisas en el stock de un tauser.
    
    Args:
        tauser_id: ID del tauser
        divisa_id: ID de la divisa
        denominaciones_cantidades: lista de {'denominacion': int, 'cantidad': int}
        transaccion: La transacción asociada (opcional)
        panel_admin: Indica si la acción es desde el panel de administración o desde transacciones

    Returns:
        MovimientoStock creado

    """
    from apps.operaciones.models import Divisa
    from apps.tauser.models import Tauser

    tauser = Tauser.objects.get(id=tauser_id)
    divisa = Divisa.objects.get(codigo=divisa_id)

    # Crear movimiento principal
    movimiento = MovimientoStock.objects.create(
        tauser=tauser,
        divisa=divisa,
        tipo_movimiento='entrada',
        transaccion=transaccion,
        estado='confirmado',
        motivo=f'Depósito manual de {divisa.codigo}' if panel_admin else f'Transaccion - Depósito de {divisa.codigo}',
    )

    # Procesar cada denominación
    for item in denominaciones_cantidades:
        denominacion = int(item['denominacion'])
        cantidad = int(item['cantidad'])

        if cantidad <= 0:
            raise ValidationError(f"La cantidad debe ser mayor a 0 para denominación {denominacion}")

        # Obtener o crear registro de stock
        stock_obj, created = StockDivisaTauser.objects.select_for_update().get_or_create(
            tauser=tauser,
            divisa=divisa,
            denominacion=denominacion,
            defaults={'stock': 0, 'stock_reservado': 0}
        )

        # Actualizar stock
        stock_obj.stock += cantidad
        stock_obj.save()

        # Crear detalle del movimiento
        MovimientoStockDetalle.objects.create(
            movimiento_stock=movimiento,
            denominacion=denominacion,
            cantidad=cantidad
        )

    return movimiento


@transaction.atomic
def extraer_divisas(tauser_id, divisa_id, denominaciones_cantidades, transaccion=None, panel_admin=True):
    """Extrae divisas del stock de un tauser.
    
    Args:
        tauser_id: ID del tauser
        divisa_id: ID de la divisa
        denominaciones_cantidades: lista de {'denominacion': int, 'cantidad': int}
        transaccion: La transacción asociada (opcional)
        panel_admin: Indica si la acción es desde el panel de administración o desde transacciones
    
    Returns:
        MovimientoStock creado

    """
    from apps.operaciones.models import Divisa
    from apps.tauser.models import Tauser

    tauser = Tauser.objects.get(id=tauser_id)
    divisa = Divisa.objects.get(codigo=divisa_id)

    # Validar que hay suficiente stock antes de hacer cambios
    for item in denominaciones_cantidades:
        denominacion = int(item['denominacion'])
        cantidad = int(item['cantidad'])

        if cantidad <= 0:
            raise ValidationError(f"La cantidad debe ser mayor a 0 para denominación {denominacion}")

        try:
            stock_obj = StockDivisaTauser.objects.get(
                tauser=tauser,
                divisa=divisa,
                denominacion=denominacion
            )
            if stock_obj.stock_libre < cantidad:
                raise ValidationError(
                    f"Stock insuficiente para denominación {denominacion}. "
                    f"Disponible: {stock_obj.stock_libre}, Solicitado: {cantidad}"
                )
        except StockDivisaTauser.DoesNotExist:
            raise ValidationError(f"No existe stock para denominación {denominacion}")

    # Crear movimiento principal
    movimiento = MovimientoStock.objects.create(
        tauser=tauser,
        divisa=divisa,
        tipo_movimiento='salida',
        transaccion=transaccion,
        estado='confirmado' if panel_admin else 'pendiente',
        motivo=f'Extracción manual de {divisa.codigo}' if panel_admin else f'Transaccion - Extracción de {divisa.codigo}',
    )

    # Procesar cada denominación
    for item in denominaciones_cantidades:
        denominacion = int(item['denominacion'])
        cantidad = int(item['cantidad'])

        # Obtener registro de stock con lock
        stock_obj = StockDivisaTauser.objects.select_for_update().get(
            tauser=tauser,
            divisa=divisa,
            denominacion=denominacion
        )

        # Actualizar stock
        stock_obj.stock -= cantidad
        # Si es una transacción, aumentar stock reservado
        if transaccion is not None:
            stock_obj.stock_reservado += cantidad
        stock_obj.save()

        # Crear detalle del movimiento
        MovimientoStockDetalle.objects.create(
            movimiento_stock=movimiento,
            denominacion=denominacion,
            cantidad=cantidad
        )

    return movimiento

@transaction.atomic
def cancelar_movimiento(movimiento_id):
    """Cancela un movimiento de stock, revirtiendo los cambios en el stock.

    Args:
        movimiento_id (int): ID del movimiento a cancelar.

    Raises:
        ValidationError: Si el movimiento no puede ser cancelado.

    """
    movimiento = MovimientoStock.objects.select_for_update().get(id=movimiento_id)

    if movimiento.estado != 'pendiente':
        raise ValidationError("Solo se pueden cancelar movimientos pendientes.")

    for detalle in movimiento.detalles.all():
        stock_obj = StockDivisaTauser.objects.select_for_update().get(
            tauser=movimiento.tauser,
            divisa=movimiento.divisa,
            denominacion=detalle.denominacion
        )

        if movimiento.tipo_movimiento == 'entrada':
            # Revertir depósito
            if stock_obj.stock_reservado < detalle.cantidad:
                raise ValidationError(f"No hay suficiente stock reservado para revertir la denominación {detalle.denominacion}.")
            stock_obj.stock_reservado -= detalle.cantidad
        elif movimiento.tipo_movimiento == 'salida':
            # Revertir extracción
            stock_obj.stock += detalle.cantidad
            if movimiento.transaccion is not None:
                # Si fue parte de una transacción, liberar stock reservado
                if stock_obj.stock_reservado < detalle.cantidad:
                    raise ValidationError(f"No hay suficiente stock reservado para revertir la denominación {detalle.denominacion}.")
                stock_obj.stock_reservado -= detalle.cantidad
        stock_obj.save()

    movimiento.estado = 'cancelado'
    movimiento.save()


@transaction.atomic
def confirmar_movimiento(movimiento_id):
    """Confirma un movimiento de stock pendiente.

    Args:
        movimiento_id (int): ID del movimiento a confirmar.

    Raises:
        ValidationError: Si el movimiento no puede ser confirmado.

    """
    movimiento = MovimientoStock.objects.select_for_update().get(id=movimiento_id)

    if movimiento.estado != 'pendiente':
        raise ValidationError("Solo se pueden confirmar movimientos pendientes.")

    for detalle in movimiento.detalles.all():
        stock_obj = StockDivisaTauser.objects.select_for_update().get(
            tauser=movimiento.tauser,
            divisa=movimiento.divisa,
            denominacion=detalle.denominacion
        )

        if movimiento.tipo_movimiento == 'entrada':
            # Reducir stock reservado al confirmar depósito
            if stock_obj.stock_reservado < detalle.cantidad:
                raise ValidationError(f"No hay suficiente stock reservado para confirmar la denominación {detalle.denominacion}.")
            stock_obj.stock_reservado -= detalle.cantidad
            stock_obj.stock += detalle.cantidad
        elif movimiento.tipo_movimiento == 'salida':
            # Reducir stock reservado al confirmar extracción
            if stock_obj.stock_reservado < detalle.cantidad:
                raise ValidationError(f"No hay suficiente stock reservado para confirmar la denominación {detalle.denominacion}.")
            stock_obj.stock_reservado -= detalle.cantidad
        stock_obj.save()

    movimiento.estado = 'confirmado'
    movimiento.save()
