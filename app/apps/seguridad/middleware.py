"""Middleware para gestionar la selección y asignación de clientes en las solicitudes.

Este middleware se encarga de asociar un objeto Cliente a cada solicitud HTTP
basándose en la sesión del usuario autenticado. Si hay un cliente_id en la sesión,
intenta recuperar el cliente correspondiente. Si no, asigna el primer cliente
asociado al usuario. Esto facilita el acceso al cliente actual en vistas y
otros componentes de la aplicación.

Clases:
    ClienteMiddleware: Middleware principal que maneja la lógica de asignación
        de clientes.
"""

from apps.usuarios.models import Cliente


class ClienteMiddleware:
    """Middleware que asigna un objeto Cliente al request basado en la sesión del usuario autenticado.

    Este middleware verifica si el usuario está autenticado y, en caso afirmativo, intenta recuperar
    el cliente asociado desde la sesión. Si no hay un cliente en la sesión, asigna el primer cliente
    disponible para el usuario. Si el cliente en la sesión ya no existe, lo elimina de la sesión.
    Atributo:
        get_response (callable): Función que obtiene la respuesta del siguiente middleware o vista.
    Métodos:
        __init__(get_response): Inicializa el middleware con la función get_response.
        __call__(request): Procesa la solicitud, asigna request.cliente y devuelve la respuesta.
    """

    def __init__(self, get_response):
        """Inicializa el middleware con la función get_response."""
        self.get_response = get_response

    def __call__(self, request):
        """Procesa la solicitud, asigna request.cliente y devuelve la respuesta."""
        request.cliente = None

        if request.user.is_authenticated:
            cliente_id = request.session.get("cliente_id")
            if cliente_id:
                try:
                    request.cliente = Cliente.objects.get(id=cliente_id, usuarios=request.user)
                except Cliente.DoesNotExist:
                    request.session.pop("cliente_id", None)  # limpiar si ya no existe

            # Solo asignar el primer cliente si no hay cliente en sesión
            if request.cliente is None:
                cliente = Cliente.objects.filter(usuarios=request.user).first()
                if cliente:
                    request.session["cliente_id"] = cliente.id
                    request.cliente = cliente

        response = self.get_response(request)
        return response
