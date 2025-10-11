"""Servicios para la aplicación de stock."""

import json
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import MovimientoStock, MovimientoStockDetalle, StockDivisaTauser


def cargar_denominaciones_divisa():
    """Carga las denominaciones disponibles desde currency_denominations.json."""
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
    """Obtiene todo el stock de un tauser agrupado por divisa."""
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
    """Obtiene las divisas que tienen stock disponible para un tauser."""
    from apps.operaciones.models import Divisa

    divisas_con_stock = StockDivisaTauser.objects.filter(
        tauser_id=tauser_id,
        stock__gt=0
    ).values_list('divisa_id', flat=True).distinct()

    return Divisa.objects.filter(codigo__in=divisas_con_stock).order_by('codigo')


def obtener_denominaciones_disponibles(tauser_id, divisa_id):
    """Obtiene las denominaciones disponibles en stock para un tauser y divisa."""
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


@transaction.atomic
def depositar_divisas(tauser_id, divisa_id, denominaciones_cantidades):
    """Deposita divisas en el stock de un tauser.
    
    Args:
        tauser_id: ID del tauser
        divisa_id: ID de la divisa
        denominaciones_cantidades: lista de {'denominacion': int, 'cantidad': int}
    
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
        estado='confirmado',
        motivo=f'Depósito manual de {divisa.codigo}',
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
def extraer_divisas(tauser_id, divisa_id, denominaciones_cantidades):
    """Extrae divisas del stock de un tauser.
    
    Args:
        tauser_id: ID del tauser
        divisa_id: ID de la divisa
        denominaciones_cantidades: lista de {'denominacion': int, 'cantidad': int}
    
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
        estado='confirmado',
        motivo=f'Extracción manual de {divisa.codigo}',
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
        stock_obj.save()

        # Crear detalle del movimiento
        MovimientoStockDetalle.objects.create(
            movimiento_stock=movimiento,
            denominacion=denominacion,
            cantidad=cantidad
        )

    return movimiento
