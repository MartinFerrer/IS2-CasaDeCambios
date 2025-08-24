from django import forms
from .models import Usuario, Rol, Cliente

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre', 'email', 'password', 'rol', 'activo']
        widgets = {
            'password': forms.PasswordInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rol'].queryset = Rol.objects.all()

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['ruc', 'nombre', 'email', 'telefono', 'direccion', 'tipo_cliente']
        widgets = {
            'tipo_cliente': forms.Select(),
        }
