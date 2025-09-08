"""Vistas para la aplicación de operaciones.

Este módulo contiene las vistas CRUD para el modelo TasaCambio.
"""

import pycountry
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from forex_python.converter import CurrencyCodes

from .forms import DivisaForm, TasaCambioForm
from .models import Divisa, TasaCambio


def crear_divisa(request):
    """View para crear una nueva divisa.

    Argumento:
        request: La solicitud HTTP.
    Retorna:
        HttpResponse: el formulario de creación o la redirección después de guardar.

    """
    if request.method == "POST":
        form = DivisaForm(request.POST)
        if form.is_valid():
            divisa = form.save()
            return JsonResponse(
                {
                    "success": True,
                    "message": "Divisa creada exitosamente",
                    "divisa": {
                        "pk": str(divisa.pk),  # Ensure PK is string
                        "codigo": divisa.codigo,
                        "nombre": divisa.nombre,
                        "simbolo": divisa.simbolo,
                    },
                },
                status=201,
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    form = DivisaForm()
    return render(request, "operaciones/crear_divisa.html", {"form": form})


def obtener_divisas(request: HttpRequest) -> JsonResponse:
    """Obtiene las divisas disponibles en el sistema y las devuelve como un JSON.

    Esta vista utiliza la librería `pycountry` para obtener una lista de códigos
    ISO de divisas.

    Argumentos:
        request: La solicitud HTTP.

    Returns:
        JsonResponse: Una respuesta HTTP con una lista de diccionarios de divisas.

    """
    c = CurrencyCodes()
    data = []
    # mantengo el ingles para que tenga coherencia con las librerias
    for currency in pycountry.currencies:
        codigo = getattr(currency, "alpha_3", None)
        if not codigo:
            continue
        nombre = getattr(currency, "name", "Desconocida")
        simbolo = c.get_symbol(codigo)
        data.append({"codigo": codigo, "nombre": nombre, "simbolo": simbolo})

    return JsonResponse(data, safe=False)


def edit_divisa(request, pk):
    """View para editar una divisa existente.

    Argumentos:
        request: La solicitud HTTP.
        pk: El identificador de la divisa a editar.
    Retorna:
        HttpResponse: el formulario de edición o la redirección después de guardar.

    """
    divisa = get_object_or_404(Divisa, pk=pk)
    if request.method == "POST":
        form = DivisaForm(request.POST, instance=divisa)
        if form.is_valid():
            form.save()
            return redirect("operaciones:divisa_list")
    else:
        form = DivisaForm(instance=divisa)
    divisas = Divisa.objects.all().order_by("codigo")

    return render(request, "divisa_list.html", {"form": form, "divisa": divisa, "object_list": divisas})


def delete_divisa(request, pk):
    """View para eliminar una divisa específica.

    Argumento:
        request: La solicitud HTTP.
        pk: El identificador de la divisa a eliminar.
    Retorna:
        HttpResponse: Redirige a la lista de divisas después de eliminar.

    """
    divisa = get_object_or_404(Divisa, pk=pk)
    if request.method == "POST":
        divisa.delete()
        return redirect("operaciones:divisa_list")  # Redirige a la lista de divisas después de eliminar
    return redirect("operaciones:divisa_detail", pk=pk)


def divisa_detail(request, pk):
    """View para mostrar los detalles de una divisa específica.

    Argumento:
        request: La solicitud HTTP.
        pk: El identificador de la divisa a mostrar.
    Retorna:
        HttpResponse: Renderiza el template divisa_detalle.html con el contexto de la divisa.

    """
    divisa = get_object_or_404(Divisa, pk=pk)
    return render(request, "divisa_detalle.html", {"divisa": divisa})


def divisa_listar(request: HttpRequest) -> object:
    """Muestra el listado de todas las divisas en el sistema.

    Argumentos:
        request: La solicitud HTTP.

    Retorna:
        HttpResponse: La página HTML con la lista de divisas.
    """
    divisas = Divisa.objects.all().order_by("codigo")
    # ===== ADD DEBUG PRINT =====
    print(f"DEBUG divisa_listar: Found {divisas.count()} currencies in database")
    for divisa in divisas:
        print(f"DEBUG: {divisa.pk} - {divisa.codigo} - {divisa.nombre}")
    # ===== END DEBUG PRINT =====
    return render(request, "divisa_list.html", {"object_list": divisas})


def tasa_cambio_listar(request: HttpRequest) -> object:
    """Renderiza la página de listado de tasas de cambio.

    Argumento:
        request: Objeto HttpRequest.

    Retorna:
        HttpResponse: Renderiza el template tasa_cambio_list.html con el contexto de las tasas de cambio.

    """
    tasas = TasaCambio.objects.all().order_by("-fecha_actualizacion")
    return render(request, "tasa_cambio_list.html", {"tasas_de_cambio": tasas})


def tasa_cambio_crear(request: HttpRequest) -> object:
    """Crea una nueva tasa de cambio.

    Argumento:
        request: Objeto HttpRequest.

    Retorna:
        HttpResponse: Redirige al listado de tasas o renderiza el formulario de creación.

    """
    if request.method == "POST":
        form = TasaCambioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("operaciones:tasa_cambio_listar")
    else:
        form = TasaCambioForm()
    return render(request, "tasa_cambio_form.html", {"form": form})


def tasa_cambio_editar(request: HttpRequest, pk: str) -> object:
    """Edita una tasa de cambio existente.

    Argumento:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a editar.

    Retorna:
        HttpResponse: Redirige al listado de tasas o renderiza el formulario de edición.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)
    if request.method == "POST":
        form = TasaCambioForm(request.POST, instance=tasa)
        if form.is_valid():
            form.save()
            return redirect("operaciones:tasa_cambio_listar")
    else:
        form = TasaCambioForm(instance=tasa)
    return render(request, "tasa_cambio_form.html", {"form": form})


def tasa_cambio_desactivar(request: HttpRequest, pk: str) -> object:
    """Desactiva una tasa de cambio existente.

    Argumento:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a desactivar.

    Retorna:
        HttpResponse: Redirige al listado de tasas.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)
    if request.method == "POST":
        tasa.activo = False
        tasa.save()
        return redirect("operaciones:tasa_cambio_listar")
    # Redirige de vuelta si no es un POST, o podrías usar un template de confirmación.
    return redirect("operaciones:tasa_cambio_listar")


def tasa_cambio_activar(request: HttpRequest, pk: str) -> object:
    """Activa una tasa de cambio existente.

    Argumento:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a activar.

    Retorna:
        HttpResponse: Redirige al listado de tasas.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)
    if request.method == "POST":
        tasa.activo = True
        tasa.save()
        return redirect("operaciones:tasa_cambio_listar")
    # Redirige de vuelta si no es un POST.
    return redirect("operaciones:tasa_cambio_listar")
