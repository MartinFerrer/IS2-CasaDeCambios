"""Tests unitarios para las views de clientes en panel_admin/views.py."""

import pytest
from apps.usuarios.models import Cliente, TipoCliente, Usuario
from django.urls import reverse


@pytest.mark.django_db
def test_cliente_list_view(client):
    """Verifica que la vista de lista de clientes responde correctamente y contiene los objetos esperados."""
    tipo = TipoCliente.objects.create(nombre="Tipo1")
    _usuario = Usuario.objects.create(nombre="U1", email="u1@x.com", password="p", activo=True)
    Cliente.objects.create(
        ruc="123", nombre="C1", email="c1@x.com", telefono="1234", direccion="Dir", tipo_cliente=tipo
    )
    url = reverse("cliente_listar")
    response = client.get(url)
    assert response.status_code == 200
    assert "clientes" in response.context
    assert "tipos_cliente" in response.context
    assert "usuarios" in response.context


@pytest.mark.django_db
def test_cliente_create_view(client):
    """Verifica que se puede crear un cliente mediante la vista correspondiente."""
    tipo = TipoCliente.objects.create(nombre="Tipo2")
    url = reverse("cliente_listar")
    data = {
        "ruc": "456",
        "nombre": "C2",
        "email": "c2@x.com",
        "telefono": "5678",
        "direccion": "Dir2",
        "tipo_cliente": tipo.pk,
    }
    response = client.post(url, data)
    assert response.status_code == 302
    assert Cliente.objects.filter(nombre="C2").exists()


@pytest.mark.django_db
def test_cliente_edit_view(client):
    """Verifica que se puede editar un cliente mediante la vista correspondiente."""
    tipo = TipoCliente.objects.create(nombre="Tipo3")
    cliente = Cliente.objects.create(
        ruc="789", nombre="C3", email="c3@x.com", telefono="9999", direccion="Dir3", tipo_cliente=tipo
    )
    url = reverse("cliente_editar", args=[cliente.pk])
    data = {
        "ruc": "789",
        "nombre": "C3-editado",
        "email": "c3@x.com",
        "telefono": "9999",
        "direccion": "Dir3",
        "tipo_cliente": tipo.pk,
    }
    response = client.post(url, data)
    assert response.status_code == 302
    cliente.refresh_from_db()
    assert cliente.nombre == "C3-editado"


@pytest.mark.django_db
def test_cliente_delete_view(client):
    """Verifica que se puede eliminar un cliente mediante la vista correspondiente."""
    tipo = TipoCliente.objects.create(nombre="Tipo4")
    cliente = Cliente.objects.create(
        ruc="000", nombre="C4", email="c4@x.com", telefono="0000", direccion="Dir4", tipo_cliente=tipo
    )
    url = reverse("cliente_eliminar", args=[cliente.pk])
    response = client.post(url)
    assert response.status_code == 302
    assert not Cliente.objects.filter(pk=cliente.pk).exists()
