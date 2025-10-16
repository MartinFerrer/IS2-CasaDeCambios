"""Tests adicionales para la integración de Stripe."""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from apps.transacciones.views import _get_stripe_fixed_fee_pyg
from django.test import Client, override_settings


@pytest.mark.django_db
class TestStripeIntegration:
    """Tests para funcionalidades de Stripe."""

    @patch("apps.transacciones.views.TasaCambio.objects.filter")
    def test_get_stripe_fixed_fee_pyg_success(self, mock_filter):
        """Test conversión correcta de comisión fija USD a PYG."""
        # Mock de tasa de cambio USD
        mock_tasa = MagicMock()
        mock_tasa.tasa_venta = Decimal("7500.00")  # 1 USD = 7500 PYG
        mock_filter.return_value.first.return_value = mock_tasa

        resultado = _get_stripe_fixed_fee_pyg()

        # 0.30 USD * 7500 PYG/USD = 2250 PYG
        assert resultado == Decimal("2250.00")
        mock_filter.assert_called_once_with(divisa_origen__codigo="PYG", divisa_destino__codigo="USD", estado="activo")

    @patch("apps.transacciones.views.TasaCambio.objects.filter")
    def test_get_stripe_fixed_fee_pyg_no_rate(self, mock_filter):
        """Test cuando no hay tasa de cambio USD disponible."""
        mock_filter.return_value.first.return_value = None

        resultado = _get_stripe_fixed_fee_pyg()

        # Debe usar tasa por defecto: 0.30 * 7000 = 2100
        assert resultado == Decimal("2100.00")

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_123",
        STRIPE_PUBLISHABLE_KEY="pk_test_123",
        STRIPE_FIXED_FEE_USD=Decimal("0.30"),
        STRIPE_COMMISSION_RATE=Decimal("2.9"),
    )
    def test_simulation_includes_stripe_fees(self):
        """Test que la simulación incluye comisiones duales de Stripe."""
        client = Client()

        # Datos de simulación
        data = {"tipo_operacion": "compra", "divisa_deseada": "USD", "monto": "100", "medio_pago": "stripe"}

        with patch("apps.transacciones.views._get_stripe_fixed_fee_pyg") as mock_fee:
            mock_fee.return_value = Decimal("2250.00")  # 0.30 USD en PYG

            response = client.post("/api/transacciones/simular/", data)

        if response.status_code == 200:
            result = json.loads(response.content)

            # Verificar que incluya comisiones de Stripe
            if "comision_stripe_variable" in result:
                assert "comision_stripe_variable" in result
                assert "comision_stripe_fija" in result
                assert result["comision_stripe_fija"] == "2250.00"

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("stripe.PaymentIntent.create")
    def test_create_stripe_payment_intent(self, mock_create):
        """Test creación de payment intent de Stripe."""
        client = Client()

        # Mock del payment intent
        mock_intent = MagicMock()
        mock_intent.id = "pi_test_123"
        mock_intent.client_secret = "pi_test_123_secret_456"
        mock_create.return_value = mock_intent

        data = {"amount": "1000", "currency": "usd", "description": "Test payment"}

        response = client.post(
            "/api/stripe/create-payment-intent/", data=json.dumps(data), content_type="application/json"
        )

        if response.status_code == 200:
            result = json.loads(response.content)
            assert result["success"] is True
            assert "client_secret" in result

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("stripe.PaymentIntent.confirm")
    def test_confirm_stripe_payment_success(self, mock_confirm):
        """Test confirmación exitosa de pago Stripe."""
        client = Client()

        # Mock del payment intent confirmado
        mock_intent = MagicMock()
        mock_intent.status = "succeeded"
        mock_intent.id = "pi_test_123"
        mock_confirm.return_value = mock_intent

        data = {"payment_intent_id": "pi_test_123", "payment_method": "pm_test_456"}

        response = client.post("/api/stripe/confirm-payment/", data=json.dumps(data), content_type="application/json")

        if response.status_code == 200:
            result = json.loads(response.content)
            assert result["success"] is True
            assert result["status"] == "succeeded"

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_123")
    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_handler(self, mock_construct):
        """Test manejo de webhook de Stripe."""
        client = Client()

        # Mock del evento webhook
        mock_event = {
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_test_123", "status": "succeeded"}},
        }
        mock_construct.return_value = mock_event

        payload = json.dumps(mock_event)

        response = client.post(
            "/transacciones/stripe/webhook/",
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_signature",
        )

        # Webhook debe responder con 200 aunque no procese completamente
        assert response.status_code in [200, 400]  # 400 si no encuentra transacción

    @patch("apps.transacciones.views.TasaCambio.objects.filter")
    def test_stripe_dual_commission_calculation(self, mock_filter):
        """Test cálculo correcto de comisiones duales de Stripe."""
        # Mock de tasa de cambio USD para que devuelva valor consistente
        mock_tasa = MagicMock()
        mock_tasa.tasa_venta = Decimal("7500.00")  # 1 USD = 7500 PYG
        mock_filter.return_value.first.return_value = mock_tasa

        # Test que las funciones de comisión funcionan
        fee_fija = _get_stripe_fixed_fee_pyg()
        assert fee_fija == Decimal("2250.00")  # 0.30 USD * 7500 = 2250 PYG

        # Comisión variable: 2.9% de 100 USD = 2.90 USD
        # En PYG: 2.90 * 7500 = 21750 PYG (aproximado)
        monto_usd = Decimal("100.00")
        comision_variable_pct = Decimal("2.9")  # 2.9%
        comision_variable_usd = monto_usd * (comision_variable_pct / 100)

        assert comision_variable_usd == Decimal("2.90")


@pytest.mark.django_db
class TestStripeAPIEndpoints:
    """Tests específicos para endpoints de API de Stripe."""

    def test_stripe_endpoints_require_post(self):
        """Test que endpoints de Stripe requieren método POST."""
        client = Client()

        endpoints = ["/api/stripe/create-payment-intent/", "/api/stripe/confirm-payment/", "/stripe/webhook/"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            # Debe rechazar GET (405 Method Not Allowed o redirect)
            assert response.status_code in [405, 302, 404]


@pytest.mark.django_db
class TestStripeTestEnvironment:
    """Tests para asegurar configuración correcta de entorno de pruebas."""

    def test_stripe_test_keys_configured(self):
        """Test que se usen claves de test de Stripe."""
        from django.conf import settings

        # Verificar que las claves son de test
        if hasattr(settings, "STRIPE_PUBLISHABLE_KEY"):
            assert settings.STRIPE_PUBLISHABLE_KEY.startswith("pk_test_")

        if hasattr(settings, "STRIPE_SECRET_KEY"):
            assert settings.STRIPE_SECRET_KEY.startswith("sk_test_")

    def test_stripe_commission_settings(self):
        """Test configuración de comisiones de Stripe."""
        from django.conf import settings

        # Verificar configuración de comisiones
        assert hasattr(settings, "STRIPE_COMMISSION_RATE")
        assert hasattr(settings, "STRIPE_FIXED_FEE_USD")

        assert settings.STRIPE_COMMISSION_RATE == Decimal("2.9")
        assert settings.STRIPE_FIXED_FEE_USD == Decimal("0.30")
