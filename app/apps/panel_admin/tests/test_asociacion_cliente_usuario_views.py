"""Tests unitarios para las views de asociación cliente-usuario en panel_admin/views.py."""

import pytest
from apps.usuarios.models import Cliente, TipoCliente, Usuario
from django.urls import reverse


@pytest.mark.django_db
def test_asociar_cliente_usuario_form_view(client):
    """Verifica que la vista de formulario de asociación responde correctamente y contiene los objetos esperados."""
    tipo = TipoCliente.objects.create(nombre="TipoA")
    _usuario = Usuario.objects.create(nombre="U1", email="u1@x.com", password="p", activo=True)
    Cliente.objects.create(
        ruc="80000005-5", nombre="C1", email="c1@x.com", telefono="1234", direccion="Dir", tipo_cliente=tipo
    )
    url = reverse("asociar_cliente_usuario_form")
    response = client.get(url)
    assert response.status_code == 200
    assert "clientes" in response.context
    assert "usuarios" in response.context


@pytest.mark.django_db
def test_asociar_cliente_usuario_post_view(client):
    """Verifica que se puede asociar un cliente a un usuario mediante la vista correspondiente."""
    tipo = TipoCliente.objects.create(nombre="TipoB")
    usuario = Usuario.objects.create(nombre="U2", email="u2@x.com", password="p", activo=True)
    cliente = Cliente.objects.create(
        ruc="80000006-4", nombre="C2", email="c2@x.com", telefono="5678", direccion="Dir2", tipo_cliente=tipo
    )
    url = reverse("asociar_cliente_usuario_post", args=[usuario.pk])
    data = {"cliente_id": cliente.pk}
    response = client.post(url, data)
    assert response.status_code == 302
    assert usuario in cliente.usuarios.all()


@pytest.mark.django_db
def test_desasociar_cliente_usuario_view(client):
    """Verifica que se puede desasociar un cliente de un usuario mediante la vista correspondiente."""
    tipo = TipoCliente.objects.create(nombre="TipoC")
    usuario = Usuario.objects.create(nombre="U3", email="u3@x.com", password="p", activo=True)
    cliente = Cliente.objects.create(
        ruc="80000007-3", nombre="C3", email="c3@x.com", telefono="9999", direccion="Dir3", tipo_cliente=tipo
    )
    cliente.usuarios.add(usuario)
    url = reverse("desasociar_cliente_usuario", args=[usuario.pk])
    data = {"cliente_id": cliente.pk}
    response = client.post(url, data)
    assert response.status_code == 302
    assert usuario not in cliente.usuarios.all()
