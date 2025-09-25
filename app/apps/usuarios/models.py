"""Modelos y gestores del app `usuarios`.

Este módulo define los modelos relacionados con usuarios y clientes que usa
la aplicación. Se incluyen:

- ``UsuarioManager``: gestor personalizado para crear usuarios y
  superusuarios.
- ``Usuario``: modelo de usuario personalizado que sustituye al
  modelo por defecto de Django en esta aplicación.
- ``TipoCliente``: clasifica clientes por tipo y aplica un posible
  descuento sobre comisiones.
- ``Cliente``: datos de clientes con validación específica del RUC.

Las docstrings usan el estilo Sphinx/reStructuredText para facilitar la
generación automática de la documentación del proyecto.
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models

from utils.validators import limpiar_ruc, validar_ruc_completo


# TODO [SCRUM-110]: Documentar modelos usuarios (completado parcialmente con docstrings)
class UsuarioManager(BaseUserManager):
    """Gestor personalizado para el modelo ``Usuario``.

    Proporciona métodos convenientes para crear usuarios y
    superusuarios respetando la lógica de `AbstractBaseUser`.

    Métodos
    -------
    create_user(email, nombre, password=None, **extra_fields)
        Crea y persiste un usuario normal.

    create_superuser(email, nombre, password=None, **extra_fields)
        Crea y persiste un superusuario con permisos de administrador.
    """

    def create_user(self, email, nombre, password=None, **extra_fields):
        """Crear y guardar un usuario normal.

        :param email: Correo electrónico del usuario (obligatorio).
        :type email: str
        :param nombre: Nombre completo del usuario.
        :type nombre: str
        :param password: Contraseña en texto plano (se encripta internamente).
        :type password: str or None
        :returns: Instancia del usuario creada.
        :rtype: Usuario
        :raises ValueError: Si no se proporciona el email.
        """
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(email=email, nombre=nombre, **extra_fields)
        user.set_password(password)  # encripta la contraseña
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre, password=None, **extra_fields):
        """Crear y guardar un superusuario.

        Establece los flags ``is_staff`` e ``is_superuser`` a True antes de
        delegar en :meth:`create_user`.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, nombre, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Modelo de usuario personalizado.

    Atributos principales
    ---------------------
    nombre
        Nombre completo del usuario.
    email
        Correo electrónico único usado como identificador de login.
    activo
        Flag booleano que indica si la cuenta está activa.
    is_staff
        Flag requerido por Django Admin para permitir acceso al sitio
        administrativo.

    Configuración de Django
    -----------------------
    ``USERNAME_FIELD``
        Campo usado como identificador de usuario (``email``).
    ``REQUIRED_FIELDS``
        Campos requeridos al crear un superusuario desde la línea de
        comandos (``nombre``).
    """

    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    activo = models.BooleanField(default=True)

    # Campos requeridos para integrarse con Django Admin
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"  # login con email
    REQUIRED_FIELDS = ["nombre"]  # lo pide al crear superusuario

    def __str__(self):
        """Representación legible del usuario.

        :returns: Nombre del usuario.
        :rtype: str
        """
        return self.nombre


class TipoCliente(models.Model):
    """Clasificación de clientes.

    Esta entidad permite diferenciar clientes por grupos comerciales o
    por niveles que definan descuentos sobre comisiones. El campo
    ``descuento_sobre_comision`` es un Decimal que representa el porcentaje
    (por ejemplo, 5.0 representa un 5%% de descuento).
    """

    nombre = models.CharField(max_length=50, unique=True)
    # Descuento configurable aplicado sobre la comisión en Compra/Venta de Divisas (y mostrado en simulación)
    descuento_sobre_comision = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=Decimal("0.0"),
    )  # 0.0 - 99.9

    def __str__(self) -> str:
        """Devuelve el nombre legible del tipo de cliente.

        :returns: Nombre del tipo de cliente.
        :rtype: str
        """
        return self.nombre


class Cliente(models.Model):
    """Modelo que representa a un cliente de la casa de cambios.

    Campos principales
    ------------------
    ruc
        Cadena que contiene el RUC del cliente. Se aplica limpieza y
        validación del dígito verificador en :meth:`clean`.
    nombre
        Nombre o razón social del cliente.
    email
        Correo electrónico único del cliente.
    telefono, direccion
        Datos de contacto adicionales (opcionales).
    tipo_cliente
        FK a :class:`TipoCliente` para asignar descuentos o clasificaciones.
    usuarios
        Relación ManyToMany con el modelo de usuario configurado en
        ``settings.AUTH_USER_MODEL``.
    """

    ruc = models.CharField(max_length=12, unique=True)
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

    def clean(self):
        """Validación y normalización del RUC.

        - Limpia el RUC (elimina espacios, guiones, etc.) mediante
          :func:`utils.validators.limpiar_ruc`.
        - Valida el dígito verificador con
          :func:`utils.validators.validar_ruc_completo`.
        - Si la validación es correcta, formatea el RUC insertando un
          guion antes del dígito verificador (p.ej. ``12345678-9``).

        :raises ValidationError: Si el dígito verificador es inválido.
        """
        super().clean()

        if self.ruc:
            # Limpiar el RUC (remover espacios, guiones, etc.)
            ruc_limpio = limpiar_ruc(self.ruc)

            # Validar dígito verificador
            if not validar_ruc_completo(ruc_limpio):
                raise ValidationError({"ruc": "El dígito verificador del RUC no es válido."})
            self.ruc = ruc_limpio[:-1] + "-" + ruc_limpio[-1]

    def save(self, *args, **kwargs):
        """Sobrescribe :meth:`models.Model.save` para asegurar validación.

        Llama a :meth:`full_clean` antes de llamar al método de guardado
        base, garantizando que las validaciones del modelo se ejecuten
        siempre al persistir una instancia.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Representación legible del cliente.

        :returns: Nombre o razón social del cliente.
        :rtype: str
        """
        return self.nombre
