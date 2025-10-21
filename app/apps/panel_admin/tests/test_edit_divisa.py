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

    def test_edit_divisa_post_valid(self):
        self.client.force_login(self.usuario_admin)
        data = {"codigo": "USD", "nombre": "US Dollar Updated", "simbolo": "$", "estado": "inactiva"}
        response = self.client.post(reverse("edit_divisa", args=[self.divisa.pk]), data)

        self.assertEqual(response.status_code, 302)
        self.divisa.refresh_from_db()
        self.assertEqual(self.divisa.nombre, "US Dollar Updated")
        self.assertEqual(self.divisa.estado, "inactiva")
        self.assertEqual(self.divisa.codigo, "USD")

    def test_edit_divisa_get_redirects(self):
        self.client.force_login(self.usuario_admin)
        response = self.client.get(reverse("edit_divisa", args=[self.divisa.pk]))
        self.assertEqual(response.status_code, 302)
