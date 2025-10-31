from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa
from apps.usuarios.models import Usuario


class DivisaListarTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        # Crear grupo y usuario administrador para las pruebas
        cls.grupo_admin = Group.objects.get_or_create(name="Administrador")[0]
        cls.usuario_admin = Usuario.objects.create(
            email="admin@test.com", nombre="Admin Test", password="testpass", activo=True
        )
        cls.usuario_admin.groups.add(cls.grupo_admin)

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
        # Login con el usuario administrador
        self.client.force_login(self.usuario_admin)
        response = self.client.get(reverse("divisa_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dólar")
        self.assertContains(response, "Euro")

        divisas = response.context["object_list"]
        # Verificar que están ordenadas por código
        self.assertEqual(
            list(divisas.values_list("codigo", flat=True)),
            sorted(divisas.values_list("codigo", flat=True)),
        )
