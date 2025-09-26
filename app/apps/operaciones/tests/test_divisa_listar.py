from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa


class DivisaListarTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        # Crear las divisas necesarias solo una vez
        cls.divisa_destino, _ = Divisa.objects.get_or_create(
            codigo="PYG",
            defaults={"nombre": "Guaraní", "simbolo": "₲", "estado": "activa"},
        )
        cls.divisa_usd, _ = Divisa.objects.get_or_create(
            codigo="USD", defaults={"nombre": "Dólar", "simbolo": "$", "estado": "activa"}
        )
        cls.divisa_eur, _ = Divisa.objects.get_or_create(
            codigo="EUR", defaults={"nombre": "Euro", "simbolo": "€", "estado": "activa"}
        )

    def test_divisa_listar(self):
        response = self.client.get(reverse("operaciones:divisa_listar"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dólar")
        self.assertContains(response, "Euro")

        divisas = response.context["object_list"]
        # Verificar que están ordenadas por código
        self.assertEqual(
            list(divisas.values_list("codigo", flat=True)),
            sorted(divisas.values_list("codigo", flat=True)),
        )
