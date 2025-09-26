"""Context processors for security and user information.

This module provides context processors that make user and client
information available in all templates.
"""


def user_context(request):
    """Add user and client information to template context.

    Args:
        request: Django HttpRequest object.

    Returns:
        dict: Context variables for templates.

    """
    context = {}

    if hasattr(request, "user") and request.user.is_authenticated:
        # Check if user has associated clients
        has_clients = hasattr(request.user, "clientes") and request.user.clientes.exists()
        context["user_has_clients"] = has_clients

        # Get active client from middleware if available
        if hasattr(request, "cliente"):
            context["active_client"] = request.cliente
        else:
            context["active_client"] = None

        # Get user's groups for role checking
        context["user_groups"] = list(request.user.groups.values_list("name", flat=True))

        # Check if user is admin or analyst
        authorized_groups = ["Administrador", "Analista Cambiario"]
        context["user_is_admin"] = any(group in authorized_groups for group in context["user_groups"])

    return context
