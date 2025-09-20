from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa


class DivisaViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.divisa_data = {"codigo": "USD", "nombre": "US Dollar", "simbolo": "$", "estado": "activa"}
        self.divisa = Divisa.objects.create(**self.divisa_data)

    def test_delete_divisa_post(self):
        response = self.client.post(reverse("operaciones:delete_divisa", args=[self.divisa.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Divisa.objects.filter(pk=self.divisa.pk).exists())

    def test_delete_divisa_get_redirects(self):
        response = self.client.get(reverse("operaciones:delete_divisa", args=[self.divisa.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Divisa.objects.filter(pk=self.divisa.pk).exists())
