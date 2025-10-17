"""Modelos para la aplicación de transacciones.

Este módulo define modelos de Django para transacciones financieras, incluyendo entidades
(bancos, emisores de tarjetas, proveedores de billeteras), métodos de pago (tarjetas de crédito,
cuentas bancarias, billeteras electrónicas) y límites de transacciones.
"""

import uuid
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
        default=True, help_text="Indica si este medio financiero puede utilizarse para realizar pagos"
    )
    habilitado_para_cobro = models.BooleanField(
        default=False, help_text="Indica si este medio financiero puede utilizarse para recibir cobros"
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
        limit_choices_to={"tipo": "emisor_tarjeta", "activo": True},
        help_text="Entidad emisora de la tarjeta (Visa, Mastercard, etc.)",
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        """Guarda la instancia de TarjetaCredito, configurando habilitaciones por defecto para nuevas instancias.

        Para nuevas tarjetas, establece habilitado_para_pago en True y habilitado_para_cobro en False.
        Realiza validaciones completas antes de guardar.

        Args:
            *args: Argumentos posicionales para el método save de Django.
            **kwargs: Argumentos de palabra clave para el método save de Django.

        """
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
        limit_choices_to={"tipo": "banco", "activo": True},
        help_text="Entidad bancaria",
        null=True,
        blank=True,
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

        # Validar RUC si se proporciona
        if self.documento_titular and not self.documento_titular.isdigit():
            ruc_limpio = limpiar_ruc(self.documento_titular)

            if not validar_ruc_completo(ruc_limpio):
                raise ValidationError({"documento_titular": "El dígito verificador del RUC no es válido."})

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
        limit_choices_to={"tipo": "proveedor_billetera", "activo": True},
        help_text="Proveedor de la billetera electrónica",
        null=True,
        blank=True,
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


class Transaccion(models.Model):
    """Modelo para representar transacciones de cambio de divisas.

    Attributes:
        idTransaccion (UUIDField): Identificador único de la transacción.
        cliente (ForeignKey): Referencia al cliente que realiza la transacción.
        usuario (ForeignKey): Referencia al usuario que procesa la transacción.
        tipoOperacion (CharField): Tipo de operación (compra, venta).
        estado (CharField): Estado actual de la transacción.
        fechaCreacion (DateTimeField): Fecha y hora de creación de la transacción.
        fechaPago (DateTimeField): Fecha y hora del pago (opcional).
        fechaActualizacion (DateTimeField): Fecha y hora de última actualización.
        divisaOrigen (ForeignKey): Divisa de origen de la transacción.
        divisaDestino (ForeignKey): Divisa de destino de la transacción.
        tasaAplicada (DecimalField): Tasa de cambio aplicada en la transacción.
        montoOrigen (DecimalField): Monto en la divisa de origen.
        montoDestino (DecimalField): Monto en la divisa de destino.

    """

    TIPOS_OPERACION = [
        ("compra", "Compra"),
        ("venta", "Venta"),
    ]

    ESTADOS_TRANSACCION = [
        ("pendiente", "Pendiente"),
        ("completada", "Completada"),
        ("cancelada", "Cancelada"),
        ("cancelada_cotizacion", "Cancelada por cambio de cotización"),
        ("vencida", "Vencida por cambio de cotización"),
        ("anulada", "Anulada"),
    ]

    id_transaccion = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, help_text="Identificador único de la transacción"
    )
    cliente = models.ForeignKey(
        "usuarios.Cliente",
        on_delete=models.CASCADE,
        related_name="transacciones",
        help_text="Cliente que realiza la transacción",
    )
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="transacciones_procesadas",
        help_text="Usuario que procesa la transacción",
    )
    tipo_operacion = models.CharField(
        max_length=50, choices=TIPOS_OPERACION, help_text="Tipo de operación (compra o venta)"
    )
    estado = models.CharField(
        max_length=20, choices=ESTADOS_TRANSACCION, default="pendiente", help_text="Estado actual de la transacción"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, help_text="Fecha y hora de creación de la transacción")
    fecha_pago = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora del pago (opcional)")
    fecha_actualizacion = models.DateTimeField(auto_now=True, help_text="Fecha y hora de última actualización")
    divisa_origen = models.ForeignKey(
        "operaciones.Divisa",
        on_delete=models.CASCADE,
        related_name="transacciones_origen",
        help_text="Divisa de origen de la transacción",
    )
    divisa_destino = models.ForeignKey(
        "operaciones.Divisa",
        on_delete=models.CASCADE,
        related_name="transacciones_destino",
        help_text="Divisa de destino de la transacción",
    )
    tasa_aplicada = models.DecimalField(
        max_digits=15, decimal_places=8, help_text="Tasa de cambio aplicada en la transacción"
    )
    monto_origen = models.DecimalField(max_digits=20, decimal_places=8, help_text="Monto en la divisa de origen")
    monto_destino = models.DecimalField(max_digits=20, decimal_places=8, help_text="Monto en la divisa de destino")
    medio_pago = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Identificador del medio de pago utilizado (efectivo, tarjeta_X, cuenta_X, billetera_X)",
    )
    medio_cobro = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Identificador del medio de cobro utilizado (efectivo, tarjeta_X, cuenta_X, billetera_X)",
    )
    tasa_original = models.DecimalField(
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Tasa de cambio original al momento de crear la transacción",
    )
    tasa_actual = models.DecimalField(
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Tasa de cambio actual (se actualiza al verificar cotización)",
    )
    cambio_cotizacion_notificado = models.BooleanField(
        default=False, help_text="Indica si se notificó al cliente sobre el cambio de cotización"
    )
    fecha_vencimiento_cotizacion = models.DateTimeField(
        null=True, blank=True, help_text="Fecha límite para usar la cotización original"
    )
    motivo_cancelacion = models.TextField(
        blank=True, null=True, help_text="Motivo detallado de la cancelación de la transacción"
    )
    stripe_payment = models.ForeignKey(
        "StripePayment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transacciones",
        help_text="Pago con Stripe asociado a esta transacción",
    )

    class Meta:
        """Configuración para el modelo Transaccion.

        Attributes:
            verbose_name (str): Nombre singular legible para el modelo.
            verbose_name_plural (str): Nombre plural legible para el modelo.
            ordering (list): Orden predeterminado por fecha de creación descendente.

        """

        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        """Representación en cadena de la transacción.

        Returns:
            str: Cadena descriptiva de la transacción.

        """
        return f"Transacción {self.tipo_operacion} - {self.cliente.nombre} - {self.estado}"

    def clean(self):
        """Validaciones del modelo antes de guardar.

        Validates:
            - Los montos sean positivos
            - La tasa aplicada sea positiva
            - Las divisas de origen y destino sean diferentes

        Raises:
            ValidationError: Si alguna de las validaciones falla.

        """
        super().clean()

        # Validar que los montos sean positivos
        if self.monto_origen is not None and self.monto_origen <= 0:
            raise ValidationError({"monto_origen": "El monto de origen debe ser positivo."})

        if self.monto_destino is not None and self.monto_destino <= 0:
            raise ValidationError({"monto_destino": "El monto de destino debe ser positivo."})

        # Validar que la tasa aplicada sea positiva
        if self.tasa_aplicada is not None and self.tasa_aplicada <= 0:
            raise ValidationError({"tasa_aplicada": "La tasa aplicada debe ser positiva."})

        # Validar que las divisas sean diferentes
        if self.divisa_origen and self.divisa_destino and self.divisa_origen == self.divisa_destino:
            raise ValidationError("Las divisas de origen y destino deben ser diferentes.")

    def verificar_cambio_cotizacion(self):
        """Verifica si la cotización actual difiere de la original.

        Returns:
            dict: Diccionario con información del cambio de cotización:
                - cambio_detectado (bool): True si hay cambio significativo
                - tasa_original (Decimal): Tasa original de la transacción
                - tasa_actual (Decimal): Tasa actual del mercado (incluyendo comisiones)
                - porcentaje_cambio (Decimal): Porcentaje de cambio
                - umbral_superado (bool): True si supera el umbral de notificación

        """
        from decimal import Decimal

        from apps.operaciones.models import TasaCambio

        # Obtener la tasa actual del mercado
        try:
            # Determinar la divisa extranjera (no PYG)
            # Las tasas de cambio en la BD siempre son con PYG como origen
            if self.divisa_origen.codigo == "PYG":
                divisa_extranjera = self.divisa_destino
            else:
                divisa_extranjera = self.divisa_origen

            # Buscar tasa de cambio activa (siempre con PYG como origen en la BD)
            tasa_cambio_actual = TasaCambio.objects.filter(
                divisa_origen__codigo="PYG", divisa_destino=divisa_extranjera, activo=True
            ).first()

            if not tasa_cambio_actual:
                return {
                    "cambio_detectado": False,
                    "error": f"No se encontró tasa de cambio activa para {divisa_extranjera.codigo}",
                }

            # Calcular la tasa efectiva incluyendo comisiones según el tipo de operación
            precio_base = tasa_cambio_actual.precio_base

            # Obtener descuento del cliente si existe
            porcentaje_descuento = Decimal("0.0")
            if self.cliente and self.cliente.tipo_cliente:
                porcentaje_descuento = self.cliente.tipo_cliente.descuento_sobre_comision

            if self.tipo_operacion == "compra":
                # Para compra: precio_base + comisión_compra (menos descuento)
                comision_compra = tasa_cambio_actual.comision_compra
                comision_efectiva = comision_compra - (comision_compra * porcentaje_descuento / Decimal("100"))
                tasa_actual = precio_base + comision_efectiva
            else:  # venta
                # Para venta: precio_base - comisión_venta (menos descuento)
                comision_venta = tasa_cambio_actual.comision_venta
                comision_efectiva = comision_venta - (comision_venta * porcentaje_descuento / Decimal("100"))
                tasa_actual = precio_base - comision_efectiva

            tasa_original = self.tasa_original or self.tasa_aplicada

            # Actualizar la tasa actual en el modelo
            self.tasa_actual = tasa_actual

            # Calcular el porcentaje de cambio y diferencia absoluta
            if tasa_original and tasa_actual:
                # Redondear ambas tasas a 3 decimales para comparación precisa
                tasa_original_redondeada = tasa_original.quantize(Decimal("0.001"))
                tasa_actual_redondeada = tasa_actual.quantize(Decimal("0.001"))

                cambio_absoluto = abs(tasa_actual_redondeada - tasa_original_redondeada)
                if tasa_original_redondeada != 0:
                    porcentaje_cambio = (cambio_absoluto / tasa_original_redondeada) * 100
                else:
                    porcentaje_cambio = Decimal("0")

                # Detectar cambio si:
                # 1. Hay diferencia en los 3 decimales (cualquier cambio detectable)
                # 2. O si supera el umbral del 1% (para cambios muy pequeños en tasas altas)
                umbral_absoluto = Decimal("0.001")  # Diferencia mínima de 0.001
                umbral_porcentual = Decimal("1.0")  # 1% de cambio porcentual

                cambio_significativo = (cambio_absoluto >= umbral_absoluto) or (porcentaje_cambio >= umbral_porcentual)

                return {
                    "cambio_detectado": cambio_significativo,
                    "tasa_original": tasa_original_redondeada,
                    "tasa_actual": tasa_actual_redondeada,
                    "porcentaje_cambio": porcentaje_cambio,
                    "cambio_absoluto": cambio_absoluto,
                    "umbral_superado": cambio_significativo,
                }

            return {"cambio_detectado": False}

        except Exception as e:
            return {"cambio_detectado": False, "error": str(e)}

    def cancelar_por_cotizacion(self, motivo=None):
        """Cancela la transacción por cambio de cotización.

        Args:
            motivo (str, optional): Motivo específico de la cancelación

        """
        self.estado = "cancelada_cotizacion"
        self.motivo_cancelacion = motivo or "Transacción cancelada por cambio significativo en la cotización"
        self.save()

    def marcar_como_vencida(self):
        """Marca la transacción como vencida por no aceptar nueva cotización."""
        self.estado = "vencida"
        self.motivo_cancelacion = "Transacción vencida - cotización ya no vigente"
        self.save()

    def aceptar_nueva_cotizacion(self):
        """Acepta la nueva cotización y actualiza la transacción.

        Nota: Los montos originales se mantienen ya que fueron calculados
        con todos los factores (comisiones de medios, descuentos, etc.).
        Solo se actualiza la tasa aplicada para reflejar el cambio aceptado.
        La nueva tasa también se establece como tasa original para futuras comparaciones.
        """
        if self.tasa_actual:
            self.tasa_aplicada = self.tasa_actual
            self.tasa_original = self.tasa_actual  # Nueva tasa como base para futuras comparaciones
            self.cambio_cotizacion_notificado = False  # Reset notification flag
            # Los montos se mantienen como fueron calculados originalmente
            # ya que incluyen comisiones de medios de pago/cobro y otros factores
            self.save()

    def save(self, *args, **kwargs):
        """Guarda la instancia realizando validaciones completas.

        Args:
            *args: Argumentos posicionales para el método save de Django.
            **kwargs: Argumentos de palabra clave para el método save de Django.

        """
        self.full_clean()
        super().save(*args, **kwargs)


class LimiteTransacciones(models.Model):
    """Representa los límites de transacciones diarias y mensuales del sistema.

    Este modelo almacena los límites de transacciones en guaraníes que se aplican
    a todas las operaciones del sistema. Cada modificación genera un nuevo registro
    para mantener un historial de auditoría de los cambios.

    Argumentos:
        limite_diario (DecimalField): Límite máximo de transacciones por día en guaraníes.
        limite_mensual (DecimalField): Límite máximo de transacciones por mes en guaraníes.
        fecha_modificacion (DateTimeField): Fecha y hora de cuando se realizó la configuración.

    """

    limite_diario = models.DecimalField(
        max_digits=15, decimal_places=0, help_text="Límite máximo de transacciones por día en guaraníes"
    )
    limite_mensual = models.DecimalField(
        max_digits=15, decimal_places=0, help_text="Límite máximo de transacciones por mes en guaraníes"
    )
    fecha_modificacion = models.DateTimeField(
        auto_now_add=True, help_text="Fecha y hora de cuando se estableció este límite"
    )

    class Meta:
        """Meta información para el modelo LimiteTransacciones."""

        db_table = "limite_transacciones"
        verbose_name = "Límite de Transacciones"
        verbose_name_plural = "Límites de Transacciones"
        ordering = ["-fecha_modificacion"]

    def __str__(self):
        """Representación en string del objeto."""
        return f"Límites: Diario ₲{self.limite_diario:,.0f} - Mensual ₲{self.limite_mensual:,.0f}"

    @classmethod
    def get_limite_actual(cls):
        """Retorna la configuración de límites más reciente."""
        return cls.objects.first()

    def clean(self):
        """Valida que los límites sean positivos y que el límite mensual sea mayor al diario."""
        if self.limite_diario <= 0:
            raise ValidationError("El límite diario debe ser mayor a 0")
        if self.limite_mensual <= 0:
            raise ValidationError("El límite mensual debe ser mayor a 0")
        if self.limite_mensual < self.limite_diario:
            raise ValidationError("El límite mensual debe ser mayor o igual al límite diario")


class StripePayment(models.Model):
    """Modelo para auditar pagos con Stripe (tarjetas extranjeras).

    Este modelo mantiene un registro detallado de todas las operaciones
    realizadas con Stripe para fines de auditoría y reconciliación.
    """

    STRIPE_STATUS_CHOICES = [
        ("requires_payment_method", "Requiere método de pago"),
        ("requires_confirmation", "Requiere confirmación"),
        ("requires_action", "Requiere acción"),
        ("processing", "Procesando"),
        ("requires_capture", "Requiere captura"),
        ("canceled", "Cancelado"),
        ("succeeded", "Exitoso"),
        ("failed", "Fallido"),
    ]

    # Relaciones
    cliente = models.ForeignKey(
        "usuarios.Cliente",
        on_delete=models.PROTECT,
        related_name="stripe_payments",
        help_text="Cliente que realiza el pago",
    )

    # Datos de Stripe
    stripe_payment_intent_id = models.CharField(max_length=100, unique=True, help_text="ID del PaymentIntent de Stripe")
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID del customer en Stripe")
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Monto del pago en la moneda especificada")
    currency = models.CharField(max_length=3, default="USD", help_text="Moneda del pago (USD, EUR, etc.)")
    status = models.CharField(
        max_length=30,
        choices=STRIPE_STATUS_CHOICES,
        default="requires_payment_method",
        help_text="Estado del pago en Stripe",
    )
    payment_method_id = models.CharField(
        max_length=100, blank=True, null=True, help_text="ID del método de pago en Stripe"
    )

    # Datos de auditoría detallados
    card_brand = models.CharField(
        max_length=20, blank=True, null=True, help_text="Marca de la tarjeta (visa, mastercard, etc.)"
    )
    card_last4 = models.CharField(max_length=4, blank=True, null=True, help_text="Últimos 4 dígitos de la tarjeta")
    card_country = models.CharField(
        max_length=2, blank=True, null=True, help_text="País emisor de la tarjeta (código ISO)"
    )

    # Auditoría completa
    fecha_creacion = models.DateTimeField(auto_now_add=True, help_text="Fecha de creación del pago")
    fecha_actualizacion = models.DateTimeField(auto_now=True, help_text="Fecha de última actualización")
    metadata = models.JSONField(default=dict, blank=True, help_text="Metadatos adicionales del pago")

    # Logs de operaciones para auditoría
    log_operaciones = models.TextField(blank=True, null=True, help_text="Log JSON de todas las operaciones realizadas")

    class Meta:
        verbose_name = "Pago Stripe"
        verbose_name_plural = "Pagos Stripe"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Stripe {self.amount} {self.currency} - {self.get_status_display()}"

    def is_successful(self) -> bool:
        """Verifica si el pago fue exitoso."""
        return self.status == "succeeded"

    def get_card_display(self) -> str:
        """Retorna información legible de la tarjeta."""
        if self.card_brand and self.card_last4:
            return f"{self.card_brand.title()} *{self.card_last4}"
        return "Tarjeta Internacional"


class TarjetaExtranjera(models.Model):
    """Modelo para tarjetas extranjeras guardadas vía Stripe.

    Permite a los clientes guardar sus tarjetas internacionales
    para uso futuro en transacciones.
    """

    # Relaciones
    cliente = models.ForeignKey(
        "usuarios.Cliente",
        on_delete=models.CASCADE,
        related_name="tarjetas_extranjeras",
        help_text="Cliente propietario de la tarjeta",
    )

    # Identificadores de Stripe
    stripe_payment_method_id = models.CharField(max_length=100, unique=True, help_text="ID del PaymentMethod en Stripe")
    stripe_customer_id = models.CharField(max_length=100, help_text="ID del Customer en Stripe")

    # Información visible para el cliente
    brand = models.CharField(max_length=20, help_text="Marca de la tarjeta (visa, mastercard, etc.)")
    last4 = models.CharField(max_length=4, help_text="Últimos 4 dígitos de la tarjeta")
    alias = models.CharField(max_length=50, help_text="Alias personalizado para la tarjeta")

    # Control
    activo = models.BooleanField(default=True, help_text="Indica si la tarjeta está activa para uso")
    fecha_creacion = models.DateTimeField(auto_now_add=True, help_text="Fecha de registro de la tarjeta")

    class Meta:
        verbose_name = "Tarjeta Extranjera"
        verbose_name_plural = "Tarjetas Extranjeras"
        ordering = ["-fecha_creacion"]
        unique_together = ["cliente", "stripe_payment_method_id"]

    def __str__(self):
        return f"{self.brand.title()} *{self.last4} - {self.cliente.nombre}"

    def get_display_name(self) -> str:
        """Retorna el nombre para mostrar en la UI."""
        return f"💳 {self.brand.title()} *{self.last4} ({self.alias})"
