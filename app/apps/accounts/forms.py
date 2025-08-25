from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label=_("Correo electrónico"),
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )

    password1 = forms.CharField(
        label=_("Contraseña"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=_("Tu contraseña debe tener al menos 8 caracteres y no ser demasiado común."),
    )

    password2 = forms.CharField(
        label=_("Confirmar contraseña"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=_("Ingresa la misma contraseña para verificación."),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        labels = {
            "username": _("Nombre de usuario"),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
