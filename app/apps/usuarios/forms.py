from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import PreferenciaNotificacion, Usuario


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        # modelo que usamos
        model = Usuario
        fields = ("nombre", "email", "password1", "password2")
        labels = {
            "nombre": _("Nombre completo"),
            "email": _("Correo electrónico"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # estilos Tailwind
        for field in self.fields.values():
            field.widget.attrs.update({"class": "w-full mt-1 p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"})


class PreferenciaNotificacionForm(forms.ModelForm):
    class Meta:
        model = PreferenciaNotificacion
        fields = ["habilitado", "frecuencia"]
        labels = {
            "habilitado": _("Activado"),
            "frecuencia": _("Frecuencia"),
        }
        help_texts = {
            "habilitado": _("Marque para que el cliente reciba actualizaciones de cambios en tasas."),
            "frecuencia": _("Seleccione la frecuencia de envío."),
        }
        widgets = {
            "habilitado": forms.CheckboxInput(
                attrs={
                    "class": "checkbox",
                    "aria-label": _("Activado"),
                    "title": _("Activado"),
                }
            ),
            "frecuencia": forms.Select(
                attrs={
                    "class": "select select-bordered w-full",
                    "aria-label": _("Frecuencia"),
                    "title": _("Frecuencia"),
                }
            ),
        }
