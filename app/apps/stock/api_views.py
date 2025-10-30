"""API views para la gestión de stock."""

import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services import (
    cancelar_movimiento,
    cargar_denominaciones_divisa,
    cargar_denominaciones_divisa_especifica,
    depositar_divisas,
    extraer_divisas,
    obtener_denominaciones_disponibles,
    obtener_divisas_con_stock,
    obtener_stock_tauser,
)


@login_required
@require_http_methods(["GET"])
def obtener_stock_api(request, tauser_id):
    """Obtiene el stock de un tauser.

    Args:
        request (HttpRequest): petición HTTP
        tauser_id (int): ID del tauser

    Returns:
        JsonResponse: {'success': True, 'data': [...] } o {'success': False, 'error': ...}

    """
    try:
        stock_data = obtener_stock_tauser(tauser_id)
        return JsonResponse({
            'success': True,
            'data': stock_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def obtener_divisas_api(request):
    """Devuelve las divisas activas y sus denominaciones (desde JSON).

    Args:
        request (HttpRequest): petición HTTP.

    Returns:
        JsonResponse: {'success': True, 'data': [...] }.

    """
    try:
        from apps.operaciones.models import Divisa

        # Cargar denominaciones desde JSON
        denominaciones_json = cargar_denominaciones_divisa()

        # Obtener divisas activas
        divisas = Divisa.objects.filter(estado='activa').order_by('codigo')

        resultado = []
        for divisa in divisas:
            denominaciones = denominaciones_json.get(divisa.codigo, [])
            resultado.append({
                'id': divisa.codigo,
                'codigo': divisa.codigo,
                'nombre': divisa.nombre,
                'simbolo': divisa.simbolo,
                'denominaciones': denominaciones
            })

        return JsonResponse({
            'success': True,
            'data': resultado
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def obtener_divisas_con_stock_api(request, tauser_id):
    """Devuelve las divisas que tienen stock>0 para un tauser.

    Args:
        request (HttpRequest): petición HTTP.
        tauser_id (int): ID del tauser.

    Returns:
        JsonResponse: lista de divisas en 'data'.

    """
    try:
        divisas = obtener_divisas_con_stock(tauser_id)

        resultado = []
        for divisa in divisas:
            resultado.append({
                'id': divisa.codigo,
                'codigo': divisa.codigo,
                'nombre': divisa.nombre,
                'simbolo': divisa.simbolo
            })

        return JsonResponse({
            'success': True,
            'data': resultado
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def obtener_denominaciones_api(request, tauser_id, divisa_id):
    """Devuelve las denominaciones disponibles para una divisa y tauser.

    Args:
        request (HttpRequest): petición HTTP.
        tauser_id (int): ID del tauser.
        divisa_id (str): Código ISO de la divisa.

    Returns:
        JsonResponse: lista de denominaciones en 'data'.

    """
    try:
        denominaciones = obtener_denominaciones_disponibles(tauser_id, divisa_id)
        return JsonResponse({
            'success': True,
            'data': denominaciones
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def depositar_divisas_api(request):
    """Endpoint POST para depositar denominaciones en un tauser.

    Args:
        request (HttpRequest): petición HTTP.

    Returns:
        JsonResponse con 'movimiento_id' en caso de éxito o error y código HTTP.

    """
    try:
        data = json.loads(request.body)

        # Validar campos requeridos
        required_fields = ['tauser_id', 'divisa_id', 'denominaciones']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'error': f'Campo requerido: {field}'
                }, status=400)

        # Validar denominaciones
        denominaciones = data['denominaciones']
        if not isinstance(denominaciones, list) or not denominaciones:
            return JsonResponse({
                'success': False,
                'error': 'Las denominaciones deben ser una lista no vacía'
            }, status=400)

        for item in denominaciones:
            if not isinstance(item, dict) or 'denominacion' not in item or 'cantidad' not in item:
                return JsonResponse({
                    'success': False,
                    'error': 'Cada denominación debe tener denominacion y cantidad'
                }, status=400)

        # Realizar el depósito
        movimiento = depositar_divisas(
            tauser_id=data['tauser_id'],
            divisa_id=data['divisa_id'],
            denominaciones_cantidades=denominaciones
        )

        return JsonResponse({
            'success': True,
            'data': {
                'movimiento_id': movimiento.pk,
                'mensaje': 'Depósito realizado exitosamente'
            }
        })

    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error interno: {e!s}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def extraer_divisas_api(request):
    """Endpoint POST para extraer denominaciones de un tauser.

    Args:
        request (HttpRequest): petición HTTP.

    Returns:
        JsonResponse con 'movimiento_id' en caso de éxito o error y código HTTP.

    """
    try:
        data = json.loads(request.body)

        # Validar campos requeridos
        required_fields = ['tauser_id', 'divisa_id', 'denominaciones']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'error': f'Campo requerido: {field}'
                }, status=400)

        # Validar denominaciones
        denominaciones = data['denominaciones']
        if not isinstance(denominaciones, list) or not denominaciones:
            return JsonResponse({
                'success': False,
                'error': 'Las denominaciones deben ser una lista no vacía'
            }, status=400)

        for item in denominaciones:
            if not isinstance(item, dict) or 'denominacion' not in item or 'cantidad' not in item:
                return JsonResponse({
                    'success': False,
                    'error': 'Cada denominación debe tener denominacion y cantidad'
                }, status=400)

        # Realizar la extracción
        movimiento = extraer_divisas(
            tauser_id=data['tauser_id'],
            divisa_id=data['divisa_id'],
            denominaciones_cantidades=denominaciones
        )

        return JsonResponse({
            'success': True,
            'data': {
                'movimiento_id': movimiento.pk,
                'mensaje': 'Extracción realizada exitosamente'
            }
        })

    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error interno: {e!s}'
        }, status=500)


@require_http_methods(["GET"])
def api_denominaciones_divisa(request, divisa_codigo):
    """API para obtener denominaciones disponibles de una divisa específica.

    Args:
        request (HttpRequest): Solicitud HTTP.
        divisa_codigo (str): Código de la divisa (ej. 'USD').

    Returns:
        JsonResponse: Lista de denominaciones disponibles.

    """
    try:
        denominaciones = cargar_denominaciones_divisa_especifica(divisa_codigo)
        return JsonResponse(denominaciones, safe=False)
    except Exception as e:
        return JsonResponse({'error': f'Error al cargar denominaciones: {e!s}'}, status=500)

@require_http_methods(["POST"])
def api_cancelar_movimiento_transaccion(request, transaccion_id=None):
    """API para cancelar un movimiento de stock.

    Args:
        request (HttpRequest): Solicitud HTTP.
        transaccion_id (int, optional): ID de la transacción asociada al movimiento a cancelar.

    Returns:
        JsonResponse: Resultado de la operación.

    """
    from .models import MovimientoStock
    try:
        movimiento_stock = None
        if transaccion_id:
            movimiento_stock = MovimientoStock.objects.filter(
                transaccion=transaccion_id,
                estado='pendiente'
            ).first()
        movimiento_id = movimiento_stock.pk if movimiento_stock else None
        cancelar_movimiento(movimiento_id)
        return JsonResponse({'success': True, 'message': 'Movimiento cancelado exitosamente.'})
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error interno: {e!s}'}, status=500)
