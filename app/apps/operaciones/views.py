from django.shortcuts import get_object_or_404, redirect, render

from .forms import MonedaForm
from .models import Moneda


def create_moneda(request):
    """View para crear una nueva moneda.

    Args:
        request: La solicitud HTTP.

    """
    if request.method == "POST":
        # si se envía el formulario, se vinculan los datos al formulario
        form = MonedaForm(request.POST)
        if form.is_valid():
            # si el formulario es válido, guarda la nueva instancia de moneda en la base de datos
            moneda = form.save()
            return redirect(
                "operaciones:moneda_detail", pk=moneda.pk
            )  # Redirige a la vista de detalle con el namespace
    else:
        # si es una solicitud GET, crea un formulario vacío
        form = MonedaForm()

    # renderiza el formulario en la plantilla
    return render(request, "operaciones/create_moneda.html", {"form": form})


def edit_moneda(request, pk):
    """View para editar una moneda existente."""
    moneda = get_object_or_404(Moneda, pk=pk)
    if request.method == "POST":
        form = MonedaForm(request.POST, instance=moneda)
        if form.is_valid():
            form.save()
            return redirect("operaciones:moneda_detail", pk=moneda.pk)
    else:
        form = MonedaForm(instance=moneda)

    return render(request, "operaciones/edit_moneda.html", {"form": form, "moneda": moneda})


def delete_moneda(request, pk):
    """View para eliminar una moneda específica.

    Args:
        request: La solicitud HTTP.
        pk: El identificador de la moneda a eliminar.

    """
    moneda = get_object_or_404(Moneda, pk=pk)
    if request.method == "POST":
        moneda.delete()
        return redirect("operaciones:moneda_list")  # Redirige a la lista de monedas después de eliminar
    return render(request, "operaciones/moneda_confirm_delete.html", {"moneda": moneda})


def moneda_detail(request, pk):
    """View para mostrar los detalles de una moneda específica.

    Args:
        request: La solicitud HTTP.
        pk: El identificador de la moneda a mostrar.

    """
    moneda = get_object_or_404(Moneda, pk=pk)
    return render(request, "operaciones/moneda_detail.html", {"moneda": moneda})


def moneda_listar(request):
    """View para mostrar las monedas."""
    monedas = Moneda.objects.all().order_by("nombre")
    context = {
        "monedas": monedas,
    }
    return render(request, "operaciones/moneda_list.html", context)
