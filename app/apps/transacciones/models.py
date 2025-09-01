from datetime import date

from django.core.exceptions import ValidationError
from django.db import models


class MedioDePago(models.Model):
    """Modelo base abstracto para todos los medios de pago."""

    cliente = models.ForeignKey("usuarios.Cliente", on_delete=models.CASCADE, related_name="%(class)s_set")
    alias = models.CharField(max_length=50, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-fecha_creacion"]

    def generar_alias(self) -> str:
        """Genera un alias automático para el medio de pago."""
        return f"{self.__class__.__name__}"

    def __str__(self):
        return f"{self.__class__.__name__} - {self.cliente.nombre}" + (f" ({self.alias})" if self.alias else "")


class TarjetaCredito(MedioDePago):
    """Modelo para tarjetas de crédito."""

    numero_tarjeta = models.CharField(max_length=16)  # No modificable después de crear
    nombre_titular = models.CharField(max_length=100)
    fecha_expiracion = models.DateField()
    cvv = models.CharField(max_length=4)  # No modificable por seguridad

    def generar_alias(self) -> str:
        """Genera alias automático basado en los últimos 4 dígitos."""
        ultimos_digitos = self.numero_tarjeta[-4:] if self.numero_tarjeta else "****"
        return f"Tarjeta de Crédito - ****{ultimos_digitos}"

    def validar_fecha_vencimiento(self) -> None:
        """Valida la fecha de expiración de la tarjeta de crédito."""
        if self.fecha_expiracion and self.fecha_expiracion <= date.today():
            raise ValidationError({"fecha_expiracion": "La tarjeta no puede estar vencida."})

    def get_numero_enmascarado(self) -> str:
        """Retorna el número de tarjeta enmascarado para mostrar en UI"""
        numero = self.numero_tarjeta.replace(" ", "")
        return f"****-****-****-{numero[-4:]}"

    def validar_numero_tarjeta_repetido(self) -> None:
        """Valida que no exista otra tarjeta con el mismo número."""
        if self.numero_tarjeta:
            tarjeta_existente = TarjetaCredito.objects.filter(
                numero_tarjeta=self.numero_tarjeta,
            ).exclude(pk=self.pk)

            if tarjeta_existente.exists():
                raise ValidationError(
                    {
                        "numero_tarjeta": "El cliente ya tiene asociada una tarjeta con este número.",
                    }
                )

    def clean(self):
        """Validaciones del modelo antes de guardar."""
        super().clean()
        self.validar_fecha_vencimiento()
        self.validar_numero_tarjeta_repetido()

    def save(self, *args, **kwargs):
        """Guardar con validaciones."""
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Tarjeta de Crédito"
        verbose_name_plural = "Tarjetas de Crédito"
        unique_together = ["cliente", "numero_tarjeta"]


class CuentaBancaria(MedioDePago):
    """Modelo para cuentas bancarias."""

    numero_cuenta = models.CharField(max_length=30)
    banco = models.CharField(max_length=100)
    titular_cuenta = models.CharField(max_length=100)
    ruc_titular = models.CharField(max_length=12, blank=True)

    def get_numero_enmascarado(self) -> str:
        """Retorna el número de cuenta enmascarado"""
        return f"****{self.numero_cuenta[-4:]}" if len(self.numero_cuenta) > 4 else self.numero_cuenta

    def generar_alias(self) -> str:
        """Genera alias automático basado en banco y últimos dígitos."""
        ultimos_digitos = self.numero_cuenta[-4:] if len(self.numero_cuenta) > 4 else self.numero_cuenta
        return f"{self.banco} ****{ultimos_digitos}"

    def clean(self):
        """Validaciones del modelo antes de guardar."""
        super().clean()

        # Validar cuenta bancaria duplicada
        if self.numero_cuenta and self.banco:
            cuenta_existente = CuentaBancaria.objects.filter(
                numero_cuenta=self.numero_cuenta,
                banco=self.banco,
            ).exclude(pk=self.pk)

            if cuenta_existente.exists():
                raise ValidationError(
                    {
                        "numero_cuenta": f"Ya existe una cuenta con este número en {self.banco}",
                    }
                )

    def save(self, *args, **kwargs):
        """Guardar con validaciones."""
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Cuenta Bancaria"
        verbose_name_plural = "Cuentas Bancarias"
        unique_together = ["cliente", "numero_cuenta", "banco"]


class BilleteraElectronica(MedioDePago):
    """Modelo para billeteras electrónicas."""

    PROVEEDORES = [
        ("personal_pay", "Personal Pay"),
        ("mango", "Mango"),
        ("wally", "Wally"),
        ("eko", "Eko"),
        ("vaquita", "Vaquita"),
        ("otros", "Otros"),
    ]

    proveedor = models.CharField(max_length=50, choices=PROVEEDORES)
    identificador = models.CharField(max_length=100, help_text="Email, número de teléfono o ID de la billetera")
    numero_telefono = models.CharField(max_length=15)
    email_asociado = models.EmailField()

    def generar_alias(self) -> str:
        """Genera alias automático basado en proveedor e identificador."""
        proveedor_display = dict(self.PROVEEDORES).get(self.proveedor, self.proveedor)
        identificador_corto = self.identificador[:10] + "..." if len(self.identificador) > 10 else self.identificador
        return f"{proveedor_display} ({identificador_corto})"

    def clean(self):
        """Validaciones del modelo antes de guardar."""
        super().clean()

        # Validar billetera electrónica duplicada
        if self.proveedor and self.identificador:
            billetera_existente = BilleteraElectronica.objects.filter(
                proveedor=self.proveedor,
                identificador=self.identificador,
            ).exclude(pk=self.pk)

            if billetera_existente.exists():
                proveedor_display = dict(self.PROVEEDORES).get(self.proveedor, self.proveedor)
                raise ValidationError(
                    {
                        "identificador": f"Ya existe una billetera de {proveedor_display} con este identificador",
                    }
                )

    def save(self, *args, **kwargs):
        """Guardar con validaciones."""
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Billetera Electrónica"
        verbose_name_plural = "Billeteras Electrónicas"
        unique_together = ["cliente", "proveedor", "identificador"]
