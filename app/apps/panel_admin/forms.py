"""Clases de Formularios para la aplicación de panel administrativo."""

from django import forms

from apps.usuarios.models import Cliente, Usuario


class UsuarioForm(forms.ModelForm):
    """Formulario de Usuario."""

    class Meta:
        """Meta clase conteniendo los campos del formulario de usuario."""

        model = Usuario
        fields = ["nombre", "email", "password", "rol", "activo"]
        widgets = {
            "password": forms.PasswordInput(),
            "rol": forms.Select(),
        }


class ClienteForm(forms.ModelForm):
    """Formulario de Cliente."""

    class Meta:
        """Meta clase conteniendo los campos del formulario de cliente."""

        model = Cliente
        fields = ["ruc", "nombre", "email", "telefono", "direccion", "tipo_cliente"]
        widgets = {
            "tipo_cliente": forms.Select(),
        }
