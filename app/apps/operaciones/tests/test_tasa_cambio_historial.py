"""Pruebas unitarias para el modelo TasaCambioHistorial."""

import datetime
from decimal import Decimal

import pytest
from apps.operaciones.models import Divisa, TasaCambio, TasaCambioHistorial
from django.utils import timezone


@pytest.mark.django_db
class TestTasaCambioHistorialModel:
    """Pruebas unitarias para el modelo TasaCambioHistorial."""

    def setup_method(self):
        """Configura divisas y una tasa de cambio base para los tests."""
        self.divisa_pyg = Divisa.objects.create(codigo="PYG", nombre="Guaraní", simbolo="₲", estado="activa")
        self.divisa_usd = Divisa.objects.create(codigo="USD", nombre="Dólar", simbolo="$", estado="activa")
        self.tasa = TasaCambio.objects.create(
            divisa_origen=self.divisa_pyg,
            divisa_destino=self.divisa_usd,
            valor=Decimal("7000.000"),
            comision_compra=Decimal("10.000"),
            comision_venta=Decimal("15.000"),
            fecha_vigencia=timezone.now().date(),
            hora_vigencia=datetime.time(7, 0),
            activo=True,
        )

    def test_create_tasa_cambio_historial(self):
        """Verifica que se puede crear un historial y se guarda correctamente."""
        historial = TasaCambioHistorial.objects.create(
            tasa_cambio_original=self.tasa,
            divisa_origen=self.divisa_pyg,
            divisa_destino=self.divisa_usd,
            valor=Decimal("7000.000"),
            comision_compra=Decimal("10.000"),
            comision_venta=Decimal("15.000"),
            fecha_vigencia=timezone.now().date(),
            hora_vigencia=datetime.time(7, 0),
            activo=True,
            motivo="Creación",
        )
        assert TasaCambioHistorial.objects.filter(pk=historial.pk).exists()
        assert historial.tasa_cambio_original == self.tasa
        assert historial.divisa_origen.codigo == "PYG"
        assert historial.divisa_destino.codigo == "USD"
        assert historial.motivo == "Creación"

    def test_historial_relacion_con_tasa(self):
        """Verifica que el historial se asocia correctamente a la tasa de cambio."""
        historial = TasaCambioHistorial.objects.create(
            tasa_cambio_original=self.tasa,
            divisa_origen=self.divisa_pyg,
            divisa_destino=self.divisa_usd,
            valor=Decimal("7000.000"),
            comision_compra=Decimal("10.000"),
            comision_venta=Decimal("15.000"),
            fecha_vigencia=timezone.now().date(),
            hora_vigencia=datetime.time(7, 0),
            activo=True,
            motivo="Edición",
        )
        assert TasaCambioHistorial.objects.filter(tasa_cambio_original=historial.tasa_cambio_original).count() == 1
        assert historial in TasaCambioHistorial.objects.filter(tasa_cambio_original=self.tasa)

    def test_historial_fecha_registro_auto(self):
        """Verifica que fecha_registro se asigna automáticamente al crear el historial."""
        historial = TasaCambioHistorial.objects.create(
            tasa_cambio_original=self.tasa,
            divisa_origen=self.divisa_pyg,
            divisa_destino=self.divisa_usd,
            valor=Decimal("7000.000"),
            comision_compra=Decimal("10.000"),
            comision_venta=Decimal("15.000"),
            fecha_vigencia=timezone.now().date(),
            hora_vigencia=datetime.time(7, 0),
            activo=True,
            motivo="Creación",
        )
        assert historial.fecha_registro is not None
