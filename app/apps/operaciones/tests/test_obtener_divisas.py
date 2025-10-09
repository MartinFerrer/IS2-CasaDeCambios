import json

from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa
from apps.usuarios.models import Usuario


class ObtenerDivisasTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Crear divisas mínimas para evitar errores
        Divisa.objects.get_or_create(
            codigo="PYG",
            defaults={"nombre": "Guaraní", "simbolo": "₲", "estado": "activa"},
        )
        Divisa.objects.get_or_create(
            codigo="USD",
            defaults={"nombre": "Dólar", "simbolo": "$", "estado": "activa"},
        )
        # Crear grupo y usuario administrador para las pruebas
        self.grupo_admin = Group.objects.get_or_create(name="Administrador")[0]
        self.usuario_admin = Usuario.objects.create(
            email="admin@test.com", nombre="Admin Test", password="testpass", activo=True
        )
        self.usuario_admin.groups.add(self.grupo_admin)

    def test_obtener_divisas_json(self):
        self.client.force_login(self.usuario_admin)
        response = self.client.get(reverse("api_divisas"))
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)  # 👈 asegura que devuelve algo
        self.assertTrue(all("codigo" in d and "nombre" in d and "simbolo" in d for d in data))
