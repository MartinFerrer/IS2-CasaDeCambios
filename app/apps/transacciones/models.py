from datetime import date

from django.core.exceptions import ValidationError
from django.db import models

from utils.validators import limpiar_ruc, validar_ruc_completo


class MedioDePago(models.Model):
    """Modelo base abstracto para todos los medios de pago.

    Attributes:
        cliente (ForeignKey): Referencia al cliente propietario del medio de pago.
        alias (CharField): Alias personalizado para el medio de pago, opcional.
        fecha_creacion (DateTimeField): Fecha y hora de creación del registro.
        fecha_modificacion (DateTimeField): Fecha y hora de la última modificación.

    """

    cliente = models.ForeignKey("usuarios.Cliente", on_delete=models.CASCADE, related_name="%(class)s_set")
    alias = models.CharField(max_length=50, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        """Configuración para el modelo MedioDePago.

        Attributes:
            abstract (bool): Indica que este modelo no crea una tabla en la base de datos.
            ordering (list): Ordena los registros por fecha de creación descendente.

        """

        abstract = True
        ordering = ["-fecha_creacion"]

    def generar_alias(self) -> str:
        """Genera un alias automático para el medio de pago.

        Returns:
            str: Nombre de la clase del medio de pago.

        """
        return f"{self.__class__.__name__}"

    def __str__(self):
        """Representación en cadena del medio de pago.

        Returns:
            str: Cadena en formato "ClaseMedioPago - Nombre del Cliente (alias)" o 
                "ClaseMedioPago - Nombre del Cliente" si no tiene alias.

        """
        return f"{self.__class__.__name__} - {self.cliente.nombre}" + (f" ({self.alias})" if self.alias else "")


class TarjetaCredito(MedioDePago):
    """Modelo para tarjetas de crédito.

    Attributes:
        numero_tarjeta (CharField): Número de la tarjeta de crédito, hasta 16 dígitos.
        nombre_titular (CharField): Nombre completo del titular de la tarjeta, hasta 100 caracteres.
        fecha_expiracion (DateField): Fecha de expiración de la tarjeta.
        cvv (CharField): Código de verificación de la tarjeta, hasta 4 dígitos.

    """

    numero_tarjeta = models.CharField(max_length=16)
    nombre_titular = models.CharField(max_length=100)
    fecha_expiracion = models.DateField()
    cvv = models.CharField(max_length=4)

    def generar_alias(self) -> str:
        """Genera alias automático basado en los últimos 4 dígitos.

        Returns:
            str: Alias en formato "Tarjeta de Crédito - ****XXXX" donde XXXX son los últimos 4 dígitos.

        """
        ultimos_digitos = self.numero_tarjeta[-4:] if self.numero_tarjeta else "****"
        return f"Tarjeta de Crédito - ****{ultimos_digitos}"

    def validar_fecha_vencimiento(self) -> None:
        """Valida la fecha de expiración de la tarjeta de crédito.

        Raises:
            ValidationError: Si la tarjeta está vencida (fecha <= hoy).

        """
        if self.fecha_expiracion and self.fecha_expiracion <= date.today():
            raise ValidationError({"fecha_expiracion": "La tarjeta no puede estar vencida."})

    def get_numero_enmascarado(self) -> str:
        """Retorna el número de tarjeta enmascarado para mostrar en UI.

        Returns:
            str: Número enmascarado en formato ****-****-****-XXXX donde XXXX son los últimos 4 dígitos.

        """
        numero = self.numero_tarjeta.replace(" ", "")
        return f"****-****-****-{numero[-4:]}"

    def clean(self):
        """Validaciones del modelo antes de guardar.

        Validates:
            - La tarjeta no puede estar vencida
            - Número de tarjeta único por cliente

        Raises:
            ValidationError: Si la validación falla.

        """
        super().clean()
        self.validar_fecha_vencimiento()

        # Valida que no exista otra tarjeta con el mismo número para el mismo cliente.
        if self.numero_tarjeta and self.cliente:
            tarjeta_existente = TarjetaCredito.objects.filter(
                cliente=self.cliente,
                numero_tarjeta=self.numero_tarjeta,
            ).exclude(pk=self.pk)

            if tarjeta_existente.exists():
                raise ValidationError(
                    {
                        "numero_tarjeta": "Ya tienes asociada una tarjeta con este número.",
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        """Configuración para el modelo TarjetaCredito.

        Attributes:
            verbose_name (str): Nombre singular legible para el modelo.
            verbose_name_plural (str): Nombre plural legible para el modelo.
            unique_together (list): Un cliente no puede tener dos tarjetas con el mismo número.

        """

        verbose_name = "Tarjeta de Crédito"
        verbose_name_plural = "Tarjetas de Crédito"
        unique_together = ["cliente", "numero_tarjeta"]


class CuentaBancaria(MedioDePago):
    """Modelo para cuentas bancarias.

    Atributos:
        numero_cuenta (CharField): Número de cuenta bancaria, hasta 30 caracteres.
        banco (CharField): Nombre del banco asociado, hasta 100 caracteres.
        titular_cuenta (CharField): Nombre completo del titular de la cuenta, hasta 100 caracteres.
        documento_titular (CharField): Cédula de identidad o RUC del titular, hasta 12 caracteres.
    """

    numero_cuenta = models.CharField(max_length=30)
    # TODO [SCRUM-112]: dropdown de valores permitidos para banco
    banco = models.CharField(max_length=100)
    titular_cuenta = models.CharField(max_length=100)
    documento_titular = models.CharField(max_length=12)

    def get_numero_enmascarado(self) -> str:
        """Retorna el número de cuenta enmascarado, mostrando solo los últimos 4 dígitos.

        Returns:
            str: Número de cuenta enmascarado en formato ****XXXX donde XXXX son los últimos 4 dígitos.

        """
        return f"****{self.numero_cuenta[-4:]}" if len(self.numero_cuenta) > 4 else self.numero_cuenta

    def generar_alias(self) -> str:
        """Genera alias automático basado en banco y últimos dígitos.

        Returns:
            str: Alias en formato "Banco ****XXXX" donde XXXX son los últimos 4 dígitos del número de cuenta.

        """
        ultimos_digitos = self.numero_cuenta[-4:] if len(self.numero_cuenta) > 4 else self.numero_cuenta
        return f"{self.banco} ****{ultimos_digitos}"

    def clean(self):
        """Validaciones del modelo antes de guardar.

        Validates:
            - Formato y dígito verificador del RUC si el documento no es solo dígitos
            - Número de cuenta único por cliente y banco

        Raises:
            ValidationError: Si el RUC es inválido o si ya existe una cuenta con el mismo número 
                           para el cliente en el banco especificado.

        """
        super().clean()

        # Validar RUC si se proporciona un RUC
        if self.documento_titular and not self.documento_titular.isdigit():
            ruc_limpio = limpiar_ruc(self.documento_titular)

            if not validar_ruc_completo(ruc_limpio):
                raise ValidationError({
                    'documento_titular': 'El dígito verificador del RUC no es válido.'
                })

            self.documento_titular = ruc_limpio[:-1] + "-" + ruc_limpio[-1]

        # Validar cuenta bancaria duplicada para el mismo cliente
        if self.numero_cuenta and self.banco and self.cliente:
            cuenta_existente = CuentaBancaria.objects.filter(
                cliente=self.cliente,
                numero_cuenta=self.numero_cuenta,
                banco=self.banco,
            ).exclude(pk=self.pk)

            if cuenta_existente.exists():
                raise ValidationError(
                    {
                        "numero_cuenta": f"Ya tienes una cuenta con este número en {self.banco}",
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        """Configuración para el modelo CuentaBancaria.
        
        Attributes:
            verbose_name (str): Nombre singular legible para el modelo.
            verbose_name_plural (str): Nombre plural legible para el modelo.
            unique_together (list): Un cliente no puede tener dos cuentas con el mismo número y banco.

        """

        verbose_name = "Cuenta Bancaria"
        verbose_name_plural = "Cuentas Bancarias"
        unique_together = ["cliente", "numero_cuenta", "banco"]


class BilleteraElectronica(MedioDePago):
    """Modelo para billeteras electrónicas.

    Attributes:
        proveedor (CharField): Proveedor de la billetera electrónica, con opciones predefinidas.
        identificador (CharField): Email, número de teléfono o ID único de la billetera.
        numero_telefono (CharField): Número de teléfono asociado a la billetera.
        email_asociado (EmailField): Email asociado a la billetera electrónica.

    """

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
        """Genera alias automático basado en proveedor e identificador.

        Returns:
            str: Alias en formato "Proveedor (identificador)", el identificador se trunca 
                a 10 caracteres si es muy largo.

        """
        proveedor_display = dict(self.PROVEEDORES).get(self.proveedor, self.proveedor)
        identificador_corto = self.identificador[:10] + "..." if len(self.identificador) > 10 else self.identificador
        return f"{proveedor_display} ({identificador_corto})"

    def clean(self):
        """Validaciones del modelo antes de guardar.

        Validates:
            - Combinación única de cliente, proveedor e identificador

        Raises:
            ValidationError: Si ya existe una billetera con el mismo proveedor e identificador 
                           para el cliente especificado.

        """
        super().clean()

        # Validar billetera electrónica duplicada para el mismo cliente
        if self.proveedor and self.identificador and self.cliente:
            billetera_existente = BilleteraElectronica.objects.filter(
                cliente=self.cliente,
                proveedor=self.proveedor,
                identificador=self.identificador,
            ).exclude(pk=self.pk)

            if billetera_existente.exists():
                proveedor_display = dict(self.PROVEEDORES).get(self.proveedor, self.proveedor)
                raise ValidationError(
                    {
                        "identificador": f"Ya tienes una billetera de {proveedor_display} con este identificador",
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        """Configuración  para el modelo BilleteraElectronica.
        
        Attributes:
            verbose_name (str): Nombre singular legible para el modelo.
            verbose_name_plural (str): Nombre plural legible para el modelo.
            unique_together (list): Un cliente no puede tener dos billeteras con el mismo proveedor e identificador.

        """

        verbose_name = "Billetera Electrónica"
        verbose_name_plural = "Billeteras Electrónicas"
        unique_together = ["cliente", "proveedor", "identificador"]
