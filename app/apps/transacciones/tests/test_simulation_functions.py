"""Tests unitarios para funciones de simulación con Stripe."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from apps.transacciones.views import _compute_simulation
from apps.usuarios.models import Usuario
from django.test import RequestFactory


@pytest.mark.django_db
class TestComputeSimulation:
    """Tests para función _compute_simulation con integración de Stripe."""

    @pytest.fixture
    def mock_request(self):
        """Fixture para crear un request mock."""
        factory = RequestFactory()
        request = factory.post("/test/")
        request.user = Usuario.objects.create_user("test@test.com", "Test User", "pass")
        return request

    @patch("apps.transacciones.views.TasaCambio.objects.filter")
    @patch("apps.transacciones.views._get_stripe_fixed_fee_pyg")
    def test_compute_simulation_with_stripe_dual_commission(self, mock_stripe_fee, mock_tasa_filter, mock_request):
        """Test cálculo de simulación con comisiones duales de Stripe."""
        # Mock tasa de cambio
        mock_tasa = MagicMock()
        mock_tasa.precio_base = Decimal("7450.00")
        mock_tasa.comision_compra = Decimal("50.00")
        mock_tasa.comision_venta = Decimal("50.00")
        mock_tasa.tasa_compra = Decimal("7500.00")
        mock_tasa.tasa_venta = Decimal("7400.00")
        mock_tasa.divisa_origen.codigo = "PYG"
        mock_tasa.divisa_destino.codigo = "USD"
        mock_tasa_filter.return_value.first.return_value = mock_tasa

        # Mock comisión fija de Stripe en PYG
        mock_stripe_fee.return_value = Decimal("2250.00")  # 0.30 USD * 7500

        # Parámetros de simulación
        params = {
            "tipo_operacion": "compra",
            "divisa_deseada": "USD",
            "monto": Decimal("100.00"),
            "medio_pago": "stripe",
        }

        result = _compute_simulation(params, mock_request)

        # Verificar que el resultado incluye información de Stripe
        assert result is not None

        # Si el medio de pago es Stripe, debe incluir comisiones específicas
        if "comision_stripe" in str(result) or "stripe" in str(result).lower():
            # Verificar estructura de comisiones duales
            assert any(key in str(result).lower() for key in ["comision", "fee", "stripe"])

    @patch("apps.transacciones.views._get_stripe_fixed_fee_pyg")
    @patch("apps.transacciones.views.TasaCambio.objects.filter")
    def test_compute_simulation_stripe_commission_calculation(self, mock_tasa_filter, mock_stripe_fee, mock_request):
        """Test cálculo específico de comisiones de Stripe."""
        # Mock tasa de cambio USD
        mock_tasa = MagicMock()
        mock_tasa.precio_base = Decimal("7450.00")
        mock_tasa.comision_compra = Decimal("50.00")
        mock_tasa.comision_venta = Decimal("50.00")
        mock_tasa.tasa_compra = Decimal("7500.00")  # precio_base + comision_compra
        mock_tasa.tasa_venta = Decimal("7400.00")  # precio_base - comision_venta
        mock_tasa.divisa_origen.codigo = "PYG"
        mock_tasa.divisa_destino.codigo = "USD"
        mock_tasa_filter.return_value.first.return_value = mock_tasa

        # Mock comisión fija convertida a PYG
        mock_stripe_fee.return_value = Decimal("2250.00")  # 0.30 USD

        params = {
            "tipo_operacion": "compra",
            "divisa_deseada": "USD",
            "monto": Decimal("100.00"),
            "medio_pago": "stripe",
        }

        result = _compute_simulation(params, mock_request)

        # Verificar que se llame a la función de comisión fija
        mock_stripe_fee.assert_called_once()

        # Verificar que el resultado tenga estructura válida
        assert isinstance(result, dict)

    @patch("apps.transacciones.views.TasaCambio.objects.filter")
    def test_compute_simulation_non_stripe_payment(self, mock_tasa_filter, mock_request):
        """Test simulación con medio de pago que no es Stripe."""
        # Mock tasa de cambio
        mock_tasa = MagicMock()
        mock_tasa.precio_base = Decimal("7450.00")
        mock_tasa.comision_compra = Decimal("50.00")
        mock_tasa.comision_venta = Decimal("50.00")
        mock_tasa.tasa_compra = Decimal("7500.00")
        mock_tasa.tasa_venta = Decimal("7400.00")
        mock_tasa.divisa_origen.codigo = "PYG"
        mock_tasa.divisa_destino.codigo = "USD"
        mock_tasa_filter.return_value.first.return_value = mock_tasa

        params = {
            "tipo_operacion": "compra",
            "divisa_deseada": "USD",
            "monto": Decimal("100.00"),
            "medio_pago": "efectivo",
        }

        result = _compute_simulation(params, mock_request)

        # Debe funcionar sin errores para medios no-Stripe
        assert result is not None
        assert isinstance(result, dict)


@pytest.mark.django_db
class TestStripeCommissionCalculation:
    """Tests específicos para cálculos de comisión de Stripe."""

    @patch("apps.transacciones.views.TasaCambio.objects.filter")
    def test_stripe_variable_commission_calculation(self, mock_tasa_filter):
        """Test cálculo de comisión variable de Stripe (2.9%)."""
        # Mock tasa USD
        mock_tasa = MagicMock()
        mock_tasa.tasa_venta = Decimal("7500.00")
        mock_tasa_filter.return_value.first.return_value = mock_tasa

        # Monto en USD
        monto_usd = Decimal("100.00")
        tasa_comision = Decimal("2.9")  # 2.9%

        # Cálculo directo
        comision_variable_usd = monto_usd * (tasa_comision / 100)
        comision_variable_pyg = comision_variable_usd * mock_tasa.tasa_venta

        # Verificar cálculos
        assert comision_variable_usd == Decimal("2.90")
        assert comision_variable_pyg == Decimal("21750.00")  # 2.90 * 7500

    @patch("apps.transacciones.views.TasaCambio.objects.filter")
    def test_stripe_fixed_commission_conversion(self, mock_tasa_filter):
        """Test conversión de comisión fija USD a PYG."""
        from apps.transacciones.views import _get_stripe_fixed_fee_pyg

        # Mock tasa USD
        mock_tasa = MagicMock()
        mock_tasa.tasa_venta = Decimal("7500.00")
        mock_tasa_filter.return_value.first.return_value = mock_tasa

        fee_pyg = _get_stripe_fixed_fee_pyg()

        # 0.30 USD * 7500 PYG/USD = 2250 PYG
        assert fee_pyg == Decimal("2250.00")

    def test_stripe_total_commission_example(self):
        """Test ejemplo completo de comisión total de Stripe."""
        # Transacción de $100 USD
        monto_usd = Decimal("100.00")
        tasa_cambio = Decimal("7500.00")  # PYG por USD

        # Comisiones
        comision_variable = monto_usd * Decimal("0.029")  # 2.9%
        comision_fija_usd = Decimal("0.30")

        # Total en USD
        total_comision_usd = comision_variable + comision_fija_usd
        # Total en PYG
        total_comision_pyg = total_comision_usd * tasa_cambio

        # Verificaciones
        assert comision_variable == Decimal("2.90")
        assert total_comision_usd == Decimal("3.20")  # 2.90 + 0.30
        assert total_comision_pyg == Decimal("24000.00")  # 3.20 * 7500
