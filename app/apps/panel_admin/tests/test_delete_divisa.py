from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa
from apps.usuarios.models import Usuario


class DivisaViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.grupo_admin, _ = Group.objects.get_or_create(name="Administrador")
        self.usuario_admin = Usuario.objects.create_user(
            email="admin@test.com", password="password", nombre="Admin User"
        )
        self.usuario_admin.groups.add(self.grupo_admin)
        self.divisa_data = {"codigo": "USD", "nombre": "US Dollar", "simbolo": "$", "estado": "activa"}
        self.divisa = Divisa.objects.create(**self.divisa_data)

    def test_delete_divisa_post(self):
        self.client.force_login(self.usuario_admin)
        response = self.client.post(reverse("delete_divisa", args=[self.divisa.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Divisa.objects.filter(pk=self.divisa.pk).exists())

    def test_delete_divisa_get_redirects(self):
        self.client.force_login(self.usuario_admin)
        response = self.client.get(reverse("delete_divisa", args=[self.divisa.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Divisa.objects.filter(pk=self.divisa.pk).exists())
