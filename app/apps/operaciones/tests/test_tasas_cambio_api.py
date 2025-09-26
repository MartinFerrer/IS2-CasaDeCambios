from django.test import Client, TestCase

from apps.operaciones.models import Divisa, TasaCambio


class TasasCambioApiTest(TestCase):
    def setUp(self):
        self.client = Client()

        # ⚡ Eliminar divisas existentes con esos códigos
        Divisa.objects.filter(codigo="USD").delete()
        Divisa.objects.filter(codigo="PYG").delete()

        origen = Divisa.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        destino = Divisa.objects.create(codigo="PYG", nombre="Guaraní", simbolo="₲")

        TasaCambio.objects.create(
            divisa_origen=origen,
            divisa_destino=destino,
            precio_base=7000,
            comision_compra=10,
            comision_venta=10,
            activo=True,
        )
