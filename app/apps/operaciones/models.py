"""Modelos para gestionar divisas y tasas de cambio en el sistema de Casa de Cambios.

Incluye:
- Divisa: modelo para las monedas soportadas.
- TasaCambio: modelo para las tasas de cambio entre divisas.
"""

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class Divisa(models.Model):
    """Representa una Divisa utilizada en el sistema de cambio.

    Este modelo almacena información básica sobre cada Divisa, incluyendo su
    código ISO, nombre y símbolo.

    Argumentos:
        codigo (CharField): El código ISO 4217 de la Divisa (e.g 'USD', 'EUR').
        nombre (CharField): El nombre de la Divisa (e.g., 'Dólar').
        simbolo (CharField): El símbolo de la Divisa (ej. ₲, $, €).

    """

    codigo = models.CharField(
        primary_key=True, max_length=3, unique=True, help_text="Código ISO 4217 de la divisa (ej. PYG, USD, EUR)."
    )
    nombre = models.CharField(max_length=50, help_text="Nombre de la divisa (ej. Guaraní, Dólar Estadounidense).")
    simbolo = models.CharField(max_length=5, help_text="Símbolo de la divisa (ej. ₲, $, €).")

    class Meta:
        """Meta información para el modelo Divisa.

        Define detalles como el nombre de la tabla y nombres para la administración.
        """

        db_table = "divisa"
        verbose_name = "Divisa"
        verbose_name_plural = "Divisas"

    def __str__(self):
        """Representación en string del objeto, útil para su visualización."""
        return f"{self.codigo}"


class TasaCambio(models.Model):
    """Representa la Tasa de Cambio de una divisa a otra.

    Este modelo almacena el valor de la tasa de cambio entre dos divisas, junto
    con las comisiones asociadas para la compra y venta. También incluye la fecha
    en que la tasa entra en vigencia.

    Argumentos:
        id_tasa_cambio (UUIDField): Identificador único para la tasa de cambio.
        divisa_origen (ForeignKey): La divisa desde la que se realiza la conversión.
        divisa_destino (ForeignKey): La divisa a la que se realiza la conversión.
        valor (DecimalField): El valor de la tasa de cambio.
        comision_compra (DecimalField): Comisión aplicada al comprar la divisa destino.
        comision_venta (DecimalField): Comisión aplicada al vender la divisa destino.
        fecha_vigencia (DateField): Fecha en que la tasa de cambio es válida.
        hora_vigencia (TimeField): Hora en que la tasa de cambio es válida.
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
    valor = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        help_text="El valor de la divisa de origen en términos de la divisa de destino.",
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
    fecha_vigencia = models.DateField(help_text="Fecha a partir de la cual esta tasa es válida.")
    activo = models.BooleanField(
        default=True, help_text="Indica si la tasa de cambio está activa o ha sido desactivada."
    )
    hora_vigencia = models.TimeField(
        null=True, blank=True, help_text="Hora en la que la tasa de cambio entra en vigencia."
    )

    def clean(self):
        """Valida que una de las divisas en la tasa de cambio sea la Divisa base (PYG)."""
        # Suponiendo que la divisa base (PYG) se puede identificar por un código,
        # un campo booleano 'es_base', o un ID conocido.
        # Por ahora, trabajando con el código 'PYG'.
        es_divisa_base = self.divisa_origen.codigo == "PYG" or self.divisa_destino.codigo == "PYG"

        if not es_divisa_base:
            raise ValidationError("Una de las divisas en la tasa de cambio debe ser la Divisa base (PYG).")

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

        Retorna el valor actual de la tasa de cambio almacenado en el atributo 'valor'.
        En esta clase se define la clave primaria (PK) y las restricciones de unicidad
        para asegurar la integridad de los datos de operaciones de cambio.
        """
        return self.valor

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
        return f"{self.divisa_origen} a {self.divisa_destino} - Valor: {self.valor} ({estado})"


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
        valor (DecimalField): El valor de la tasa de cambio en el momento del registro.
        comision_compra (DecimalField): Comisión aplicada al comprar la divisa destino.
        comision_venta (DecimalField): Comisión aplicada al vender la divisa destino.
        fecha_vigencia (DateField): Fecha en que la tasa de cambio era válida.
        hora_vigencia (TimeField): Hora en que la tasa de cambio era válida.
        fecha_registro (DateTimeField): Fecha y hora cuando se registró este historial.
        activo (BooleanField): Estado de la tasa de cambio en el momento del registro.
        motivo (CharField): Motivo del cambio realizado.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tasa_cambio_original = models.ForeignKey("TasaCambio", on_delete=models.CASCADE, related_name="historial")
    divisa_origen = models.ForeignKey("Divisa", on_delete=models.PROTECT, related_name="tasas_historial_origen")
    divisa_destino = models.ForeignKey("Divisa", on_delete=models.PROTECT, related_name="tasas_historial_destino")
    valor = models.DecimalField(max_digits=9, decimal_places=3)
    comision_compra = models.DecimalField(max_digits=7, decimal_places=3)
    comision_venta = models.DecimalField(max_digits=7, decimal_places=3)
    fecha_vigencia = models.DateField()
    hora_vigencia = models.TimeField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
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
