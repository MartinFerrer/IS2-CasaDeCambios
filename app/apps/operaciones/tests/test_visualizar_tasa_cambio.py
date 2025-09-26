"""Pruebas para el endpoint tasas_cambio_api."""

import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
def test_tasas_cambio_api(client):
    """Prueba el endpoint tasas_cambio_api para asegurar que devuelve las tasas de cambio correctamente."""
    # Crear divisas base y destino
    pyg = baker.make("operaciones.Divisa", codigo="PYG", nombre="Guaraní", simbolo="₲")
    usd = baker.make("operaciones.Divisa", codigo="USD", nombre="Dólar", simbolo="$")
    # Crear tasa activa
    _tasa = baker.make(
        "operaciones.TasaCambio",
        divisa_origen=pyg,
        divisa_destino=usd,
        precio_base=7000,
        comision_compra=50,
        comision_venta=60,
        activo=True,
    )
    url = reverse("operaciones:tasas_cambio_api")
    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert "tasas" in data
    assert data["total"] == 1
    tasa_data = data["tasas"][0]
    assert tasa_data["divisa"]["codigo"] == "USD"
    assert "precio_compra" in tasa_data
    assert "precio_venta" in tasa_data
    assert "fecha_actualizacion" in tasa_data
