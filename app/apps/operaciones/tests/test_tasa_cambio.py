"""Pruebas unitarias para el modelo TasaCambio."""

import datetime
from decimal import Decimal

import pytest
from apps.operaciones.models import Divisa, TasaCambio
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone


@pytest.mark.django_db
class TestTasaCambioModel:
    """Pruebas unitarias para el modelo TasaCambio."""

    def setup_method(self):
        """Configura las divisas base para los tests."""
        self.divisa_pyg = Divisa.objects.get_or_create(codigo="PYG", nombre="Guaraní", simbolo="₲", estado="activa")
        self.divisa_usd = Divisa.objects.get_or_create(codigo="USD", nombre="Dólar", simbolo="$", estado="activa")

    def test_valor_negativo_no_permitido(self):
        """No debe permitirse val|or negativo en la tasa de cambio."""
        with pytest.raises(ValidationError):
            TasaCambio.objects.create(
                divisa_origen=self.divisa_pyg,
                divisa_destino=self.divisa_usd,
                valor=Decimal("-1.000"),
                comision_compra=Decimal("10.000"),
                comision_venta=Decimal("15.000"),
                fecha_vigencia=timezone.now().date(),
                hora_vigencia=datetime.time(7, 0),
                activo=True,
            )

    def test_comision_compra_negativa_no_permitida(self):
        """No debe permitirse comisión de compra negativa."""
        with pytest.raises(ValidationError):
            TasaCambio.objects.create(
                divisa_origen=self.divisa_pyg,
                divisa_destino=self.divisa_usd,
                valor=Decimal("7000.000"),
                comision_compra=Decimal("-5.000"),
                comision_venta=Decimal("15.000"),
                fecha_vigencia=timezone.now().date(),
                hora_vigencia=datetime.time(7, 0),
                activo=True,
            )

    def test_comision_venta_negativa_no_permitida(self):
        """No debe permitirse comisión de venta negativa."""
        with pytest.raises(ValidationError):
            TasaCambio.objects.create(
                divisa_origen=self.divisa_pyg,
                divisa_destino=self.divisa_usd,
                valor=Decimal("7000.000"),
                comision_compra=Decimal("10.000"),
                comision_venta=Decimal("-2.000"),
                fecha_vigencia=timezone.now().date(),
                hora_vigencia=datetime.time(7, 0),
                activo=True,
            )

    def test_valor_cero_no_permitido(self):
        """No debe permitirse valor cero en la tasa de cambio."""
        with pytest.raises(ValidationError):
            TasaCambio.objects.create(
                divisa_origen=self.divisa_pyg,
                divisa_destino=self.divisa_usd,
                valor=Decimal("0.000"),
                comision_compra=Decimal("10.000"),
                comision_venta=Decimal("15.000"),
                fecha_vigencia=timezone.now().date(),
                hora_vigencia=datetime.time(7, 0),
                activo=True,
            )

    def test_clean_valid_base_currency(self):
        """Valida que clean() no lance excepción si una divisa es PYG."""
        tasa = TasaCambio(
            divisa_origen=self.divisa_pyg,
            divisa_destino=self.divisa_usd,
            valor=Decimal("7000.000"),
            comision_compra=Decimal("10.000"),
            comision_venta=Decimal("15.000"),
            fecha_vigencia=timezone.now().date(),
            hora_vigencia=datetime.time(7, 0),
            activo=True,
        )
        tasa.clean()  # No debe lanzar excepción

    def test_clean_invalid_base_currency(self):
        """Valida que clean() lance ValidationError si ninguna divisa es PYG."""
        divisa_eur = Divisa.objects.create(codigo="EUR", nombre="Euro", simbolo="€", estado="activa")
        tasa = TasaCambio(
            divisa_origen=divisa_eur,
            divisa_destino=self.divisa_usd,
            valor=Decimal("1.000"),
            comision_compra=Decimal("0.000"),
            comision_venta=Decimal("0.000"),
            fecha_vigencia=timezone.now().date(),
            hora_vigencia=datetime.time(7, 0),
            activo=True,
        )
        with pytest.raises(ValidationError):
            tasa.clean()

    def test_create_tasa_cambio(self):
        """Verifica que se puede crear una TasaCambio y se guarda correctamente."""
        tasa = TasaCambio.objects.create(
            divisa_origen=self.divisa_pyg,
            divisa_destino=self.divisa_usd,
            valor=Decimal("7000.000"),
            comision_compra=Decimal("10.000"),
            comision_venta=Decimal("15.000"),
            fecha_vigencia=timezone.now().date(),
            hora_vigencia=datetime.time(7, 0),
            activo=True,
        )
        assert TasaCambio.objects.filter(pk=tasa.pk).exists()
        assert tasa.divisa_origen.codigo == "PYG"
        assert tasa.divisa_destino.codigo == "USD"

    def test_consultar_tasa_actual(self):
        """Verifica que consultar_tasa_actual retorna el valor correcto."""
        tasa = TasaCambio.objects.create(
            divisa_origen=self.divisa_pyg,
            divisa_destino=self.divisa_usd,
            valor=Decimal("7000.000"),
            comision_compra=Decimal("10.000"),
            comision_venta=Decimal("15.000"),
            fecha_vigencia=timezone.now().date(),
            hora_vigencia=datetime.time(7, 0),
            activo=True,
        )
        assert tasa.consultar_tasa_actual() == Decimal("7000.000")

    def test_unique_together_constraint(self):
        """Verifica que no se pueden crear dos tasas con la misma combinación origen/destino."""
        TasaCambio.objects.create(
            divisa_origen=self.divisa_pyg,
            divisa_destino=self.divisa_usd,
            valor=Decimal("7000.000"),
            comision_compra=Decimal("10.000"),
            comision_venta=Decimal("15.000"),
            fecha_vigencia=timezone.now().date(),
            hora_vigencia=datetime.time(7, 0),
            activo=True,
        )
        with pytest.raises(IntegrityError):
            # Debe fallar por restricción de unicidad
            TasaCambio.objects.create(
                divisa_origen=self.divisa_pyg,
                divisa_destino=self.divisa_usd,
                valor=Decimal("8000.000"),
                comision_compra=Decimal("20.000"),
                comision_venta=Decimal("25.000"),
                fecha_vigencia=timezone.now().date(),
                hora_vigencia=datetime.time(8, 0),
                activo=True,
            )
