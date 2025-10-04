from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from apps.usuarios.models import Usuario

from .models import PerfilMFA


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


class CodigoMFAForm(forms.Form):
    """Formulario para ingresar código TOTP de MFA."""

    codigo = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition text-center text-2xl tracking-widest",
                "placeholder": "000000",
                "maxlength": 6,
                "pattern": "[0-9]{6}",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
            }
        ),
        help_text="Ingresa el código de 6 dígitos de tu aplicación de autenticación",
        error_messages={
            "required": "El código TOTP es obligatorio.",
            "max_length": "El código debe tener exactamente 6 dígitos.",
            "min_length": "El código debe tener exactamente 6 dígitos.",
        },
    )

    def clean_codigo(self):
        """Valida que el código solo contenga números."""
        codigo = self.cleaned_data.get("codigo")
        if codigo and not codigo.isdigit():
            raise forms.ValidationError("El código debe contener solo números.")
        return codigo


class ConfiguracionMFAForm(forms.ModelForm):
    """Formulario para configurar MFA del usuario."""

    class Meta:
        """Configuración del formulario."""

        model = PerfilMFA
        fields = ["mfa_habilitado_login", "mfa_habilitado_transacciones"]

    mfa_habilitado_login = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
            }
        ),
        label="Habilitar autenticación de dos factores (2FA) para el login",
        help_text="Cuando esté habilitado, se te pedirá un código adicional al iniciar sesión",
    )

    mfa_habilitado_transacciones = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "w-4 h-4 text-green-600 bg-gray-100 border-gray-300 rounded focus:ring-green-500 focus:ring-2"
            }
        ),
        label="Habilitar autenticación de dos factores (2FA) para transacciones",
        help_text="Recomendado: Se te pedirá un código adicional antes de procesar transacciones importantes",
    )
