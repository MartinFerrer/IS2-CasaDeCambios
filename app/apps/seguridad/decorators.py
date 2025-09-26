"""Decoradores de seguridad para control de acceso basado en roles.

Este módulo proporciona decoradores que verifican si el usuario tiene
los permisos o roles necesarios para acceder a ciertas vistas.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def admin_required(view_func):
    """Decorador que requiere que el usuario tenga rol de Administrador o Analista Cambiario.

    Este decorador verifica que el usuario esté autenticado y pertenezca a uno de los
    grupos autorizados para acceder a funcionalidades administrativas.

    Args:
        view_func: La función de vista a decorar.

    Returns:
        La función decorada que incluye la verificación de permisos.

    Raises:
        PermissionDenied: Si el usuario no tiene los permisos necesarios.

    """

    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        # Verificar si el usuario pertenece a los grupos autorizados
        user_groups = request.user.groups.values_list("name", flat=True)
        authorized_groups = ["Administrador", "Analista Cambiario"]

        if not any(group in authorized_groups for group in user_groups):
            # Renderizar página de acceso denegado en lugar de lanzar excepción
            return render(
                request,
                "error_403.html",
                {"message": "No tienes permisos para acceder a esta área administrativa."},
                status=403,
            )

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def superuser_required(view_func):
    """Decorador que requiere que el usuario sea superusuario.

    Args:
        view_func: La función de vista a decorar.

    Returns:
        La función decorada que incluye la verificación de superusuario.

    """

    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(
                request,
                "error_403.html",
                {"message": "Solo los superusuarios pueden acceder a esta funcionalidad."},
                status=403,
            )

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def group_required(*group_names):
    """Decorador parametrizado que requiere que el usuario pertenezca a uno de los grupos especificados.

    Args:
        *group_names: Nombres de los grupos autorizados.

    Returns:
        El decorador configurado.

    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user_groups = request.user.groups.values_list("name", flat=True)

            if not any(group in group_names for group in user_groups):
                return render(
                    request,
                    "error_403.html",
                    {"message": f"Necesitas pertenecer a uno de estos grupos: {', '.join(group_names)}"},
                    status=403,
                )

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def client_required(view_func):
    """Decorador que requiere que el usuario tenga al menos un cliente asociado.

    Este decorador verifica que el usuario esté autenticado y tenga al menos
    un cliente asociado para poder realizar transacciones.

    Args:
        view_func: La función de vista a decorar.

    Returns:
        La función decorada que incluye la verificación de cliente asociado.

    """

    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        # Verificar si el usuario tiene clientes asociados
        if not hasattr(request.user, "clientes") or not request.user.clientes.exists():
            return render(
                request,
                "error_403.html",
                {"message": "Necesita un cliente asociado para realizar la acción."},
                status=403,
            )

        return view_func(request, *args, **kwargs)

    return _wrapped_view
