"""Vistas para la aplicación de operaciones.

Este módulo contiene las vistas CRUD para el modelo TasaCambio.
"""

from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DivisaForm, TasaCambioForm
from .models import Divisa, TasaCambio, TasaCambioHistorial


def create_divisa(request):
    """View para crear una nueva divisa.

    Args:
        request: La solicitud HTTP.
    Retorna:
        HttpResponse: el formulario de creación o la redirección después de guardar.

    """
    if request.method == "POST":
        # si se envía el formulario, se vinculan los datos al formulario
        form = DivisaForm(request.POST)
        if form.is_valid():
            # si el formulario es válido, guarda la nueva instancia de divisa en la base de datos
            divisa = form.save()
            return redirect("operaciones:divisa_list", pk=divisa.pk)  # Redirige a la vista de detalle con el namespace
    else:
        # si es una solicitud GET, crea un formulario vacío
        form = DivisaForm()

    # renderiza el formulario en la plantilla
    return render(request, "crear_divisa.html", {"form": form})


def edit_divisa(request, pk):
    """View para editar una divisa existente.

    Args:
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
            return redirect("operaciones:divisa_detail", pk=divisa.pk)
    else:
        form = DivisaForm(instance=divisa)

    return render(request, "crear_divisa.html", {"form": form, "divisa": divisa})


def delete_divisa(request, pk):
    """View para eliminar una divisa específica.

    Args:
        request: La solicitud HTTP.
        pk: El identificador de la divisa a eliminar.
    Retorna:
        HttpResponse: Redirige a la lista de divisas después de eliminar.

    """
    divisa = get_object_or_404(Divisa, pk=pk)
    if request.method == "POST":
        divisa.delete()
        return redirect("operaciones:divisa_list")  # Redirige a la lista de divisas después de eliminar
    return render(request, "divisa_list.html", {"divisa": divisa})


def divisa_detail(request, pk):
    """View para mostrar los detalles de una divisa específica.

    Args:
        request: La solicitud HTTP.
        pk: El identificador de la divisa a mostrar.
    Retorna:
        HttpResponse: Renderiza el template divisa_detalle.html con el contexto de la divisa.

    """
    divisa = get_object_or_404(Divisa, pk=pk)
    return render(request, "divisa_detalle.html", {"divisa": divisa})


def divisa_listar(request):
    """View para mostrar las divisas.

    Args:
        request: La solicitud HTTP.

    Retorna:
        HttpResponse: Renderiza el template divisa_list.html con el contexto de las divisas.

    """
    divisas = Divisa.objects.all().order_by("nombre")
    context = {
        "divisas": divisas,
    }
    return render(request, "divisa_list.html", context)


def tasa_cambio_listar(request: HttpRequest) -> object:
    """Renderiza la página de listado de tasas de cambio.

    Args:
        request: Objeto HttpRequest.

    Retorna:
        HttpResponse: Renderiza el template tasa_cambio_list.html con el contexto de las tasas de cambio.

    """
    tasas = TasaCambio.objects.all().order_by("-fecha_actualizacion")
    return render(request, "tasa_cambio_list.html", {"tasas_de_cambio": tasas})


def tasa_cambio_crear(request: HttpRequest) -> object:
    """Crea una nueva tasa de cambio.

    Args:
        request: Objeto HttpRequest.

    Retorna:
        HttpResponse: Redirige al listado de tasas o renderiza el formulario de creación.

    """
    if request.method == "POST":
        form = TasaCambioForm(request.POST)
        if form.is_valid():
            nueva_tasa = form.save()
            # Guardar en el historial
            TasaCambioHistorial.objects.create(
                tasa_cambio_original=nueva_tasa,
                divisa_origen=nueva_tasa.divisa_origen,
                divisa_destino=nueva_tasa.divisa_destino,
                valor=nueva_tasa.valor,
                comision_compra=nueva_tasa.comision_compra,
                comision_venta=nueva_tasa.comision_venta,
                fecha_vigencia=nueva_tasa.fecha_vigencia,
                hora_vigencia=nueva_tasa.hora_vigencia,
                activo=nueva_tasa.activo,
                motivo="Creación de Tasa",
            )
            return redirect("operaciones:tasa_cambio_listar")
    else:
        form = TasaCambioForm()
    return render(request, "tasa_cambio_form.html", {"form": form})


def tasa_cambio_editar(request: HttpRequest, pk: str) -> object:
    """Edita una tasa de cambio existente.

    Args:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a editar.

    Retorna:
        HttpResponse: Redirige al listado de tasas o renderiza el formulario de edición.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)
    if request.method == "POST":
        form = TasaCambioForm(request.POST, instance=tasa)
        if form.is_valid():
            tasa_editada = form.save()
            # Guardar en el historial
            TasaCambioHistorial.objects.create(
                tasa_cambio_original=tasa_editada,
                divisa_origen=tasa_editada.divisa_origen,
                divisa_destino=tasa_editada.divisa_destino,
                valor=tasa_editada.valor,
                comision_compra=tasa_editada.comision_compra,
                comision_venta=tasa_editada.comision_venta,
                fecha_vigencia=tasa_editada.fecha_vigencia,
                hora_vigencia=tasa_editada.hora_vigencia,
                activo=tasa_editada.activo,
                motivo="Edición de Tasa",
            )
            return redirect("operaciones:tasa_cambio_listar")
    else:
        form = TasaCambioForm(instance=tasa)
    return render(request, "tasa_cambio_form.html", {"form": form})


def tasa_cambio_desactivar(request: HttpRequest, pk: str) -> object:
    """Desactiva una tasa de cambio existente.

    Args:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a desactivar.

    Retorna:
        HttpResponse: Redirige al listado de tasas.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)
    if request.method == "POST":
        tasa.activo = False
        tasa.save()
        # Guardar en el historial
        TasaCambioHistorial.objects.create(
            tasa_cambio_original=tasa,
            divisa_origen=tasa.divisa_origen,
            divisa_destino=tasa.divisa_destino,
            valor=tasa.valor,
            comision_compra=tasa.comision_compra,
            comision_venta=tasa.comision_venta,
            fecha_vigencia=tasa.fecha_vigencia,
            hora_vigencia=tasa.hora_vigencia,
            activo=tasa.activo,
            motivo="Desactivación de Tasa",
        )
        return redirect("operaciones:tasa_cambio_listar")
    return redirect("operaciones:tasa_cambio_listar")


def tasa_cambio_activar(request: HttpRequest, pk: str) -> object:
    """Activa una tasa de cambio existente.

    Args:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a activar.

    Retorna:
        HttpResponse: Redirige al listado de tasas.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)
    if request.method == "POST":
        tasa.activo = True
        tasa.save()
        # Guardar en el historial
        TasaCambioHistorial.objects.create(
            tasa_cambio_original=tasa,
            divisa_origen=tasa.divisa_origen,
            divisa_destino=tasa.divisa_destino,
            valor=tasa.valor,
            comision_compra=tasa.comision_compra,
            comision_venta=tasa.comision_venta,
            fecha_vigencia=tasa.fecha_vigencia,
            hora_vigencia=tasa.hora_vigencia,
            activo=tasa.activo,
            motivo="Activación de Tasa",
        )
        return redirect("operaciones:tasa_cambio_listar")
    return redirect("operaciones:tasa_cambio_listar")


def tasa_cambio_historial_listar(request: HttpRequest) -> object:
    """Renderiza la página de listado del historial de tasas de cambio con filtros.

    Args:
        request: Objeto HttpRequest.

    Retorna:
        HttpResponse: Renderiza el template tasa_cambio_historial_list.html con el contexto del historial filtrado.

    """
    historial = TasaCambioHistorial.objects.all()

    # Filtros
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    divisa = request.GET.get("divisa")
    motivo = request.GET.get("motivo")

    if fecha_inicio:
        historial = historial.filter(fecha_registro__gte=fecha_inicio)
    if fecha_fin:
        historial = historial.filter(fecha_registro__lte=fecha_fin)
    if divisa:
        historial = historial.filter(Q(divisa_origen__codigo=divisa) | Q(divisa_destino__codigo=divisa))
    if motivo:
        historial = historial.filter(motivo__icontains=motivo)

    context = {
        "historial": historial,
        "divisas": Divisa.objects.all(),  # Para el filtro de divisas
        "motivos": TasaCambioHistorial.objects.values_list("motivo", flat=True).distinct(),  # Para el filtro de motivos
    }

    return render(request, "tasa_cambio_historial_list.html", context)
