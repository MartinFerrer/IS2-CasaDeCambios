# Create your models here.
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class ExchangeSimulation(models.Model):
    """
    Modelo de simulación simple para una casa de cambios.

    Regla fija:
      - divisa1 = 2 * divisa2

    Restricciones:
      - Ambos campos son enteros entre 1 y 10 (inclusive).

    Uso típico:
      - comprar_divisa2(): ¿Cuánta divisa1 necesito para comprar `divisa2`?
      - vender_divisa1(): ¿Cuánta divisa2 recibo si vendo `divisa1`?
    """

    # Entradas del usuario (1..10)
    divisa1 = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Cantidad de divisa1 (1-10)."
    )
    divisa2 = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Cantidad de divisa2 (1-10)."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Simulación de Cambio"
        verbose_name_plural = "Simulaciones de Cambio"

    def __str__(self) -> str:
        return f"Simulación(divisa1={self.divisa1}, divisa2={self.divisa2})"

    # Regla base: divisa1 = 2 * divisa2
    RATE_NUM = 2
    RATE_DEN = 1

    def comprar_divisa2(self) -> int:
        """
        ¿Cuánta divisa1 necesito para comprar self.divisa2?
        Según la regla: divisa1 = 2 * divisa2
        """
        return self.RATE_NUM * self.divisa2 // self.RATE_DEN

    def vender_divisa1(self) -> int:
        """
        ¿Cuánta divisa2 recibo si vendo self.divisa1?
        Invirtiendo la regla: divisa2 = divisa1 / 2
        """
        return self.divisa1 * self.RATE_DEN // self.RATE_NUM

    def salida_basica(self) -> str:
        """
        Representación básica para mostrar al usuario.
        """
        return (
            f"Para comprar {self.divisa2} divisa2 necesitas "
            f"{self.comprar_divisa2()} divisa1. "
            f"Si vendes {self.divisa1} divisa1 recibes "
            f"{self.vender_divisa1()} divisa2."
        )