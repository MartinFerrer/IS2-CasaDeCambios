"""Módulo de vistas para la aplicación de usuarios."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.operaciones.models import Divisa
from apps.seguridad.models import PerfilMFA


def ejemplo(request: HttpRequest) -> HttpResponse:
    """Vista de ejemplo."""
    return render(request, "base.html")


@login_required
def configuracion_usuario(request):
    """Vista para la configuración del usuario."""
    # Obtener información del usuario
    usuario = request.user

    # Obtener todos los clientes del usuario (tanto para usuarios normales como administradores)
    clientes = usuario.clientes.all().select_related("tipo_cliente")
    user_has_clients = clientes.exists()

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
        # 👈 VARIABLES PARA CONTROL DE VISTAS:
        "es_administrador": usuario.is_staff,
        # Para administradores: obtener divisas para filtro de ganancias
        "divisas": Divisa.objects.filter(estado="activa").exclude(codigo="PYG") if usuario.is_staff else [],
    }

    return render(request, "usuarios/configuracion_usuario.html", context)


@login_required
def editar_perfil(request):
    """Vista para editar el perfil del usuario."""
    usuario = request.user
    if request.method == "POST":
        nuevo_nombre = request.POST.get("nombre", "").strip()
        if not nuevo_nombre:
            messages.error(request, "El nombre no puede estar vacío.")
        else:
            usuario.nombre = nuevo_nombre
            usuario.save()
            messages.success(request, "Tu nombre fue actualizado correctamente.")
            return redirect("usuarios:configuracion_usuario")

    return render(request, "usuarios/editar_perfil.html", {"usuario": usuario})
