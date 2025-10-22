"""Modelos para gestionar divisas y tasas de cambio en el sistema de Casa de Cambios.

Incluye:
- Divisa: modelo para las monedas soportadas.
- TasaCambio: modelo para las tasas de cambio entre divisas.
"""

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Divisa(models.Model):
    """Representa una Divisa utilizada en el sistema de cambio.

    Este modelo almacena información básica sobre cada Divisa, incluyendo su
    código ISO, nombre y símbolo.

    Argumentos:
        codigo (CharField): El código ISO 4217 de la Divisa (e.g 'USD', 'EUR').
        nombre (CharField): El nombre de la Divisa (e.g., 'Dólar').
        simbolo (CharField): El símbolo de la Divisa (ej. ₲, $, €).

    """

    codigo = models.CharField(primary_key=True, max_length=3, unique=True, help_text="(ej. PYG, USD, EUR).")
    nombre = models.CharField(max_length=50, help_text="(ej. Guaraní, Dólar Estadounidense).")
    simbolo = models.CharField(max_length=5, blank=True, default="", help_text="(ej. ₲, $, €).")
    estado = models.CharField(
        max_length=10,
        choices=[("activa", "Activa"), ("inactiva", "Inactiva")],
        default="Activa",
    )

    class Meta:
        """Meta información para el modelo Divisa."""

        db_table = "divisa"
        verbose_name = "Divisa"
        verbose_name_plural = "Divisas"

    def __str__(self):
        """Representación en string del objeto, útil para su visualización."""
        return f"{self.codigo}"


class TasaCambio(models.Model):
    """Representa la Tasa de Cambio de una divisa a otra.

    Este modelo almacena el valor de la tasa de cambio entre dos divisas, junto
    con las comisiones asociadas para la compra y venta.

    Argumentos:
        id_tasa_cambio (UUIDField): Identificador único para la tasa de cambio.
        divisa_origen (ForeignKey): La divisa desde la que se realiza la conversión.
        divisa_destino (ForeignKey): La divisa a la que se realiza la conversión.
        precio_base (DecimalField): El precio base de la divisa.
        comision_compra (DecimalField): Comisión aplicada al comprar la divisa destino.
        comision_venta (DecimalField): Comisión aplicada al vender la divisa destino.
        activo (BooleanField): Indica si la tasa de cambio está actualmente activa.

    """

    id_tasa_cambio = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, help_text="Identificador único para la tasa de cambio."
    )
    divisa_origen = models.ForeignKey(
        "Divisa",
        on_delete=models.PROTECT,
        related_name="tasas_origen",
        help_text="La divisa que se va a intercambiar.",
    )
    divisa_destino = models.ForeignKey(
        "Divisa",
        on_delete=models.PROTECT,
        related_name="tasas_destino",
        help_text="La divisa a la cual se va a convertir.",
    )
    precio_base = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        help_text="El precio base de la divisa de origen en términos de la divisa de destino.",
    )
    comision_compra = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="Monto de comisión por compra en la divisa de destino (Guaraníes).",
    )
    comision_venta = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="Monto de comisión por venta en la divisa de destino (Guaraníes).",
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True, help_text="Fecha y hora de la última actualización de la tasa."
    )
    activo = models.BooleanField(
        default=True, help_text="Indica si la tasa de cambio está activa o ha sido desactivada."
    )

    def clean(self):
        """Valida que una de las divisas sea la Divisa base (PYG) y que los valores sean positivos."""
        # Validar que una de las divisas sea PYG
        es_divisa_base = self.divisa_origen.codigo == "PYG" or self.divisa_destino.codigo == "PYG"
        if not es_divisa_base:
            raise ValidationError("Una de las divisas en la tasa de cambio debe ser la Divisa base (PYG).")

        # Validar que el precio base sea positivo
        if self.precio_base is not None and self.precio_base <= 0:
            raise ValidationError("El precio base de la divisa debe ser positivo.")

        # Validar que las comisiones sean no negativas
        if self.comision_compra is not None and self.comision_compra < 0:
            raise ValidationError("La comisión de compra no puede ser negativa.")

        if self.comision_venta is not None and self.comision_venta < 0:
            raise ValidationError("La comisión de venta no puede ser negativa.")

        # Validar que la comisión de compra sea menor que el precio base
        if (
            self.comision_compra is not None
            and self.precio_base is not None
            and self.comision_compra >= self.precio_base
        ):
            raise ValidationError(
                {
                    "comision_compra": "La comisión de compra debe ser menor que el precio base.\n"
                    f"Precio base: {self.precio_base}, Comisión: {self.comision_compra}"
                }
            )

        # Validar que la comisión de venta sea menor que el precio base
        if self.comision_venta is not None and self.precio_base is not None and self.comision_venta >= self.precio_base:
            raise ValidationError(
                {
                    "comision_venta": "La comisión de venta debe ser menor que el precio base.\n"
                    f"Precio base: {self.precio_base}, Comisión: {self.comision_venta}"
                }
            )

    def save(self, *args, **kwargs):
        """Guarda el objeto después de validar los datos."""
        self.full_clean()
        super().save(*args, **kwargs)

    # Las siguientes funciones no se definen como campos del modelo en Django,
    # sino como métodos de la clase para encapsular la lógica de negocio.
    def actualizar_tasa_compra(self, tasa: float):
        """Método para actualizar la tasa de compra."""
        # Lógica para actualizar la tasa de compra
        pass

    def actualizar_tasa_venta(self, tasa: float):
        """Método para actualizar la tasa de venta."""
        # Lógica para actualizar la tasa de venta
        pass

    def consultar_tasa_actual(self) -> Decimal:
        """Método para consultar la tasa de cambio actual.

        Retorna el precio base actual de la divisa almacenado en el atributo 'precio_base'.
        En esta clase se define la clave primaria (PK) y las restricciones de unicidad
        para asegurar la integridad de los datos de operaciones de cambio.
        """
        return self.precio_base

    @property
    def tasa_compra(self) -> Decimal:
        """Calcula la tasa de compra aplicando la comisión correspondiente."""
        # Para compra, el cliente paga más (precio_base + comisión)
        return self.precio_base + self.comision_compra

    @property
    def tasa_venta(self) -> Decimal:
        """Calcula la tasa de venta aplicando la comisión correspondiente."""
        # Para venta, el cliente recibe menos (precio_base - comisión)
        return self.precio_base - self.comision_venta

    class Meta:
        """Meta información para el modelo TasaCambio.

        Define detalles como el nombre de la tabla, nombres para la administración
        y restricciones de unicidad.
        """

        # Nombre de la tabla en la base de datos
        db_table = "tasa_cambio"
        # Nombre singular y plural para el panel de administración de Django
        verbose_name = "Tasa de Cambio"
        verbose_name_plural = "Tasas de Cambio"
        # Restricción de unicidad para evitar duplicados, por ejemplo,
        # que no haya dos tasas activas con la misma divisa origen y destino.
        unique_together = ("divisa_origen", "divisa_destino")

    def __str__(self):
        """Representación en string del objeto, útil para la administración."""
        estado = "Activa" if self.activo else "Inactiva"
        return f"{self.divisa_origen} a {self.divisa_destino} - Precio Base: {self.precio_base} ({estado})"


class TasaCambioHistorial(models.Model):
    """Representa el historial de cambios de las tasas de cambio.

    Este modelo almacena un registro histórico de todas las modificaciones
    realizadas a las tasas de cambio, permitiendo tener un seguimiento
    completo de los cambios a lo largo del tiempo.

    Argumentos:
        id (UUIDField): Identificador único para el registro histórico.
        tasa_cambio_original (ForeignKey): Referencia a la tasa de cambio original.
        divisa_origen (ForeignKey): La divisa desde la que se realiza la conversión.
        divisa_destino (ForeignKey): La divisa a la que se realiza la conversión.
        precio_base (DecimalField): El precio base de la divisa en el momento del registro.
        comision_compra (DecimalField): Comisión aplicada al comprar la divisa destino.
        comision_venta (DecimalField): Comisión aplicada al vender la divisa destino.
        fecha_registro (DateTimeField): Fecha y hora cuando se registró este historial.
        activo (BooleanField): Estado de la tasa de cambio en el momento del registro.
        motivo (CharField): Motivo del cambio realizado.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tasa_cambio_original = models.ForeignKey("TasaCambio", on_delete=models.CASCADE, related_name="historial")
    divisa_origen = models.ForeignKey("Divisa", on_delete=models.PROTECT, related_name="tasas_historial_origen")
    divisa_destino = models.ForeignKey("Divisa", on_delete=models.PROTECT, related_name="tasas_historial_destino")
    precio_base = models.DecimalField(max_digits=9, decimal_places=3)
    comision_compra = models.DecimalField(max_digits=7, decimal_places=3)
    comision_venta = models.DecimalField(max_digits=7, decimal_places=3)
    fecha_registro = models.DateTimeField(default=timezone.now)
    activo = models.BooleanField(default=True)
    motivo = models.CharField(max_length=255, help_text="Motivo del cambio (ej. Creación, Edición, Desactivación)")

    class Meta:
        """Meta información para el modelo TasaCambioHistorial.

        Define detalles como el nombre de la tabla, nombres para la administración
        y ordenamiento por defecto.
        """

        db_table = "tasa_cambio_historial"
        verbose_name = "Historial de Tasa de Cambio"
        verbose_name_plural = "Historial de Tasas de Cambio"
        ordering = ["-fecha_registro"]
