from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa
from apps.usuarios.models import Usuario


class DivisaDetailTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.divisa = Divisa.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        # Crear grupo y usuario administrador para las pruebas
        self.grupo_admin = Group.objects.get_or_create(name="Administrador")[0]
        self.usuario_admin = Usuario.objects.create(
            email="admin@test.com", nombre="Admin Test", password="testpass", activo=True
        )
        self.usuario_admin.groups.add(self.grupo_admin)

    def test_divisa_detail_existente(self):
        self.client.force_login(self.usuario_admin)
        response = self.client.get(reverse("divisa_detail", args=[self.divisa.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dólar")

    def test_divisa_detail_inexistente(self):
        self.client.force_login(self.usuario_admin)
        response = self.client.get(reverse("divisa_detail", args=[999]))
        self.assertEqual(response.status_code, 404)
