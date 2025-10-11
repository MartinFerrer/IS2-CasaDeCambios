"""Módulo de vistas para la aplicación de usuarios.

Este módulo contiene las vistas relacionadas con la gestión de usuarios,
configuración de perfiles y gestión de información personal.
"""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.seguridad.models import PerfilMFA
from usuarios.models import Cliente

from .models import PreferenciaNotificacion


def ejemplo(request: HttpRequest) -> HttpResponse:
    """_summary_.

    Args:
        request (HttpRequest): _description_

    Returns:
        HttpResponse: _description_

    """
    return render(request, "base.html")


@login_required
def configuracion_usuario(request):
    """Vista para la configuración unificada del usuario.

    Muestra una página con todas las opciones de configuración disponibles:
    - Perfil de usuario (información personal)
    - Configuración MFA (autenticación multifactor)
    - Medios de pago (si el usuario tiene clientes)
    - Listado de clientes asociados
    - Notificaciones (actualizaciones de tasas, etc.)

    Args:
        request: Objeto HttpRequest de Django.

    Returns:
        HttpResponse: Renderiza la plantilla 'configuracion_usuario.html'.

    """
    # Obtener información del usuario
    usuario = request.user

    # Verificar si el usuario tiene clientes asociados
    user_has_clients = usuario.clientes.exists()

    # Obtener todos los clientes del usuario
    clientes = usuario.clientes.all().select_related("tipo_cliente")

    # Obtener perfil MFA si existe
    perfil_mfa = None
    try:
        perfil_mfa = PerfilMFA.objects.get(usuario=usuario)
    except PerfilMFA.DoesNotExist:
        pass

    # Obtener grupos del usuario
    user_groups = [group.name for group in usuario.groups.all()]

    # Cliente seleccionado actualmente (del contexto de la sesión)
    cliente_seleccionado = getattr(request, "cliente", None)

    context = {
        "usuario": usuario,
        "user_has_clients": user_has_clients,
        "clientes": clientes,
        "cliente_seleccionado": cliente_seleccionado,
        "perfil_mfa": perfil_mfa,
        "user_groups": user_groups,
    }

    return render(request, "usuarios/configuracion_usuario.html", context)


@require_POST
@login_required
def actualizar_preferencia_notificacion(request):
    """Vista para la configuracion de frecuencia de notificaciones en base a cambios en la tasa de cambios

    Args:
        request (_type_): _description_

    Returns:
        _type_: _description_

    """
    cliente_id = request.POST.get("cliente_id")
    if not cliente_id:
        return JsonResponse({"error": "cliente_id requerido"}, status=400)

    cliente = get_object_or_404(Cliente, pk=cliente_id)
    habilitado = request.POST.get("habilitado") in ("true", "1", "on")
    frecuencia = request.POST.get("frecuencia", "diario")
    if frecuencia not in dict(PreferenciaNotificacion.FRECUENCIA_CHOICES):
        return JsonResponse({"error": "frecuencia inválida"}, status=400)

    pref, _ = PreferenciaNotificacion.objects.get_or_create(cliente=cliente)
    pref.habilitado = habilitado
    pref.frecuencia = frecuencia
    pref.save()
    return JsonResponse({"success": True})
