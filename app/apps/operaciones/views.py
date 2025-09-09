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
                        "pk": str(divisa.pk),
                        "codigo": divisa.codigo,
                        "nombre": divisa.nombre,
                        "simbolo": divisa.simbolo,
                        "estado": divisa.estado,
                    },
                },
                status=201,
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    form = DivisaForm()
    return render(request, "operaciones/divisa_list.html", {"form": form})


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
        divisa.codigo = request.POST.get("codigo")
        divisa.nombre = request.POST.get("nombre")
        divisa.simbolo = request.POST.get("simbolo")
        divisa.estado = request.POST.get("estado")
        divisa.save()
        return redirect("operaciones:divisa_list")

    return redirect("operaciones:divisa_list")


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
    print(f"DEBUG divisa_listar: Found {divisas.count()} currencies in database")
    for divisa in divisas:
        print(f"DEBUG: {divisa.pk} - {divisa.codigo} - {divisa.nombre}")
    return render(request, "divisa_list.html", {"object_list": divisas})


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

    Argumento:
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


@require_GET
def tasas_cambio_api(request: HttpRequest) -> JsonResponse:
    """API endpoint que devuelve las tasas de cambio actuales en formato JSON.

    Args:
        request: Objeto HttpRequest.

    Retorna:
        JsonResponse: JSON con las tasas de cambio activas.

    """
    # Obtener solo las tasas activas, ordenadas por divisa origen
    tasas = (
        TasaCambio.objects.filter(activo=True)
        .select_related("divisa_origen", "divisa_destino")
        .order_by("divisa_origen__codigo")
    )

    tasas_data = []
    for tasa in tasas:
        # Calcular precio de compra y venta
        if tasa.divisa_origen.codigo == "PYG":
            # Si la divisa origen es PYG, entonces vendemos la divisa destino
            precio_compra = float(tasa.valor) + float(tasa.comision_compra)
            precio_venta = float(tasa.valor) - float(tasa.comision_venta)
            divisa_mostrar = tasa.divisa_destino
        else:
            # Si la divisa destino es PYG, entonces compramos la divisa origen
            precio_compra = float(tasa.valor) - float(tasa.comision_compra)
            precio_venta = float(tasa.valor) + float(tasa.comision_venta)
            divisa_mostrar = tasa.divisa_origen

        tasas_data.append(
            {
                "divisa": {
                    "codigo": divisa_mostrar.codigo,
                    "nombre": divisa_mostrar.nombre,
                    "simbolo": divisa_mostrar.simbolo,
                },
                "precio_compra": precio_compra,
                "precio_venta": precio_venta,
                "fecha_actualizacion": tasa.fecha_actualizacion.isoformat(),
                "fecha_vigencia": tasa.fecha_vigencia.isoformat(),
            }
        )

    return JsonResponse({"tasas": tasas_data, "total": len(tasas_data)})


@require_GET
def historial_tasas_api(request: HttpRequest) -> JsonResponse:
    """API endpoint que devuelve el historial de tasas de cambio para el gráfico."""
    tasas = (
        TasaCambio.objects.filter(activo=True)
        .select_related("divisa_origen", "divisa_destino")
        .order_by("fecha_actualizacion")
    )

    historial = {}
    for tasa in tasas:
        # Determinar qué divisa mostrar
        if tasa.divisa_origen.codigo == "PYG":
            divisa = tasa.divisa_destino.codigo
            precio_compra = float(tasa.valor) + float(tasa.comision_compra)
            precio_venta = float(tasa.valor) - float(tasa.comision_venta)
        else:
            divisa = tasa.divisa_origen.codigo
            precio_compra = float(tasa.valor) - float(tasa.comision_compra)
            precio_venta = float(tasa.valor) + float(tasa.comision_venta)

        # Inicializar estructura si no existe
        if divisa not in historial:
            historial[divisa] = {"fechas": [], "compra": [], "venta": []}

        # Agregar datos
        historial[divisa]["fechas"].append(tasa.fecha_actualizacion.isoformat())
        historial[divisa]["compra"].append(precio_compra)
        historial[divisa]["venta"].append(precio_venta)

    return JsonResponse({"historial": historial})


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
