"""Procesadores de contexto para seguridad e información de usuario.

Este módulo proporciona procesadores de contexto que hacen que la información
del usuario y del cliente esté disponible en todos los templates.
"""


def user_context(request):
    """Agrega información del usuario y del cliente al contexto del template.

    Args:
        request: Objeto HttpRequest de Django.

    Returns:
        dict: Variables de contexto para los templates.

    """
    context = {}

    if hasattr(request, "user") and request.user.is_authenticated:
        # Verificar si el usuario tiene clientes asociados
        has_clients = hasattr(request.user, "clientes") and request.user.clientes.exists()
        context["user_has_clients"] = has_clients

        # Obtener cliente activo del middleware si está disponible
        if hasattr(request, "cliente"):
            context["active_client"] = request.cliente
        else:
            context["active_client"] = None

        # Obtener grupos del usuario para verificación de roles
        context["user_groups"] = list(request.user.groups.values_list("name", flat=True))

        # Verificar si el usuario es administrador o analista cambiario
        authorized_groups = ["Administrador", "Analista Cambiario"]
        context["user_is_admin"] = any(group in authorized_groups for group in context["user_groups"])

        # Función para verificar si el usuario tiene un permiso en el template
        def has_perm(permission_codename):
            """Verifica si el usuario actual tiene un permiso específico.

            Args:
            permission_codename: El codename del permiso a verificar.

            Returns:
            bool: True si el usuario tiene el permiso, False en caso contrario.

            """
            if request.user.is_superuser:
                return True

            # Obtener todos los permisos del usuario
            user_permissions = set()
            for perm in request.user.get_all_permissions():
                # Los permisos vienen en formato 'app_label.codename'
                if "." in perm:
                    user_permissions.add(perm.split(".")[1])
                user_permissions.add(perm)

            return permission_codename in user_permissions

        context["has_perm"] = has_perm

    return context
