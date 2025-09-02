from django import forms

from .models import TasaCambio


class TasaCambioForm(forms.ModelForm):
    """Formulario para la creación y edición del modelo TasaCambio.
    Añade clases de DaisyUI para el estilo.
    """

    class Meta:
        model = TasaCambio
        fields = [
            "divisaOrigen",
            "divisaDestino",
            "valor",
            "comision_compra",
            "comision_venta",
            "fechaVigencia",
            "activo",
        ]
        labels = {
            "divisaOrigen": "Divisa de Origen",
            "divisaDestino": "Divisa de Destino",
            "valor": "Valor de la Tasa",
            "comision_compra": "Comisión por Compra (Gs.)",
            "comision_venta": "Comisión por Venta (Gs.)",
            "fechaVigencia": "Fecha de Vigencia",
            "activo": "Activa",
        }
        help_texts = {
            "divisaOrigen": "Seleccione la divisa de origen para la tasa de cambio.",
            "divisaDestino": "Seleccione la divisa de destino para la tasa de cambio.",
            "valor": "Ingrese el valor de la tasa de cambio.",
            "comision_compra": "Monto en Gs. que se suma al valor de la tasa para la compra.",
            "comision_venta": "Monto en Gs. que se suma al valor de la tasa para la venta.",
            "fechaVigencia": "Establezca la fecha a partir de la cual la tasa será válida.",
            "activo": "Marque esta opción para activar la tasa de cambio.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplica las clases de estilo de DaisyUI a los widgets
        for field_name, field in self.fields.items():
            if field_name in ["divisaOrigen", "divisaDestino"]:
                # Las claves foráneas usan un widget Select por defecto
                field.widget.attrs.update({"class": "select select-bordered w-full"})
            elif field_name == "activo":
                # El campo booleano usa un widget CheckboxInput
                field.widget.attrs.update({"class": "checkbox"})
            else:
                # El resto de los campos de texto y número usan Input
                field.widget.attrs.update({"class": "input input-bordered w-full"})


from .models import Divisa


class DivisaForm(forms.ModelForm):
    """Formulario para crear y editar divisas.

    Args:
        request: La solicitud HTTP.

    """

    class Meta:
        """Se define como se mostraran los campos del formulario.
        Los widgets son para personalizar la apariencia de los campos en la interfaz.
        """

        model = Divisa
        fields = ["nombre", "simbolo", "pais", "esta_activa", "comision", "tipo_de_cambio", "tasa_actual"]
        labels = {
            "nombre": "Nombre",
            "simbolo": "Símbolo",
            "pais": "País",
            "esta_activa": "Está Activa",
            "comision": "Comisión (%)",
            "tipo_de_cambio": "Tipo de Cambio",
            "tasa_actual": "Tasa Actual",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "simbolo": forms.TextInput(attrs={"class": "form-control"}),
            "pais": forms.TextInput(attrs={"class": "form-control"}),
            "esta_activa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "comision": forms.NumberInput(attrs={"class": "form-control"}),
            "tipo_de_cambio": forms.Select(attrs={"class": "form-control"}),
            "tasa_actual": forms.NumberInput(attrs={"class": "form-control"}),
        }
