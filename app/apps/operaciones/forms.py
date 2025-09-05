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

    # Sobrescribimos el campo de Divisa de Destino para que no muestre PYG
    divisa_destino = forms.ModelChoiceField(
        queryset=Divisa.objects.exclude(codigo="PYG"),
        label="Divisa de Destino",
        help_text="Seleccione la divisa de destino para la tasa de cambio.",
    )

    class Meta:
        """Clase Meta para TasaCambioForm."""

        model = TasaCambio
        fields = [
            "divisa_origen",
            "divisa_destino",
            "valor",
            "comision_compra",
            "comision_venta",
            "fecha_vigencia",
            "hora_vigencia",
            "activo",
        ]
        labels = {
            "valor": "Valor de la Tasa",
            "comision_compra": "Comisión por Compra (Gs.)",
            "comision_venta": "Comisión por Venta (Gs.)",
            "fecha_vigencia": "Fecha de Vigencia",
            "hora_vigencia": "Hora de Vigencia",
            "activo": "Activa",
        }
        help_texts = {
            "valor": "Ingrese el monto en Gs. de la tasa de cambio.",
            "comision_compra": "Monto en Gs. que se resta al valor de la tasa para la compra.",
            "comision_venta": "Monto en Gs. que se suma al valor de la tasa para la venta.",
            "fecha_vigencia": "Fecha en la que la tasa de cambio entra en vigencia.",
            "hora_vigencia": "Hora en la que la tasa de cambio entra en vigencia.",
            "activo": "Marque para activar esta tasa de cambio.",
        }
        widgets = {
            "fecha_vigencia": forms.DateInput(attrs={"class": "input input-bordered w-full", "type": "date"}),
            "hora_vigencia": forms.TimeInput(attrs={"class": "input input-bordered w-full", "type": "time"}),
            "valor": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full validator",
                    "type": "number",
                    "min": "0",
                    "step": "0.001",
                    "required": "required",
                    "title": "El valor no puede ser un número negativo.",
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

        self.fields["divisa_destino"].widget.attrs.update({"class": "select select-bordered w-full"})

        # Después de que el formulario se inicializa (y carga los datos de la instancia),
        # verificamos si los valores de los campos son 0 y los reemplazamos por una cadena vacía.
        if self.instance:
            if self.instance.valor == Decimal("0.00"):
                self.fields["valor"].initial = ""
            if self.instance.comision_compra == Decimal("0.00"):
                self.fields["comision_compra"].initial = ""
            if self.instance.comision_venta == Decimal("0.00"):
                self.fields["comision_venta"].initial = ""
        else:
            # Para una nueva instancia de formulario, simplemente establecemos los valores iniciales como vacíos
            self.fields["valor"].initial = ""
            self.fields["comision_compra"].initial = ""
            self.fields["comision_venta"].initial = ""

        # Aplica las clases de estilo de DaisyUI a los otros widgets
        for field_name, field in self.fields.items():
            if field_name == "activo":
                # El campo booleano usa un widget CheckboxInput
                field.widget.attrs.update({"class": "checkbox"})
            elif field_name not in [
                "divisa_origen",
                "divisa_destino",
                "valor",
                "comision_compra",
                "comision_venta",
                "fecha_vigencia",
                "hora_vigencia",
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
        fields = ["codigo", "nombre", "simbolo"]
        labels = {
            "codigo": "Código",
            "nombre": "Nombre",
            "simbolo": "Símbolo",
        }
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "simbolo": forms.TextInput(attrs={"class": "form-control"}),
        }
