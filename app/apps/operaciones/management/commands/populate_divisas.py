import random
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.management.base import BaseCommand

from apps.operaciones.models import TasaCambio, TasaCambioHistorial


class Command(BaseCommand):
    """Comando de Django para generar un historial simulado de tasas de cambio.

    Este comando crea registros diarios en el modelo :class:`TasaCambioHistorial`
    desde el 17 de octubre de 2025 hasta la fecha actual, aplicando una variación
    aleatoria del ±0.5% sobre el precio base de cada tasa activa.

    **Uso:**

    .. code-block:: bash

        python manage.py generar_historial_tasas

    **Detalles:**
        - Elimina cualquier historial anterior asociado a las tasas activas.
        - Genera nuevas tasas con pequeñas fluctuaciones diarias.
        - Mantiene la coherencia con las comisiones de compra y venta originales.

    """

    help = "Genera historial de tasas de cambio realista desde el 2 de octubre hasta hoy."

    def handle(self, *args, **options):
        """Ejecuta el proceso de generación de historial.

        :param args: Argumentos posicionales del comando.
        :param options: Opciones adicionales (no utilizadas).
        """
        start_date = datetime(2025, 10, 2)
        end_date = datetime.today()
        delta = timedelta(days=1)

        fechas = []
        current = start_date
        while current <= end_date:
            fechas.append(current)
            current += delta

        tasas_activas = TasaCambio.objects.filter(activo=True)

        if not tasas_activas.exists():
            self.stdout.write(self.style.WARNING("No hay tasas activas para generar historial."))
            return

        # Eliminar historiales previos de las tasas activas
        TasaCambioHistorial.objects.filter(tasa_cambio_original__in=tasas_activas).delete()
        self.stdout.write(self.style.WARNING("Historial antiguo eliminado."))

        for tasa in tasas_activas:
            precio_base = tasa.precio_base
            ultimo_precio = precio_base

            for fecha in fechas:
                variacion = ultimo_precio * Decimal(random.uniform(-0.005, 0.005))
                nuevo_precio = (ultimo_precio + variacion).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

                TasaCambioHistorial.objects.create(
                    tasa_cambio_original=tasa,
                    divisa_origen=tasa.divisa_origen,
                    divisa_destino=tasa.divisa_destino,
                    precio_base=nuevo_precio,
                    comision_compra=tasa.comision_compra,
                    comision_venta=tasa.comision_venta,
                    activo=True,
                    motivo=f"Historial simulado {fecha.strftime('%Y-%m-%d')}",
                    fecha_registro=fecha,
                )

                ultimo_precio = nuevo_precio

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Historial para {tasa.divisa_origen.codigo}->{tasa.divisa_destino.codigo} "
                        f"en {fecha.strftime('%Y-%m-%d')} cargado: {nuevo_precio}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Historial de tasas activas cargado correctamente desde el 17 de octubre hasta {end_date.strftime('%Y-%m-%d')}."
            )
        )
