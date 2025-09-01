from django import forms

from .models import Moneda


class MonedaForm(forms.ModelForm):
    """Formulario para crear y editar monedas.

    Args:
        request: La solicitud HTTP.

    """

    class Meta:
        """Se define como se mostraran los campos del formulario.
        Los widgets son para personalizar la apariencia de los campos en la interfaz.
        """

        model = Moneda
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
