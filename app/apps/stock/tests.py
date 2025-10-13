import pytest
from django.core.exceptions import ValidationError
from model_bakery import baker

from apps.stock import services
from apps.stock.models import StockDivisaTauser


@pytest.mark.django_db
def test_operaciones_basicas_de_stock():
    tauser = baker.make('tauser.Tauser')
    divisa = baker.make('operaciones.Divisa', codigo='USD')

    stock = StockDivisaTauser.objects.create(
        tauser=tauser,
        divisa=divisa,
        denominacion=100,
        stock=10,
        stock_reservado=2,
    )

    # stock_libre
    assert stock.stock_libre == 8

    # reservar_stock success
    assert stock.reservar_stock(3) is True
    assert stock.stock_reservado == 5

    # reservar_stock fail
    assert stock.reservar_stock(100) is False

    # liberar_stock_reservado
    stock.liberar_stock_reservado(2)
    assert stock.stock_reservado == 3

    # confirmar_movimiento
    stock.confirmar_movimiento(2)
    assert stock.stock == 8
    assert stock.stock_reservado == 1


@pytest.mark.django_db
def test_obtener_totales_y_seleccionar_denominaciones():
    tauser = baker.make('tauser.Tauser')
    divisa = baker.make('operaciones.Divisa', codigo='USD')

    # crear varias denominaciones
    StockDivisaTauser.objects.create(tauser=tauser, divisa=divisa, denominacion=100, stock=2, stock_reservado=0)
    StockDivisaTauser.objects.create(tauser=tauser, divisa=divisa, denominacion=50, stock=4, stock_reservado=1)

    totals = StockDivisaTauser.obtener_stock_total_divisa(tauser, divisa)
    # total disponible = 2*100 + 4*50 = 200 + 200 = 400
    assert totals['total_disponible'] == 400
    # total reservado = 1*50 = 50
    assert totals['total_reservado'] == 50

    # seleccionar denominaciones para monto 250 -> 100x2 + 50x1
    seleccion = StockDivisaTauser.seleccionar_denominaciones_optimas(tauser, divisa, 250)
    assert seleccion is not None
    # debe sumar 250
    assert sum(item['valor_total'] for item in seleccion) == 250


@pytest.mark.django_db
def test_depositar_y_extraer_divisas_services():
    tauser = baker.make('tauser.Tauser')
    divisa = baker.make('operaciones.Divisa', codigo='USD')

    # depositar: agregar denominaciones
    movimiento = services.depositar_divisas(tauser.id, divisa.codigo, [
        {'denominacion': 100, 'cantidad': 5},
        {'denominacion': 50, 'cantidad': 2},
    ])

    assert movimiento.tipo_movimiento == 'entrada'
    # comprobar que stock se creó y cantidades
    s100 = StockDivisaTauser.objects.get(tauser=tauser, divisa=divisa, denominacion=100)
    assert s100.stock == 5

    s50 = StockDivisaTauser.objects.get(tauser=tauser, divisa=divisa, denominacion=50)
    assert s50.stock == 2

    # extraer con cantidad válida
    movimiento2 = services.extraer_divisas(tauser.id, divisa.codigo, [
        {'denominacion': 100, 'cantidad': 3},
    ])
    assert movimiento2.tipo_movimiento == 'salida'
    s100.refresh_from_db()
    assert s100.stock == 2

    # intentar extraer más del disponible -> ValidationError
    with pytest.raises(ValidationError):
        services.extraer_divisas(tauser.id, divisa.codigo, [
            {'denominacion': 50, 'cantidad': 10},
        ])

    # cantidad negativa en deposito -> ValidationError
    with pytest.raises(ValidationError):
        services.depositar_divisas(tauser.id, divisa.codigo, [
            {'denominacion': 20, 'cantidad': -1},
        ])


@pytest.mark.django_db
def test_valor_total_detalle_y_seleccion_insuficiente():
    # valor_total de MovimientoStockDetalle está implícito a través del servicio
    tauser = baker.make('tauser.Tauser')
    divisa = baker.make('operaciones.Divisa', codigo='USD')

    movimiento = services.depositar_divisas(tauser.id, divisa.codigo, [
        {'denominacion': 100, 'cantidad': 1},
    ])

    # el detalle debe tener valor_total = 100
    detalle = movimiento.detalles.first()
    assert detalle.valor_total == 100

    # seleccionar_denominaciones_optimas devuelve None si no alcanza
    seleccion = StockDivisaTauser.seleccionar_denominaciones_optimas(tauser, divisa, 500)
    assert seleccion is None


@pytest.mark.django_db
def test_obtener_denominaciones_disponibles_y_validaciones_modelo():
    tauser = baker.make('tauser.Tauser')
    divisa = baker.make('operaciones.Divisa', codigo='USD')

    # crear stock disponible
    StockDivisaTauser.objects.create(tauser=tauser, divisa=divisa, denominacion=20, stock=3, stock_reservado=1)
    disponibles = services.obtener_denominaciones_disponibles(tauser.id, divisa.codigo)
    assert isinstance(disponibles, list)
    assert len(disponibles) == 1

    # validaciones del modelo: denominacion <= 0
    s = StockDivisaTauser(tauser=tauser, divisa=divisa, denominacion=0, stock=1, stock_reservado=0)
    with pytest.raises(Exception):
        s.full_clean()

    # validacion stock negativo
    s2 = StockDivisaTauser(tauser=tauser, divisa=divisa, denominacion=10, stock=-1, stock_reservado=0)
    with pytest.raises(Exception):
        s2.full_clean()

