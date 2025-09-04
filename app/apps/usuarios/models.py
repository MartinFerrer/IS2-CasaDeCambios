from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# TODO [SCRUM-110]: Documentar modelos usuarios
class UsuarioManager(BaseUserManager):
    def create_user(self, email, nombre, password=None, **extra_fields):
        """Crea y guarda un usuario normal"""
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(email=email, nombre=nombre, **extra_fields)
        user.set_password(password)  # encripta la contraseña
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre, password=None, **extra_fields):
        """Crea y guarda un superusuario"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, nombre, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    activo = models.BooleanField(default=True)

    # Campos requeridos para integrarse con Django Admin
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"  # login con email
    REQUIRED_FIELDS = ["nombre"]  # lo pide al crear superusuario

    def __str__(self):
        return self.nombre


class TipoCliente(models.Model):
    """Modelo que representa el tipo de cliente."""

    nombre = models.CharField(max_length=50, unique=True)
    # Descuento configurable aplicado sobre la comisión en Compra/Venta de Divisas (y mostrado en simulación)
    descuento_sobre_comision = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=Decimal("0.0"),
    )  # 0.0 - 99.9

    def __str__(self) -> str:
        return self.nombre


class Cliente(models.Model):
    """Modelo que representa a un cliente."""

    ruc = models.CharField(max_length=11, unique=True)
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15, blank=True)
    direccion = models.CharField(max_length=255, blank=True)

    # referencia a TipoCliente
    tipo_cliente = models.ForeignKey(
        TipoCliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # referencia dinámica al modelo de usuario
    usuarios = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="clientes")

    def __str__(self):
        return self.nombre
