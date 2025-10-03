from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa


class DivisaDetailTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.divisa = Divisa.objects.create(codigo="USD", nombre="Dólar", simbolo="$")

    def test_divisa_detail_existente(self):
        response = self.client.get(reverse("operaciones:divisa_detail", args=[self.divisa.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dólar")

    def test_divisa_detail_inexistente(self):
        response = self.client.get(reverse("operaciones:divisa_detail", args=[999]))
        self.assertEqual(response.status_code, 404)
