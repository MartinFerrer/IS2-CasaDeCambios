from django.conf import settings
from django.db import models


class TipoCliente(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    ruc = models.CharField(max_length=11, unique=True)
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15, blank=True)
    direccion = models.CharField(max_length=255, blank=True)

    # referencia a TipoCliente
    tipo_cliente = models.ForeignKey(TipoCliente, on_delete=models.SET_NULL, null=True, blank=True)

    # referencia dinámica al modelo de usuario
    usuarios = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="clientes")

    def __str__(self):
        return self.nombre
