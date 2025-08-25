"""Módulo de modelos para el panel de administración.

Este módulo define los modelos de datos principales para el sistema:
- Permiso: Define los permisos disponibles en el sistema
- Rol: Agrupa permisos para asignar a usuarios
- Usuario: Representa usuarios del sistema
- Cliente: Almacena información de clientes
- TipoCliente: Define las categorías de clientes
"""

from django.db import models


class Permiso(models.Model):
    """Modelo que representa un permiso en el sistema.

    Campos:
        nombre (CharField): Nombre único del permiso.
        descripcion (TextField): Descripción opcional del permiso.
    """

    nombre = models.CharField(max_length=30, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self) -> str:
        """Devuelve una representación en cadena del Permiso."""
        return self.nombre


class Rol(models.Model):
    """Modelo que representa un rol en el sistema.

    Campos:
        nombre (CharField): Nombre único del rol.
        descripcion (TextField): Descripción opcional del rol.
        permisos (ManyToManyField): Permisos asociados al rol.
    """

    nombre = models.CharField(max_length=30, unique=True)
    descripcion = models.TextField(blank=True)
    permisos = models.ManyToManyField(Permiso, blank=True)

    def __str__(self) -> str:
        """Devuelve una representación en cadena del Rol."""
        return self.nombre


class Usuario(models.Model):
    """Modelo que representa un usuario en el sistema.

    Campos:
        nombre (CharField): Nombre del usuario.
        email (EmailField): Correo electrónico único del usuario.
        password (CharField): Contraseña encriptada del usuario.
        rol (ForeignKey): Rol asignado al usuario.
        activo (BooleanField): Indica si el usuario está activo.
    """

    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Aquí se almacena la contraseña encriptada
    rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self) -> str:
        """Devuelve una representación en cadena del Usuario."""
        return self.nombre


class Cliente(models.Model):
    """Modelo que representa un cliente en el sistema.

    Campos:
        ruc (CharField): RUC único del cliente.
        nombre (CharField): Nombre del cliente.
        email (EmailField): Correo electrónico único del cliente.
        telefono (CharField): Teléfono del cliente (opcional).
        direccion (CharField): Dirección del cliente (opcional).
        tipo_cliente (ForeignKey): Tipo de cliente asignado.
        usuarios (ManyToManyField): Usuarios asociados al cliente.
    """

    ruc = models.CharField(max_length=11, unique=True)
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    tipo_cliente = models.ForeignKey("TipoCliente", on_delete=models.SET_NULL, null=True, blank=True)
    usuarios = models.ManyToManyField("Usuario", blank=False, related_name="clientes")

    def __str__(self) -> str:
        """Devuelve una representación en cadena del Usuario."""
        return self.nombre


class TipoCliente(models.Model):
    """Modelo que representa un tipo de cliente en el sistema.

    Campos:
        nombre (CharField): Nombre único del tipo de cliente con opciones predefinidas.
        descripcion (TextField): Descripción opcional del tipo de cliente.
    Métodos:
        crear_tipos_por_defecto: Crea los tipos de cliente por defecto si no existen.
    """

    TIPO_CHOICES = (
        ("minorista", "Minorista"),
        ("corporativo", "Corporativo"),
        ("vip", "VIP"),
    )
    nombre = models.CharField(max_length=20, choices=TIPO_CHOICES, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self) -> str:
        """Devuelve una representación en cadena del TipoCliente."""
        return self.nombre
