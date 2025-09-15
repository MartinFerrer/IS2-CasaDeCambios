from apps.usuarios.models import Usuario
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _


# class CustomUserCreationForm(UserCreationForm):
#     class Meta:
#         model = Usuario   # 👈 aquí usamos tu modelo, no el User default
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True, label=_("Correo electrónico"), widget=forms.EmailInput(attrs={"autocomplete": "email"})
    )

    password1 = forms.CharField(
        label=_("Contraseña"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_("Tu contraseña debe tener al menos 8 caracteres y no ser demasiado común."),
    )

    password2 = forms.CharField(
        label=_("Confirmar contraseña"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_("Ingresa la misma contraseña para verificación."),
    )

    class Meta:
        model = Usuario  # 👈 aquí usamos tu modelo, no el User default
        fields = ("nombre", "email", "password1", "password2")
        labels = {
            "nombre": _("Nombre completo"),
            "email": _("Correo electrónico"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ocultar todos los help_text
        for field in self.fields.values():
            field.help_text = None
            # Opcional: agregar clases de Tailwind a cada input
            field.widget.attrs.update(
                {"class": "w-full mt-1 p-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"}
            )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
