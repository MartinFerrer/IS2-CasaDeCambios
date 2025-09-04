from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import Usuario


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
