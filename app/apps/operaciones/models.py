from decimal import Decimal

from django.db import models


class TipoDeCambio(models.Model):
    """Define los tipos de cambio disponibles: Compra y Venta.

    El argumento TextChoices permite seleccionar entre opciones predefinidas
    para los tipos de cambio que se pueden aplicar.

    Args:
        nombre (str): El nombre del tipo de cambio (e.g., 'Compra', 'Venta').

    """

    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre")
    """La funcion __str__ devuelve un nombre entendible para el objeto Tipo de Cambio.
    """

    def __str__(self):
        return self.nombre


class Moneda(models.Model):
    """Representa una moneda utilizada en el sistema de cambio.

    Este modelo almacena información básica sobre cada moneda, incluyendo su
    símbolo, país, estado de activación, y las tasas de cambio y comisiones
    asociadas.

    Args:
        nombre (CharField): El nombre de la moneda (e.g., 'Dólar').
        simbolo (CharField): El símbolo de la moneda (e.g., 'USD').
        pais (CharField): El país al que pertenece la moneda.
        esta_activa (BooleanField): Indica si la moneda está activa para operaciones.
        tipo_de_cambio (ForeignKey): El tipo de cambio asociado (Compra o Venta).
        comision (DecimalField): comisión aplicada a las transacciones de esta moneda.
        tasa_actual (DecimalField): La tasa de cambio actual en tiempo real.

    """

    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre")
    simbolo = models.CharField(max_length=5, unique=True, verbose_name="Símbolo")
    pais = models.CharField(max_length=50, blank=True, verbose_name="País")
    esta_activa = models.BooleanField(default=True, verbose_name="Está Activa")

    comision = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        # chequear que la cantidad de decimales sean los correctos
        default=Decimal("0.00"),
        verbose_name="Comisión (%)",
    )

    tipo_de_cambio = models.ForeignKey(
        "TipoDeCambio",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="Tipo de Cambio",
    )

    tasa_actual = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        # chequear que la cantidad de decimales sean los correctos
        default=Decimal("0.0000"),
        verbose_name="Tasa Actual",
    )

    def __str__(self):
        """Devuelve una representación en cadena del objeto. Por ejem, Dolar, USD"""
        return f"{self.nombre} ({self.simbolo})"


class TasaDeCambio(models.Model):
    """Almacena el historial de las tasas de cambio para una moneda.

    El modelo permite registrar el valor de las tasas de compra y venta
    en un momento específico.

    Args:
        moneda (ForeignKey): La moneda a la que pertenece la tasa de cambio.
        tasa_compra (DecimalField): La tasa de compra registrada en ese momento.
        tasa_venta (DecimalField): La tasa de venta registrada en ese momento.
        fecha_y_hora (DateTimeField): El momento en que la tasa fue registrada.

    """

    moneda = models.ForeignKey(
        Moneda,
        on_delete=models.CASCADE,
        verbose_name="Moneda",
    )
    tasa_compra = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Tasa de Compra")
    tasa_venta = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Tasa de Venta")
    fecha_y_hora = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")

    def __str__(self):
        """Devuelve una representación en cadena del objeto."""
        return f"Tasa de {self.moneda.nombre} - Compra: {self.tasa_compra}, Venta: {self.tasa_venta}"
