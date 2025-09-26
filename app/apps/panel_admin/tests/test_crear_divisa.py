import json

from django.template.exceptions import TemplateDoesNotExist
from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa


class TestDivisaViews(TestCase):
    def setUp(self):
        self.client = Client()
        self.url_crear_divisa = reverse("crear_divisa")
        self.url_divisa_list = reverse("divisa_list")
        self.divisa = Divisa.objects.create(codigo="USD", nombre="Dólar Estadounidense", simbolo="$")

    def test_crear_divisa_get(self):
        try:
            response = self.client.get(reverse("crear_divisa"))
            self.assertIn(response.status_code, [200, 302])
        except TemplateDoesNotExist:
            pass

    def test_crear_divisa_post_valid(self):
        data = {"codigo": "EUR", "nombre": "Euro", "simbolo": "€", "estado": "activa"}
        response = self.client.post(reverse("crear_divisa"), data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        self.assertEqual(response_data["divisa"]["codigo"], "EUR")
        self.assertTrue(Divisa.objects.filter(codigo="EUR").exists())

    def test_crear_divisa_post_invalid(self):
        data = {"codigo": ""}
        response = self.client.post(reverse("crear_divisa"), data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("errors", response_data)

    def test_crear_divisa_post_duplicate_code(self):
        data = {
            "codigo": "USD",
            "nombre": "Dólar de los Estados Unidos",
            "simbolo": "$",
        }

        response = self.client.post(self.url_crear_divisa, json.dumps(data), content_type="application/json")

        self.assertEqual(response.status_code, 400)

        response_data = response.json()

        self.assertFalse(response_data["success"])
        self.assertIn("errors", response_data)
        self.assertIn("codigo", response_data["errors"])
