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


def permission_required(*permission_codenames, require_all=False):
    """Decorador parametrizado que requiere que el usuario tenga uno o más permisos específicos.

    Este decorador verifica que el usuario esté autenticado y tenga los permisos
    necesarios para acceder a la vista. Los permisos se verifican por codename.

    Args:
        *permission_codenames: Codenames de los permisos requeridos (ej: 'view_usuario', 'change_cliente').
        require_all: Si es True, requiere todos los permisos. Si es False (default),
                    requiere al menos uno de los permisos listados.

    Returns:
        El decorador configurado.

    Examples:
        @permission_required('view_usuario')  # Requiere el permiso view_usuario
        @permission_required('view_usuario', 'change_usuario')  # Requiere al menos uno
        @permission_required('view_usuario', 'change_usuario', require_all=True)  # Requiere ambos

    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # Superusuarios tienen todos los permisos
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Construir el formato completo del permiso: app_label.codename
            user_permissions = set()
            for perm in request.user.get_all_permissions():
                # Los permisos vienen en formato 'app_label.codename'
                if "." in perm:
                    user_permissions.add(perm.split(".")[1])
                user_permissions.add(perm)

            # Verificar si el usuario tiene los permisos necesarios
            has_permission = False
            if require_all:
                # Requiere todos los permisos
                has_permission = all(perm in user_permissions for perm in permission_codenames)
            else:
                # Requiere al menos uno de los permisos
                has_permission = any(perm in user_permissions for perm in permission_codenames)

            if not has_permission:
                permisos_texto = " y ".join(permission_codenames) if require_all else " o ".join(permission_codenames)
                return render(
                    request,
                    "error_403.html",
                    {"message": f"No tienes los permisos necesarios: {permisos_texto}"},
                    status=403,
                )

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
