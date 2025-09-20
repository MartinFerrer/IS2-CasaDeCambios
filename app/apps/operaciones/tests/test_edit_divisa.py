from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa


class DivisaViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.divisa_data = {"codigo": "USD", "nombre": "US Dollar", "simbolo": "$", "estado": "activa"}
        self.divisa = Divisa.objects.create(**self.divisa_data)

    def test_edit_divisa_post_valid(self):
        data = {"codigo": "USD", "nombre": "US Dollar Updated", "simbolo": "$", "estado": "inactiva"}
        response = self.client.post(reverse("operaciones:edit_divisa", args=[self.divisa.pk]), data)

        self.assertEqual(response.status_code, 302)
        self.divisa.refresh_from_db()
        self.assertEqual(self.divisa.nombre, "US Dollar Updated")
        self.assertEqual(self.divisa.estado, "inactiva")
        self.assertEqual(self.divisa.codigo, "USD")

    def test_edit_divisa_get_redirects(self):
        response = self.client.get(reverse("operaciones:edit_divisa", args=[self.divisa.pk]))
        self.assertEqual(response.status_code, 302)
