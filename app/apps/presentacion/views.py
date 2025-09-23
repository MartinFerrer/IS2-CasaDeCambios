from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.usuarios.models import Cliente


def home(request):
    """Vista para la página de inicio."""
    cliente_id = request.session.get("cliente_id")
    cliente = None
    if cliente_id:
        try:
            cliente = Cliente.objects.get(id=cliente_id)
        except Cliente.DoesNotExist:
            request.session.pop("cliente_id", None)  # limpiar si no existe

    return render(request, "index.html", {"cliente": cliente})


@login_required
def cambiar_cliente(request):
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        if cliente_id:
            # Validar que el cliente pertenece al usuario
            cliente = get_object_or_404(Cliente, id=cliente_id, usuarios=request.user)
            request.session["cliente_id"] = cliente.id
    return redirect("presentacion:home")
