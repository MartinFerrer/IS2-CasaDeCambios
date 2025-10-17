"""Pruebas de restricciones de pago en efectivo para compras de divisas."""

from apps.transacciones.views import _compute_simulation
from apps.usuarios.models import Cliente, TipoCliente
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.test import TestCase

User = get_user_model()


class TestCashPaymentRestriction(TestCase):
    """Casos de prueba para restricciones de pago en efectivo en transacciones de divisas."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

        # Crear TipoCliente
        self.tipo_cliente = TipoCliente.objects.create(nombre="Cliente Regular", descuento_sobre_comision=0)

        # Crear Cliente
        self.cliente = Cliente.objects.create(
            user=self.user, nombre="Cliente Test", cedula="12345678", tipo_cliente=self.tipo_cliente
        )

    def test_compute_simulation_cash_purchase_restriction(self):
        """Prueba que _compute_simulation lanza ValueError para compra en efectivo."""
        # Crear objeto request con atributo cliente (simulando middleware)
        request = HttpRequest()
        request.user = self.user
        request.cliente = self.cliente

        # Parámetros para compra en efectivo (debe estar restringida)
        params = {
            "monto": "100",
            "divisa_seleccionada": "USD",
            "tipo_operacion": "compra",
            "metodo_pago": "efectivo",
            "metodo_cobro": "efectivo",
        }

        # Debe lanzar ValueError
        with self.assertRaises(ValueError) as cm:
            _compute_simulation(params, request)

        self.assertIn("No se permite comprar divisas usando efectivo", str(cm.exception))

    def test_compute_simulation_cash_sale_allowed(self):
        """Prueba que _compute_simulation permite ventas en efectivo."""
        # Crear objeto request con atributo cliente (simulando middleware)
        request = HttpRequest()
        request.user = self.user
        request.cliente = self.cliente

        # Parámetros para venta en efectivo (debe estar permitida)
        params = {
            "monto": "100",
            "divisa_seleccionada": "USD",
            "tipo_operacion": "venta",
            "metodo_pago": "efectivo",
            "metodo_cobro": "efectivo",
        }

        # No debe lanzar ValueError
        try:
            result = _compute_simulation(params, request)
            self.assertIn("tipo_operacion", result)
            self.assertEqual(result["tipo_operacion"], "venta")
        except ValueError:
            self.fail("Las ventas en efectivo deben estar permitidas")

    def test_compute_simulation_card_purchase_allowed(self):
        """Prueba que _compute_simulation permite compras con tarjeta."""
        # Crear objeto request con atributo cliente (simulando middleware)
        request = HttpRequest()
        request.user = self.user
        request.cliente = self.cliente

        # Parámetros para compra con tarjeta (debe estar permitida)
        params = {
            "monto": "100",
            "divisa_seleccionada": "USD",
            "tipo_operacion": "compra",
            "metodo_pago": "tarjeta_1",
            "metodo_cobro": "efectivo",
        }

        # No debe lanzar ValueError
        try:
            result = _compute_simulation(params, request)
            self.assertIn("tipo_operacion", result)
            self.assertEqual(result["tipo_operacion"], "compra")
        except ValueError:
            self.fail("Las compras con tarjeta deben estar permitidas")
