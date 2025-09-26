"""Vistas públicas del módulo de presentación.

Este módulo contiene vistas simples usadas en la página de inicio
y para seleccionar/cambiar el cliente activo en la sesión.

Documentación Sphinx / reStructuredText disponible para cada
objeto: funciones están documentadas con `:param`, `:type`,
` :returns:` y posibles códigos de estado HTTP.

Ejemplo:

.. code-block:: python

        from apps.presentacion import views

        # Llamada típica desde Django
        response = views.home(request)

"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from apps.usuarios.models import Cliente


def home(request):
    """Renderiza la página de inicio con el cliente actualmente seleccionado.

    Busca en la sesión la clave ``cliente_id`` y, si existe y corresponde a un
    ``Cliente`` válido, lo pasa al template ``index.html`` dentro del contexto
    con la clave ``cliente``.

    :param request: Objeto HttpRequest provisto por Django.
    :type request: django.http.HttpRequest
    :returns: HttpResponse con el template renderizado.
    :rtype: django.http.HttpResponse

    Comportamiento:

    - Si ``cliente_id`` no está en la sesión, se renderiza la página sin
        cliente (``cliente`` será ``None`` en el contexto).
    - Si ``cliente_id`` está en la sesión pero no existe en la base de datos,
        se elimina la clave de sesión para limpiar el estado.

    Nota: Esta vista no requiere autenticación explícita; el template puede
    mostrar controles diferentes según si hay un cliente en sesión.
    """
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
    """Cambia el cliente activo guardado en la sesión.

    Esta vista espera peticiones POST con el parámetro ``cliente_id``. Si se
    recibe un ``cliente_id`` válido se almacena en la sesión bajo la clave
    ``cliente_id`` y se devuelve un JSON indicando éxito.

    :param request: Objeto HttpRequest provisto por Django. Debe ser una
            petición POST para que la acción tenga efecto.
    :type request: django.http.HttpRequest
    :returns: JsonResponse indicando si la operación fue exitosa.
    :rtype: django.http.JsonResponse

    Respuestas:

    - 200 OK con ``{"success": True}`` cuando la sesión se guarda correctamente
        (incluye el caso en que ``cliente_id`` se proporciona pero no se valida
        contra la base de datos aquí — la validación puede realizarse en otro
        punto si es necesario).
    - 400 Bad Request con ``{"success": False}`` si la petición no es POST.

    Seguridad:

    - La vista está protegida por el decorador ``@login_required``, por lo que
        sólo usuarios autenticados pueden cambiar el cliente en la sesión.
    """
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        if cliente_id:
            request.session["cliente_id"] = cliente_id
            request.session.modified = True  # ⚡ Forzar guardar sesión
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)
