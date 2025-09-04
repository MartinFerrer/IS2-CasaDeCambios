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
    símbolo, país, estado de activación, y las tasas de cambio y comisiones
    asociadas.

    Args:
        idDivisa (UUIDField): Identificador único para la Divisa.
        codigo (CharField): El código ISO 4217 de la Divisa (e.g 'USD', 'EUR').
        nombre (CharField): El nombre de la Divisa (e.g., 'Dólar').
        simbolo (CharField): El símbolo de la Divisa (ej. ₲, $, €).

    """

    idDivisa = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, help_text="Identificador único para la divisa."
    )
    codigo = models.CharField(max_length=3, unique=True, help_text="Código ISO 4217 de la divisa (ej. PYG, USD, EUR).")
    nombre = models.CharField(max_length=50, help_text="Nombre de la divisa (ej. Guaraní, Dólar Estadounidense).")
    simbolo = models.CharField(max_length=5, help_text="Símbolo de la divisa (ej. ₲, $, €).")

    class Meta:
        db_table = "divisa"
        verbose_name = "Divisa"
        verbose_name_plural = "Divisas"

    def __str__(self):
        """Representación en string del objeto, útil para su visualización."""
        return f"{self.codigo}"


class TasaCambio(models.Model):
    """Modelo para gestionar las tasas de cambio entre divisas.

    Representa el valor de una divisa con respecto a otra en un momento dado.
    """

    id_tasa_cambio = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, help_text="Identificador único para la tasa de cambio."
    )
    divisa_origen = models.ForeignKey(
        "Divisa", on_delete=models.CASCADE, related_name="tasas_origen", help_text="La divisa que se va a intercambiar."
    )
    divisa_destino = models.ForeignKey(
        "Divisa",
        on_delete=models.CASCADE,
        related_name="tasas_destino",
        help_text="La divisa a la cual se va a convertir.",
    )
    valor = models.DecimalField(
        max_digits=15,
        decimal_places=8,
        help_text="El valor de la divisa de origen en términos de la divisa de destino.",
    )
    comision_compra = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Monto de comisión por compra en la divisa de destino (Guaraníes).",
    )
    comision_venta = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Monto de comisión por venta en la divisa de destino (Guaraníes).",
    )
    fecha_actualizacion = models.DateField(
        auto_now=True, help_text="Fecha y hora de la última actualización de la tasa."
    )
    fecha_vigencia = models.DateField(help_text="Fecha a partir de la cual esta tasa es válida.")
    activo = models.BooleanField(
        default=True, help_text="Indica si la tasa de cambio está activa o ha sido desactivada."
    )

    def clean(self):
        """Valida que una de las divisas en la tasa de cambio sea la Divisa base (PYG)."""
        # Suponiendo que la divisa base (PYG) se puede identificar por un código,
        # un campo booleano 'es_base', o un ID conocido.
        # Por ahora, trabajando con el código 'PYG'.
        es_Divisa_base = self.divisa_origen.codigo == "PYG" or self.divisa_destino.codigo == "PYG"

        if not es_Divisa_base:
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
        """Método para consultar la tasa de cambio actual."""
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
