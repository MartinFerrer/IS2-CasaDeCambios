# Importar el módulo de formularios de Django para crear formularios basados en modelos
from django import forms

from .models import Divisa, TasaCambio

"""Forms para app operaciones.

Este módulo contiene formularios de Django para crear y editar los modelos Divisa y TasaCambio.
"""


class TasaCambioForm(forms.ModelForm):
    """Formulario para la creación y edición del modelo TasaCambio."""

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
            "divisa_origen": "Divisa de Origen",
            "divisa_destino": "Divisa de Destino",
            "valor": "Valor de la Tasa",
            "comision_compra": "Comisión por Compra (Gs.)",
            "comision_venta": "Comisión por Venta (Gs.)",
            "fecha_vigencia": "Fecha de Vigencia",
            "activo": "Activa",
        }
        help_texts = {
            "divisa_origen": "Seleccione la divisa de origen para la tasa de cambio.",
            "divisa_destino": "Seleccione la divisa de destino para la tasa de cambio.",
            "valor": "Ingrese el valor de la tasa de cambio.",
            "comision_compra": "Monto en Gs. que se suma al valor de la tasa para la compra.",
            "comision_venta": "Monto en Gs. que se suma al valor de la tasa para la venta.",
            "fecha_vigencia": "Establezca la fecha a partir de la cual la tasa será válida.",
            "activo": "Marque esta opción para activar la tasa de cambio.",
        }

    def __init__(self, *args, **kwargs):
        """Inicializa el formulario y aplica clases de DaisyUI a los widgets."""
        super().__init__(*args, **kwargs)
        # Aplica las clases de estilo de DaisyUI a los widgets
        for field_name, field in self.fields.items():
            if field_name in ["divisa_origen", "divisa_destino"]:
                # Las claves foráneas usan un widget Select por defecto
                field.widget.attrs.update({"class": "select select-bordered w-full"})
            elif field_name == "activo":
                # El campo booleano usa un widget CheckboxInput
                field.widget.attrs.update({"class": "checkbox"})
            else:
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
