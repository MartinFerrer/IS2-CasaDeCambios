from django.test import Client, TestCase
from django.urls import reverse

from apps.operaciones.models import Divisa, TasaCambio, TasaCambioHistorial


class TasaCambioActivarDesactivarTest(TestCase):
    def setUp(self):
        self.client = Client()

        origen, _ = Divisa.objects.get_or_create(
            codigo="USD",
            defaults={
                "nombre": "Dólar",
                "simbolo": "$",
            },
        )
        destino, _ = Divisa.objects.get_or_create(
            codigo="PYG",
            defaults={
                "nombre": "Guaraní",
                "simbolo": "₲",
            },
        )

        self.tasa = TasaCambio.objects.create(
            divisa_origen=origen,
            divisa_destino=destino,
            precio_base=7000,
            comision_compra=10,
            comision_venta=10,
            activo=True,
        )

    def test_desactivar_tasa(self):
        response = self.client.post(reverse("tasa_cambio_desactivar", args=[self.tasa.pk]))
        self.assertRedirects(response, reverse("tasa_cambio_listar"))
        self.tasa.refresh_from_db()
        self.assertFalse(self.tasa.activo)
        self.assertTrue(TasaCambioHistorial.objects.filter(motivo="Desactivación de Tasa").exists())

    def test_activar_tasa(self):
        self.tasa.activo = False
        self.tasa.save()
        response = self.client.post(reverse("tasa_cambio_activar", args=[self.tasa.pk]))
        self.assertRedirects(response, reverse("tasa_cambio_listar"))
        self.tasa.refresh_from_db()
        self.assertTrue(self.tasa.activo)
        self.assertTrue(TasaCambioHistorial.objects.filter(motivo="Activación de Tasa").exists())
