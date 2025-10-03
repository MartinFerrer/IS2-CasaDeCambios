from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa, TasaCambio
from apps.usuarios.models import Usuario


class TasaCambioListarTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        # Create admin user for authentication
        cls.grupo_admin = Group.objects.get_or_create(name="Administrador")[0]
        cls.usuario_admin = Usuario.objects.create(
            email="admin@test.com", nombre="Admin Test", password="testpass", activo=True
        )
        cls.usuario_admin.groups.add(cls.grupo_admin)

        # Crear divisas base (o recuperarlas si ya existen)
        cls.pyg, _ = Divisa.objects.get_or_create(
            codigo="PYG",
            defaults={"nombre": "Guaraní", "simbolo": "₲", "estado": "activa"},
        )
        cls.usd, _ = Divisa.objects.get_or_create(
            codigo="USD",
            defaults={"nombre": "Dólar", "simbolo": "$", "estado": "activa"},
        )

        # Crear tasa válida (PYG ↔ USD) solo si no existe
        TasaCambio.objects.get_or_create(
            divisa_origen=cls.pyg,
            divisa_destino=cls.usd,
            defaults={
                "precio_base": Decimal("7000.000"),
                "comision_compra": Decimal("10.000"),
                "comision_venta": Decimal("10.000"),
                "activo": True,
            },
        )

    def test_tasa_cambio_listar(self):
        response = self.client.get(reverse("tasa_cambio_listar"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("tasas_de_cambio", response.context)
