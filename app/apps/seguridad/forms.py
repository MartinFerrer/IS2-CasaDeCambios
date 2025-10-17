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

    # Campo condicional para verificación TOTP cuando se habilita MFA para login
    codigo_verificacion = forms.CharField(
        max_length=6,
        min_length=6,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": (
                    "w-full p-3 border border-gray-300 rounded-xl focus:outline-none "
                    "focus:ring-2 focus:ring-blue-500 transition text-center text-2xl tracking-widest"
                ),
                "placeholder": "000000",
                "maxlength": 6,
                "pattern": "[0-9]{6}",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "id": "codigo-verificacion",
            }
        ),
        label="Código de verificación TOTP:",
        help_text=(
            "Requerido para habilitar MFA en login. Ingresa el código de 6 dígitos de tu aplicación de autenticación"
        ),
        error_messages={
            "required": "El código de verificación es obligatorio para habilitar MFA en login.",
            "max_length": "El código debe tener exactamente 6 dígitos.",
            "min_length": "El código debe tener exactamente 6 dígitos.",
        },
    )

    def __init__(self, *args, **kwargs):
        """Inicializa el formulario con usuario y perfil MFA."""
        self.usuario = kwargs.pop("usuario", None)
        self.perfil_mfa = kwargs.pop("perfil_mfa", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        """Validación personalizada del formulario."""
        cleaned_data = super().clean()
        mfa_login = cleaned_data.get("mfa_habilitado_login")
        codigo_verificacion = cleaned_data.get("codigo_verificacion")

        # Si se está habilitando MFA para login por primera vez o cambiando de deshabilitado a habilitado
        mfa_login_actual = self.perfil_mfa.mfa_habilitado_login if self.perfil_mfa else False

        if mfa_login and not mfa_login_actual:
            # Se está habilitando MFA para login - requerir verificación TOTP
            if not codigo_verificacion:
                # Si hay error, mantener el estado actual (no habilitar MFA)
                cleaned_data["mfa_habilitado_login"] = mfa_login_actual
                raise forms.ValidationError(
                    "Para habilitar MFA en login, debes ingresar el código de verificación TOTP. "
                    "Verifica los datos ingresados e intenta nuevamente."
                )

            # Verificar que el código sea válido
            if not codigo_verificacion.isdigit():
                # Si hay error, mantener el estado actual (no habilitar MFA)
                cleaned_data["mfa_habilitado_login"] = mfa_login_actual
                raise forms.ValidationError(
                    "El código de verificación TOTP debe contener solo números. "
                    "Verifica los datos ingresados e intenta nuevamente."
                )

            # Validar TOTP con el usuario
            if self.usuario and self.perfil_mfa:
                from .utils import verificar_codigo_usuario

                if not verificar_codigo_usuario(self.usuario, codigo_verificacion):
                    # Si hay error, mantener el estado actual (no habilitar MFA)
                    cleaned_data["mfa_habilitado_login"] = mfa_login_actual
                    raise forms.ValidationError(
                        "El código de verificación TOTP es incorrecto. "
                        "Verifica los datos ingresados e intenta nuevamente."
                    )

        return cleaned_data

    def clean_codigo_verificacion(self):
        """Valida que el código solo contenga números."""
        codigo = self.cleaned_data.get("codigo_verificacion")
        if codigo and not codigo.isdigit():
            raise forms.ValidationError("El código debe contener solo números.")
        return codigo
