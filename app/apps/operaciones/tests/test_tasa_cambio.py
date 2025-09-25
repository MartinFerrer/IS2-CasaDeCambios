"""Pruebas unitarias para el modelo TasaCambio."""

from decimal import Decimal

import pytest
from apps.operaciones.models import Divisa, TasaCambio
from django.core.exceptions import ValidationError


@pytest.mark.django_db
class TestTasaCambioModel:
    """Pruebas unitarias para el modelo TasaCambio."""

    def setup_method(self):
        """Configura las divisas base para los tests."""
        self.divisa_pyg, _ = Divisa.objects.get_or_create(
            codigo="PYG", defaults={"nombre": "Guaraní", "simbolo": "₲", "estado": "activa"}
        )
        self.divisa_usd, _ = Divisa.objects.get_or_create(
            codigo="USD", defaults={"nombre": "Dólar", "simbolo": "$", "estado": "activa"}
        )

    def test_precio_base_negativo_no_permitido(self):
        """No debe permitirse precio base negativo en la tasa de cambio."""
        with pytest.raises(ValidationError):
            TasaCambio.objects.create(
                divisa_origen=self.divisa_pyg,
                divisa_destino=self.divisa_usd,
                precio_base=Decimal("-1.000"),
                comision_compra=Decimal("10.000"),
                comision_venta=Decimal("15.000"),
                activo=True,
            )

    def test_comision_compra_negativa_no_permitida(self):
        """No debe permitirse comisión de compra negativa."""
        with pytest.raises(ValidationError):
            TasaCambio.objects.create(
                divisa_origen=self.divisa_pyg,
                divisa_destino=self.divisa_usd,
                precio_base=Decimal("7000.000"),
                comision_compra=Decimal("-5.000"),
                comision_venta=Decimal("15.000"),
                activo=True,
            )

    def test_comision_venta_negativa_no_permitida(self):
        """No debe permitirse comisión de venta negativa."""
        with pytest.raises(ValidationError):
            TasaCambio.objects.create(
                divisa_origen=self.divisa_pyg,
                divisa_destino=self.divisa_usd,
                precio_base=Decimal("7000.000"),
                comision_compra=Decimal("10.000"),
                comision_venta=Decimal("-2.000"),
                activo=True,
            )

    def test_precio_base_cero_no_permitido(self):
        """No debe permitirse precio base cero en la tasa de cambio."""
        with pytest.raises(ValidationError):
            TasaCambio.objects.create(
                divisa_origen=self.divisa_pyg,
                divisa_destino=self.divisa_usd,
                precio_base=Decimal("0.000"),
                comision_compra=Decimal("10.000"),
                comision_venta=Decimal("15.000"),
                activo=True,
            )

    def test_clean_valid_base_currency(self):
        """Valida que clean() no lance excepción si una divisa es PYG."""
        tasa = TasaCambio(
            divisa_origen=self.divisa_pyg,
            divisa_destino=self.divisa_usd,
            precio_base=Decimal("7000.000"),
            comision_compra=Decimal("10.000"),
            comision_venta=Decimal("15.000"),
            activo=True,
        )
        tasa.clean()  # No debe lanzar excepción

    def test_clean_invalid_base_currency(self):
        """Valida que clean() lance ValidationError si ninguna divisa es PYG."""
        divisa_eur, _ = Divisa.objects.get_or_create(
            codigo="EUR", defaults={"nombre": "Euro", "simbolo": "€", "estado": "activa"}
        )
        tasa = TasaCambio(
            divisa_origen=divisa_eur,
            divisa_destino=self.divisa_usd,
            precio_base=Decimal("1.000"),
            comision_compra=Decimal("0.000"),
            comision_venta=Decimal("0.000"),
            activo=True,
        )
        with pytest.raises(ValidationError):
            tasa.clean()

    def test_create_tasa_cambio(self):
        """Verifica que se puede crear una TasaCambio y se guarda correctamente."""
        tasa = TasaCambio.objects.create(
            divisa_origen=self.divisa_pyg,
            divisa_destino=self.divisa_usd,
            precio_base=Decimal("7000.000"),
            comision_compra=Decimal("10.000"),
            comision_venta=Decimal("15.000"),
            activo=True,
        )
        assert TasaCambio.objects.filter(pk=tasa.pk).exists()
        assert tasa.divisa_origen.codigo == "PYG"
        assert tasa.divisa_destino.codigo == "USD"

    def test_consultar_tasa_actual(self):
        """Verifica que consultar_tasa_actual retorna el precio base correcto."""
        tasa = TasaCambio.objects.create(
            divisa_origen=self.divisa_pyg,
            divisa_destino=self.divisa_usd,
            precio_base=Decimal("7000.000"),
            comision_compra=Decimal("10.000"),
            comision_venta=Decimal("15.000"),
            activo=True,
        )
        assert tasa.consultar_tasa_actual() == Decimal("7000.000")

    def test_unique_together_constraint(self):
        """Verifica que no se pueden crear dos tasas con la misma combinación origen/destino."""
        TasaCambio.objects.create(
            divisa_origen=self.divisa_pyg,
            divisa_destino=self.divisa_usd,
            precio_base=Decimal("7000.000"),
            comision_compra=Decimal("10.000"),
            comision_venta=Decimal("15.000"),
            activo=True,
        )
        with pytest.raises(ValidationError):
            # Debe fallar por restricción de unicidad
            TasaCambio.objects.create(
                divisa_origen=self.divisa_pyg,
                divisa_destino=self.divisa_usd,
                precio_base=Decimal("8000.000"),
                comision_compra=Decimal("20.000"),
                comision_venta=Decimal("25.000"),
                activo=True,
            )
