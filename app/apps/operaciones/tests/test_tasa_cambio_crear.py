from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa, TasaCambio


class TasaCambioCrearTest(TestCase):
    def setUp(self):
        self.client = Client()
        Divisa.objects.all().delete()

        # Crear PYG como divisa origen (obligatorio según tu formulario)
        self.divisa_origen = Divisa.objects.create(
            codigo="PYG", nombre="Guaraní Paraguayo", simbolo="₲", estado="activa"
        )

        # Crear divisa destino
        self.divisa_destino = Divisa.objects.create(
            codigo="USD", nombre="Dólar Americano", simbolo="$", estado="activa"
        )

    def test_crear_tasa_valida(self):
        # Usar los nombres de campos correctos del formulario
        data = {
            "divisa_origen": self.divisa_origen.pk,
            "divisa_destino": self.divisa_destino.pk,
            "precio_base": "7000",
            "comision_compra": "100",
            "comision_venta": "100",
            "activo": True,
        }

        response = self.client.post(reverse("operaciones:crear_tasa"), data)

        # Verificar que la respuesta sea exitosa (302 = redirección o 200 = OK)
        self.assertIn(response.status_code, [200, 302])

        # Verificar que se creó la tasa con los campos correctos
        self.assertTrue(
            TasaCambio.objects.filter(divisa_origen=self.divisa_origen, divisa_destino=self.divisa_destino).exists()
        )

    def test_crear_tasa_invalida(self):
        # Usar valores inválidos (precio_base negativo)
        data = {
            "divisa_origen": self.divisa_origen.pk,
            "divisa_destino": self.divisa_destino.pk,
            "precio_base": "-100",  # Valor negativo (inválido)
            "comision_compra": "100",
            "comision_venta": "100",
            "activo": True,
        }

        response = self.client.post(reverse("operaciones:crear_tasa"), data)

        # Debe retornar 200 (formulario con errores) no 302 (redirección exitosa)
        self.assertEqual(response.status_code, 200)

        # No debe haberse creado ninguna tasa con precio_base negativo
        self.assertFalse(TasaCambio.objects.filter(precio_base=-100).exists())
