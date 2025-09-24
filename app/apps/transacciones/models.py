from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from utils.validators import limpiar_ruc, validar_ruc_completo


class EntidadFinanciera(models.Model):
    """Modelo para entidades que gestionan medios financieros (bancos, emisores, proveedores).

    Attributes:
        nombre (CharField): Nombre de la entidad (ej. "Banco Nacional", "Visa", "Personal Pay").
        tipo (CharField): Tipo de entidad (banco, emisor_tarjeta, proveedor_billetera).
        comision_compra (DecimalField): Porcentaje de comisión para operaciones de compra.
        comision_venta (DecimalField): Porcentaje de comisión para operaciones de venta.
        activo (BooleanField): Indica si la entidad está activa para nuevos medios financieros.
        fecha_creacion (DateTimeField): Fecha de creación del registro.
        fecha_modificacion (DateTimeField): Fecha de última modificación.

    """

    TIPOS_ENTIDAD = [
        ("banco", "Banco"),
        ("emisor_tarjeta", "Emisor de Tarjeta"),
        ("proveedor_billetera", "Proveedor de Billetera"),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS_ENTIDAD)
    comision_compra = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    comision_venta = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        """Configuración para el modelo EntidadFinanciera.

        Attributes:
            verbose_name (str): Nombre singular legible para el modelo.
            verbose_name_plural (str): Nombre plural legible para el modelo.
            ordering (list): Orden predeterminado para los querysets.
            unique_together (list): Garantiza que la combinación de 'nombre' y 'tipo' sea única en los registros.

        """

        verbose_name = "Entidad Financiera"
        verbose_name_plural = "Entidades Financieras"
        ordering = ["tipo", "nombre"]
        unique_together = ["nombre", "tipo"]

    def __str__(self):
        tipo_display = dict(self.TIPOS_ENTIDAD).get(self.tipo, self.tipo)
        return f"{self.nombre} ({tipo_display})"

    def clean(self):
        """Validaciones del modelo antes de guardar.

        Validates:
            - El nombre de la entidad no debe estar vacío ni contener solo espacios.
            - El tipo de entidad debe ser uno de los valores permitidos.
            - Las comisiones de compra y venta no pueden ser negativas.

        Raises:
            ValidationError: Si alguna de las validaciones falla.

        """
        super().clean()

        # Validar que las comisiones no sean negativas
        if self.comision_compra < 0:
            raise ValidationError({"comision_compra": "La comisión de compra no puede ser negativa."})

        if self.comision_venta < 0:
            raise ValidationError({"comision_venta": "La comisión de venta no puede ser negativa."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class MedioFinanciero(models.Model):
    """Modelo base abstracto para todos los medios financieros (pago y cobro).

    Attributes:
        cliente (ForeignKey): Referencia al cliente propietario del medio financiero.
        alias (CharField): Alias personalizado para el medio financiero, opcional.
        habilitado_para_pago (BooleanField): Indica si puede usarse para realizar pagos.
        habilitado_para_cobro (BooleanField): Indica si puede usarse para recibir cobros.
        fecha_creacion (DateTimeField): Fecha y hora de creación del registro.
        fecha_modificacion (DateTimeField): Fecha y hora de la última modificación.

    """

    # TODO: Ver si es mejor usar SET_NULL o CASCADE para on_delete de cliente
    cliente = models.ForeignKey("usuarios.Cliente", on_delete=models.CASCADE, related_name="%(class)s_set")
    alias = models.CharField(max_length=50, blank=True)
    habilitado_para_pago = models.BooleanField(
        default=True,
        help_text="Indica si este medio financiero puede utilizarse para realizar pagos"
    )
    habilitado_para_cobro = models.BooleanField(
        default=False,
        help_text="Indica si este medio financiero puede utilizarse para recibir cobros"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        """Configuración para el modelo MedioFinanciero.

        Attributes:
            abstract (bool): Indica que este modelo no crea una tabla en la base de datos.
            ordering (list): Ordena los registros por fecha de creación descendente.

        """

        abstract = True
        ordering = ["-fecha_creacion"]

    def generar_alias(self) -> str:
        """Genera un alias automático para el medio financiero.

        Returns:
            str: Nombre de la clase del medio financiero.

        """
        return f"{self.__class__.__name__}"

    def __str__(self):
        """Representación en cadena del medio financiero.

        Returns:
            str: Cadena en formato "ClaseMedioFinanciero - Nombre del Cliente (alias)" o 
                "ClaseMedioFinanciero - Nombre del Cliente" si no tiene alias.

        """
        return f"{self.__class__.__name__} - {self.cliente.nombre}" + (f" ({self.alias})" if self.alias else "")


class TarjetaCredito(MedioFinanciero):
    """Modelo para tarjetas de crédito.

    Attributes:
        numero_tarjeta (CharField): Número de la tarjeta de crédito, hasta 16 dígitos.
        nombre_titular (CharField): Nombre completo del titular de la tarjeta, hasta 100 caracteres.
        fecha_expiracion (DateField): Fecha de expiración de la tarjeta.
        cvv (CharField): Código de verificación de la tarjeta, hasta 4 dígitos.
        entidad (ForeignKey): Referencia a la entidad emisora de la tarjeta.

    """

    numero_tarjeta = models.CharField(max_length=16)
    nombre_titular = models.CharField(max_length=100)
    fecha_expiracion = models.DateField()
    cvv = models.CharField(max_length=4)
    entidad = models.ForeignKey(
        EntidadFinanciera,
        on_delete=models.PROTECT,
        limit_choices_to={'tipo': 'emisor_tarjeta', 'activo': True},
        help_text="Entidad emisora de la tarjeta (Visa, Mastercard, etc.)",
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        # Las tarjetas de crédito solo se usan para pagos, no para cobros
        if not self.pk:
            self.habilitado_para_pago = True
            self.habilitado_para_cobro = False
        self.full_clean()
        super().save(*args, **kwargs)

    def generar_alias(self) -> str:
        """Genera alias automático basado en los últimos 4 dígitos y entidad.

        Returns:
            str: Alias en formato "EntidadEmisor - ****XXXX" donde XXXX son los últimos 4 dígitos.

        """
        ultimos_digitos = self.numero_tarjeta[-4:] if self.numero_tarjeta else "****"
        entidad_nombre = self.entidad.nombre if self.entidad else "Tarjeta"
        return f"{entidad_nombre} - ****{ultimos_digitos}"

    def get_comision_compra(self) -> Decimal:
        """Retorna la comisión de compra de la entidad emisora.

        Returns:
            Decimal: Porcentaje de comisión de compra, 0 si no hay entidad asociada.

        """
        return self.entidad.comision_compra if self.entidad else Decimal("0.00")

    def get_comision_venta(self) -> Decimal:
        """Retorna la comisión de venta de la entidad emisora.

        Returns:
            Decimal: Porcentaje de comisión de venta, 0 si no hay entidad asociada.

        """
        return self.entidad.comision_venta if self.entidad else Decimal("0.00")

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


class CuentaBancaria(MedioFinanciero):
    """Modelo para cuentas bancarias.

    Atributos:
        numero_cuenta (CharField): Número de cuenta bancaria, hasta 30 caracteres.
        entidad (ForeignKey): Referencia a la entidad bancaria.
        titular_cuenta (CharField): Nombre completo del titular de la cuenta, hasta 100 caracteres.
        documento_titular (CharField): Cédula de identidad o RUC del titular, hasta 12 caracteres.
    """

    numero_cuenta = models.CharField(max_length=30)
    entidad = models.ForeignKey(
        EntidadFinanciera,
        on_delete=models.PROTECT,
        limit_choices_to={'tipo': 'banco', 'activo': True},
        help_text="Entidad bancaria",
        null=True,
        blank=True
    )
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
        banco_nombre = self.entidad.nombre if self.entidad else "Banco"
        return f"{banco_nombre} ****{ultimos_digitos}"

    def get_comision_compra(self) -> Decimal:
        """Retorna la comisión de compra de la entidad bancaria.

        Returns:
            Decimal: Porcentaje de comisión de compra, 0 si no hay entidad asociada.

        """
        return self.entidad.comision_compra if self.entidad else Decimal("0.00")

    def get_comision_venta(self) -> Decimal:
        """Retorna la comisión de venta de la entidad bancaria.

        Returns:
            Decimal: Porcentaje de comisión de venta, 0 si no hay entidad asociada.

        """
        return self.entidad.comision_venta if self.entidad else Decimal("0.00")

    def clean(self):
        """Validaciones del modelo antes de guardar.

        Validates:
            - Formato y dígito verificador del RUC si el documento no es solo dígitos
            - Número de cuenta único por cliente y entidad bancaria

        Raises:
            ValidationError: Si el RUC es inválido o si ya existe una cuenta con el mismo número 
                           para el cliente en la entidad bancaria especificada.

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
        if self.numero_cuenta and self.entidad and self.cliente:
            cuenta_existente = CuentaBancaria.objects.filter(
                cliente=self.cliente,
                numero_cuenta=self.numero_cuenta,
                entidad=self.entidad,
            ).exclude(pk=self.pk)

            if cuenta_existente.exists():
                raise ValidationError(
                    {
                        "numero_cuenta": f"Ya tienes una cuenta con este número en {self.entidad.nombre}",
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
            unique_together (list): Un cliente no puede tener dos cuentas con el mismo número y entidad.

        """

        verbose_name = "Cuenta Bancaria"
        verbose_name_plural = "Cuentas Bancarias"
        unique_together = ["cliente", "numero_cuenta", "entidad"]


class BilleteraElectronica(MedioFinanciero):
    """Modelo para billeteras electrónicas.

    Attributes:
        entidad (ForeignKey): Referencia a la entidad proveedora de la billetera.
        identificador (CharField): Email, número de teléfono o ID único de la billetera.
        numero_telefono (CharField): Número de teléfono asociado a la billetera.
        email_asociado (EmailField): Email asociado a la billetera electrónica.

    """

    entidad = models.ForeignKey(
        EntidadFinanciera,
        on_delete=models.PROTECT,
        limit_choices_to={'tipo': 'proveedor_billetera', 'activo': True},
        help_text="Proveedor de la billetera electrónica",
        null=True,
        blank=True
    )
    identificador = models.CharField(max_length=100, help_text="Email, número de teléfono o ID de la billetera")
    numero_telefono = models.CharField(max_length=15)
    email_asociado = models.EmailField()

    def generar_alias(self) -> str:
        """Genera alias automático basado en proveedor e identificador.

        Returns:
            str: Alias en formato "Proveedor (identificador)", el identificador se trunca 
                a 10 caracteres si es muy largo.

        """
        proveedor_nombre = self.entidad.nombre if self.entidad else "Billetera"
        identificador_corto = self.identificador[:10] + "..." if len(self.identificador) > 10 else self.identificador
        return f"{proveedor_nombre} ({identificador_corto})"

    def get_comision_compra(self) -> Decimal:
        """Retorna la comisión de compra del proveedor de billetera.

        Returns:
            Decimal: Porcentaje de comisión de compra, 0 si no hay entidad asociada.

        """
        return self.entidad.comision_compra if self.entidad else Decimal("0.00")

    def get_comision_venta(self) -> Decimal:
        """Retorna la comisión de venta del proveedor de billetera.

        Returns:
            Decimal: Porcentaje de comisión de venta, 0 si no hay entidad asociada.

        """
        return self.entidad.comision_venta if self.entidad else Decimal("0.00")

    def clean(self):
        """Validaciones del modelo antes de guardar.

        Validates:
            - Combinación única de cliente, entidad e identificador

        Raises:
            ValidationError: Si ya existe una billetera con la misma entidad e identificador 
                           para el cliente especificado.

        """
        super().clean()

        # Validar billetera electrónica duplicada para el mismo cliente
        if self.entidad and self.identificador and self.cliente:
            billetera_existente = BilleteraElectronica.objects.filter(
                cliente=self.cliente,
                entidad=self.entidad,
                identificador=self.identificador,
            ).exclude(pk=self.pk)

            if billetera_existente.exists():
                raise ValidationError(
                    {
                        "identificador": f"Ya tienes una billetera de {self.entidad.nombre} con este identificador",
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
            unique_together (list): Un cliente no puede tener dos billeteras con la misma entidad e identificador.

        """

        verbose_name = "Billetera Electrónica"
        verbose_name_plural = "Billeteras Electrónicas"
        unique_together = ["cliente", "entidad", "identificador"]
