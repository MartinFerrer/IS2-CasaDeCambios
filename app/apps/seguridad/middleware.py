# middleware.py
from apps.usuarios.models import Cliente


class ClienteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
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
