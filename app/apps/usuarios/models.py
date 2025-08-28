from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# -----------------------
# MANAGER PERSONALIZADO
# -----------------------
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


# -----------------------
# MODELO USUARIO
# -----------------------
class Usuario(AbstractBaseUser, PermissionsMixin):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    rol = models.ForeignKey("Rol", on_delete=models.SET_NULL, null=True, blank=True)
    activo = models.BooleanField(default=True)

    # Campos requeridos para integrarse con Django Admin
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"  # login con email
    REQUIRED_FIELDS = ["nombre"]  # lo pide al crear superusuario

    def __str__(self):
        return self.nombre


# -----------------------
# MODELO PERMISO
# -----------------------
class Permiso(models.Model):
    nombre = models.CharField(max_length=30, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre


# -----------------------
# MODELO ROL
# -----------------------
class Rol(models.Model):
    nombre = models.CharField(max_length=30, unique=True)
    descripcion = models.TextField(blank=True)
    permisos = models.ManyToManyField(Permiso, blank=True)

    def __str__(self):
        return self.nombre
