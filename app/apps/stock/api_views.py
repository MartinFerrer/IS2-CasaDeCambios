"""API views para la gestión de stock."""

import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services import (
    cargar_denominaciones_divisa,
    depositar_divisas,
    extraer_divisas,
    obtener_denominaciones_disponibles,
    obtener_divisas_con_stock,
    obtener_stock_tauser,
)


@login_required
@require_http_methods(["GET"])
def obtener_stock_api(request, tauser_id):
    """API para obtener el stock de un tauser."""
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
    """API para obtener todas las divisas con sus denominaciones disponibles."""
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
    """API para obtener divisas que tienen stock para un tauser."""
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
    """API para obtener denominaciones disponibles para un tauser y divisa."""
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
    """API para depositar divisas en el stock de un tauser."""
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
                'movimiento_id': movimiento.id,
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
    """API para extraer divisas del stock de un tauser."""
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
                'movimiento_id': movimiento.id,
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
