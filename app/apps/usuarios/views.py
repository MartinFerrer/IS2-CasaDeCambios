"""Módulo de vistas para la aplicación de usuarios.

Este módulo contiene las vistas relacionadas con la gestión de usuarios,
configuración de perfiles y gestión de información personal.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.seguridad.models import PerfilMFA

from .forms import CustomUserCreationForm


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
    - Notificaciones (futuro)

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


def registro(request):
    """Vista de registro de usuario"""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario registrado con éxito.")
            return redirect("usuarios:configuracion_usuario")
    else:
        form = CustomUserCreationForm()
    return render(request, "usuarios/registro.html", {"form": form})
