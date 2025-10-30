"""Comando para generar datos históricos de prueba para las tasas de cambio."""

from datetime import timedelta
from decimal import Decimal
from random import uniform

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.operaciones.models import TasaCambio, TasaCambioHistorial


class Command(BaseCommand):
    """Comando para generar historial de tasas de cambio de prueba."""

    help = "Genera datos históricos de prueba para las tasas de cambio (últimos 365 días)"

    def add_arguments(self, parser):
        """Agregar argumentos al comando."""
        parser.add_argument(
            "--dias",
            type=int,
            default=365,
            help="Número de días hacia atrás para generar historial (default: 365)",
        )
        parser.add_argument(
            "--limpiar",
            action="store_true",
            help="Eliminar historial existente antes de generar nuevo",
        )

    def handle(self, *args, **options):
        """Ejecutar el comando."""
        dias = options["dias"]
        limpiar = options["limpiar"]

        self.stdout.write(self.style.WARNING(f"Generando historial de {dias} días..."))

        # Obtener todas las tasas de cambio activas
        tasas = TasaCambio.objects.filter(activo=True).select_related("divisa_origen", "divisa_destino")

        if not tasas.exists():
            self.stdout.write(self.style.ERROR("No hay tasas de cambio activas en el sistema."))
            return

        # Limpiar historial si se solicita
        if limpiar:
            self.stdout.write(self.style.WARNING("Limpiando historial existente..."))
            TasaCambioHistorial.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Historial limpiado."))

        total_registros = 0

        # Para cada tasa de cambio
        for tasa in tasas:
            self.stdout.write(f"Generando historial para {tasa.divisa_origen.codigo}/{tasa.divisa_destino.codigo}...")

            # Valores base para generar variaciones realistas
            precio_base = float(tasa.precio_base)
            comision_compra = float(tasa.comision_compra)
            comision_venta = float(tasa.comision_venta)

            # Generar un registro por día
            for i in range(dias, 0, -1):
                # Calcular la fecha para este registro
                fecha_registro = timezone.now() - timedelta(days=i)

                # Generar variación aleatoria del precio (±5%)
                variacion = uniform(-0.05, 0.05)
                precio_historico = Decimal(str(precio_base * (1 + variacion))).quantize(Decimal("0.001"))

                # Pequeña variación en comisiones (±2%)
                var_comision = uniform(-0.02, 0.02)
                comision_compra_hist = Decimal(str(comision_compra * (1 + var_comision))).quantize(Decimal("0.001"))
                comision_venta_hist = Decimal(str(comision_venta * (1 + var_comision))).quantize(Decimal("0.001"))

                # Crear el registro histórico
                TasaCambioHistorial.objects.create(
                    tasa_cambio_original=tasa,
                    divisa_origen=tasa.divisa_origen,
                    divisa_destino=tasa.divisa_destino,
                    precio_base=precio_historico,
                    comision_compra=comision_compra_hist,
                    comision_venta=comision_venta_hist,
                    fecha_registro=fecha_registro,
                    activo=tasa.activo,
                    motivo=f"Registro histórico generado automáticamente - Día {i}",
                )

                total_registros += 1

        self.stdout.write(
            self.style.SUCCESS(f"✓ Se generaron {total_registros} registros históricos para {len(tasas)} tasas.")
        )
        self.stdout.write(self.style.SUCCESS("Ahora puedes visualizar el historial completo en los gráficos."))
