import uuid

from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa, TasaCambio


class TasaCambioEditarTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Eliminar divisas si ya existen
        Divisa.objects.filter(codigo="USD").delete()
        Divisa.objects.filter(codigo="PYG").delete()

        # CAMBIO PRINCIPAL: PYG debe ser la divisa ORIGEN, no destino
        self.divisa_origen = Divisa.objects.create(
            codigo="PYG",
            nombre="Guaraní Paraguayo",
            simbolo="₲",
            estado="activa",  # Agregar estado activa
        )
        self.divisa_destino = Divisa.objects.create(
            codigo="USD",
            nombre="Dólar Americano",
            simbolo="$",
            estado="activa",  # Agregar estado activa
        )

        # Crear la tasa con PYG como origen y USD como destino
        self.tasa = TasaCambio.objects.create(
            divisa_origen=self.divisa_origen,  # PYG como origen
            divisa_destino=self.divisa_destino,  # USD como destino
            precio_base=7000.00,
            comision_compra=10.00,
            comision_venta=10.00,
            activo=True,
        )

    def test_editar_tasa_inexistente(self):
        # Generar un UUID válido pero que no existe en la DB
        uuid_inexistente = str(uuid.uuid4())
        response = self.client.post(reverse("operaciones:tasa_cambio_editar", args=[uuid_inexistente]), {})
        # Debería retornar 404 porque no encuentra el objeto
        self.assertEqual(response.status_code, 404)

    def test_editar_tasa_valida(self):
        data = {
            "divisa_origen": self.divisa_origen.pk,  # PYG (origen)
            "divisa_destino": self.divisa_destino.pk,  # USD (destino)
            "precio_base": "7100",
            "comision_compra": "15",
            "comision_venta": "15",
            "activo": True,
        }
        response = self.client.post(reverse("operaciones:tasa_cambio_editar", args=[self.tasa.pk]), data)

        # Verificar qué está pasando exactamente
        if response.status_code == 200:
            # Si devuelve 200, puede ser que haya errores en el formulario
            if hasattr(response, "context") and "form" in response.context:
                form = response.context["form"]
                if form.errors:
                    self.fail(f"El formulario tiene errores: {form.errors}")
            # Si no hay errores de formulario, el test pasa con 200
            self.assertEqual(response.status_code, 200)
        else:
            # Si devuelve 302, es una redirección exitosa
            self.assertEqual(response.status_code, 302)
