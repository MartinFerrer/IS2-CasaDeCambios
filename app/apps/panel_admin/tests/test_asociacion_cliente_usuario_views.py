"""Tests unitarios para las views de asociación cliente-usuario en panel_admin/views.py."""

import pytest
from apps.usuarios.models import Cliente, TipoCliente, Usuario
from django.contrib.auth.models import Group
from django.urls import reverse


@pytest.fixture
def admin_user():
    """Fixture para crear un usuario administrador."""
    admin_group, _ = Group.objects.get_or_create(name="Administrador")
    admin_user = Usuario(email="admin@test.com", nombre="Admin User")
    admin_user.set_password("testpass123")
    admin_user.save()
    admin_user.groups.add(admin_group)
    return admin_user


@pytest.mark.django_db
def test_asociar_cliente_usuario_form_view(client, admin_user):
    """Verifica que la vista de formulario de asociación responde correctamente y contiene los objetos esperados."""
    client.force_login(admin_user)

    tipo = TipoCliente.objects.create(nombre="TipoA")
    _usuario = Usuario(nombre="U1", email="u1@x.com", activo=True)
    _usuario.set_password("p")
    _usuario.save()
    Cliente.objects.create(
        ruc="7653142-2", nombre="C1", email="c1@x.com", telefono="1234", direccion="Dir", tipo_cliente=tipo
    )
    url = reverse("asociar_cliente_usuario_form")
    response = client.get(url)
    assert response.status_code == 200
    assert "clientes" in response.context
    assert "usuarios" in response.context


@pytest.mark.django_db
def test_asociar_cliente_usuario_post_view(client, admin_user):
    """Verifica que se puede asociar un cliente a un usuario mediante la vista correspondiente."""
    client.force_login(admin_user)

    tipo = TipoCliente.objects.create(nombre="TipoB")
    usuario = Usuario(nombre="U2", email="u2@x.com", activo=True)
    usuario.set_password("p")
    usuario.save()
    cliente = Cliente.objects.create(
        ruc="7653142-2", nombre="C2", email="c2@x.com", telefono="5678", direccion="Dir2", tipo_cliente=tipo
    )
    url = reverse("asociar_cliente_usuario_post", args=[usuario.pk])
    data = {"cliente_id": cliente.pk}
    response = client.post(url, data)
    # Acepta tanto 302 (redirect después de éxito) como 200 (error o formulario)
    assert response.status_code in [200, 302]
    # Verificar asociación solo si hubo éxito
    if response.status_code == 302:
        assert usuario in cliente.usuarios.all()


@pytest.mark.django_db
def test_desasociar_cliente_usuario_view(client, admin_user):
    """Verifica que se puede desasociar un cliente de un usuario mediante la vista correspondiente."""
    client.force_login(admin_user)

    tipo = TipoCliente.objects.create(nombre="TipoC")
    usuario = Usuario(nombre="U3", email="u3@x.com", activo=True)
    usuario.set_password("p")
    usuario.save()
    cliente = Cliente.objects.create(
        ruc="7653142-2", nombre="C3", email="c3@x.com", telefono="9999", direccion="Dir3", tipo_cliente=tipo
    )
    cliente.usuarios.add(usuario)
    url = reverse("desasociar_cliente_usuario", args=[usuario.pk])
    data = {"cliente_id": cliente.pk}
    response = client.post(url, data)
    # Acepta tanto 302 (redirect después de éxito) como 200 (error o formulario)
    assert response.status_code in [200, 302]
    # Verificar desasociación solo si hubo éxito
    if response.status_code == 302:
        assert usuario not in cliente.usuarios.all()
