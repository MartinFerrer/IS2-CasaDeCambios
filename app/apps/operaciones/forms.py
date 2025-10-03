"""Forms para app operaciones.

Este módulo contiene formularios de Django para crear y editar los modelos Divisa y TasaCambio.
Incluye:
- TasaCambioForm: formulario para crear y editar tasas de cambio
- DivisaForm: formulario para crear y editar divisas
"""

from decimal import Decimal

from django import forms

from .models import Divisa, TasaCambio


class TasaCambioForm(forms.ModelForm):
    """Formulario para la creación y edición del modelo TasaCambio."""

    # Sobrescribimos el campo de Divisa de Origen para que solo muestre PYG
    divisa_origen = forms.ModelChoiceField(
        queryset=Divisa.objects.filter(codigo="PYG"),
        label="Divisa de Origen",
        help_text="La divisa desde la cual se realiza la conversión. (Fijo en PYG)",
    )

    class Meta:
        """Clase Meta para TasaCambioForm."""

        model = TasaCambio
        fields = [
            "divisa_origen",
            "divisa_destino",
            "precio_base",
            "comision_compra",
            "comision_venta",
            "activo",
        ]
        labels = {
            "precio_base": "Precio Base",
            "comision_compra": "Comisión por Compra (Gs.)",
            "comision_venta": "Comisión por Venta (Gs.)",
            "activo": "Activa",
        }
        help_texts = {
            "precio_base": "Ingrese el precio base en Gs. de la divisa.",
            "comision_compra": "Monto en Gs. que se resta al precio base para la compra.",
            "comision_venta": "Monto en Gs. que se suma al precio base para la venta.",
            "activo": "Marque para activar esta tasa de cambio.",
        }
        widgets = {
            "precio_base": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full validator",
                    "type": "number",
                    "min": "1",
                    "step": "0.001",
                    "required": "required",
                    "title": "El precio base no puede ser un número negativo.",
                    "placeholder": "",
                }
            ),
            "comision_compra": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full validator",
                    "type": "number",
                    "min": "0",
                    "step": "0.001",
                    "required": "required",
                    "title": "La comisión no puede ser un número negativo.",
                    "placeholder": "",
                }
            ),
            "comision_venta": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full validator",
                    "type": "number",
                    "min": "0",
                    "step": "0.001",
                    "required": "required",
                    "title": "La comisión no puede ser un número negativo.",
                    "placeholder": "",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Inicializa el formulario y aplica clases de DaisyUI a los widgets."""
        super().__init__(*args, **kwargs)

        self.fields["divisa_origen"].initial = Divisa.objects.get(codigo="PYG")
        self.fields["divisa_origen"].disabled = True

        # Excluir todas las divisas que ya están como destino en cualquier TasaCambio
        used_divisas = TasaCambio.objects.all()
        if self.instance and self.instance.pk:
            used_divisas = used_divisas.exclude(pk=self.instance.pk)
        used_divisas_ids = used_divisas.values_list("divisa_destino", flat=True)

        # Mostrar solo divisas activas
        available_divisas = (
            Divisa.objects.exclude(codigo="PYG").filter(estado="activa").exclude(pk__in=used_divisas_ids)
        )
        if self.instance and self.instance.pk and self.instance.divisa_destino_id:
            available_divisas = available_divisas | Divisa.objects.filter(pk=self.instance.divisa_destino_id)

        # El campo divisa_destino se define en __init__ para evitar problemas de asignación de queryset
        self.fields["divisa_destino"] = forms.ModelChoiceField(
            queryset=available_divisas,
            label="Divisa de Destino",
            help_text="Seleccione la divisa de destino para la tasa de cambio.",
        )
        self.fields["divisa_destino"].widget.attrs.update({"class": "select select-bordered w-full"})

        # Después de que el formulario se inicializa (y carga los datos de la instancia),
        # verificamos si los valores de los campos son 0 y los reemplazamos por una cadena vacía.
        if self.instance:
            if self.instance.precio_base == Decimal("0.00"):
                self.fields["precio_base"].initial = ""
            if self.instance.comision_compra == Decimal("0.00"):
                self.fields["comision_compra"].initial = ""
            if self.instance.comision_venta == Decimal("0.00"):
                self.fields["comision_venta"].initial = ""

        # Aplicar clases de DaisyUI a todos los campos
        for field_name, field in self.fields.items():
            if field_name == "activo":
                field.widget.attrs.update({"class": "checkbox"})
            elif field_name not in [
                "divisa_origen",
                "divisa_destino",
                "precio_base",
                "comision_compra",
                "comision_venta",
            ]:
                # El resto de los campos de texto y número usan Input
                field.widget.attrs.update({"class": "input input-bordered w-full"})


class DivisaForm(forms.ModelForm):
    """Formulario para crear y editar divisas."""

    class Meta:
        """Se define como se mostraran los campos del formulario.

        Los widgets son para personalizar la apariencia de los campos en la interfaz.
        """

        model = Divisa
        fields = ["codigo", "nombre", "simbolo", "estado"]
        labels = {
            "codigo": "Código",
            "nombre": "Nombre",
            "simbolo": "Símbolo",
            "estado": "Estado",
        }
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "simbolo": forms.TextInput(attrs={"class": "form-control", "required": False}),
            "estado": forms.Select(attrs={"class": "select select-bordered w-full"}),
        }
