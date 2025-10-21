"""Testeos Unitarios para la configuración de descuento sobre comisión para cada TipoCliente."""

from decimal import Decimal

import pytest
from apps.usuarios.models import TipoCliente, Usuario
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.usuarios.models import TipoCliente


@pytest.mark.django_db
class TestPanelAdminConfiguracion:
    """Testeos Unitarios para la configuración de descuento sobre comisión para cada TipoCliente."""

    @pytest.fixture(autouse=True)
    def setup(self, client):
        """Realizar setup para testeos unitarios, Creamos 3 tipos de cliente con valores conocidos."""
        # Crear grupo administrador
        admin_group, _ = Group.objects.get_or_create(name="Administrador")

        # Crear usuario administrador
        self.admin_user = Usuario(email="admin@test.com", nombre="Admin User")
        self.admin_user.set_password("testpass123")
        self.admin_user.save()
        self.admin_user.groups.add(admin_group)

        # Autenticar para todas las pruebas
        client.force_login(self.admin_user)

        # Crear tipos de cliente
        self.minorista, _ = TipoCliente.objects.update_or_create(
            nombre="Minorista", defaults={"descuento_sobre_comision": Decimal("0.0")}
        )
        self.corporativo, _ = TipoCliente.objects.update_or_create(
            nombre="Corporativo", defaults={"descuento_sobre_comision": Decimal("5.0")}
        )
        self.vip, _ = TipoCliente.objects.update_or_create(
            nombre="VIP", defaults={"descuento_sobre_comision": Decimal("10.0")}
        )

    def test_configuracion_view_renderiza_inputs_con_valores(self, client):
        """La vista configuracion debe renderizar inputs para cada TipoCliente con su value."""
        url = reverse("configuracion")
        resp = client.get(url)
        assert resp.status_code == 200

        content = resp.content

        # Buscamos los inputs por name (usando pk) y que el value contenga el valor esperado
        # El template usa strip_trailing_zeros que elimina decimales innecesarios
        assert f'name="descuento_comision_{self.minorista.pk}"'.encode() in content
        # Minorista tiene 0.0, que con strip_trailing_zeros se convierte a "0"
        assert b'value="0"' in content

        assert f'name="descuento_comision_{self.corporativo.pk}"'.encode() in content
        assert b'value="5"' in content  # 5.0 se convierte a "5"

        assert f'name="descuento_comision_{self.vip.pk}"'.encode() in content
        assert b'value="10"' in content  # 10.0 se convierte a "10"

    def test_guardar_comisiones_actualiza_los_valores(self, client):
        """Al postear el formulario, los valores en BD deben actualizarse."""
        url = reverse("guardar_comisiones")
        data = {
            f"descuento_comision_{self.minorista.pk}": "1.5",
            f"descuento_comision_{self.corporativo.pk}": "2.0",
            f"descuento_comision_{self.vip.pk}": "12.3",
        }

        resp = client.post(url, data)
        # redirect esperado a configuracion
        assert resp.status_code in (302, 303)

        # refrescar desde la BD y comprobar
        self.minorista.refresh_from_db()
        self.corporativo.refresh_from_db()
        self.vip.refresh_from_db()

        assert self.minorista.descuento_sobre_comision == Decimal("1.5")
        assert self.corporativo.descuento_sobre_comision == Decimal("2.0")
        assert self.vip.descuento_sobre_comision == Decimal("12.3")

    def test_guardar_comisiones_missing_field_no_modifica(self, client):
        """Si falta un campo, no se realiza el guardado (se redirige y no cambia BD)."""
        url = reverse("guardar_comisiones")
        # Omitimos el campo del VIP
        data = {
            f"descuento_comision_{self.minorista.pk}": "1.0",
            f"descuento_comision_{self.corporativo.pk}": "2.0",
            # VIP faltante
        }

        resp = client.post(url, data)
        # assert codigos de redireccion.
        assert resp.status_code in (302, 303)

        # refrescar y asegurar que VIP sigue igual
        self.vip.refresh_from_db()
        assert self.vip.descuento_sobre_comision == Decimal("10.0")

    def test_guardar_comisiones_invalid_value_no_modifica(self, client):
        """Si se envía un valor no numérico, no se guarda y la BD queda igual."""
        url = reverse("guardar_comisiones")
        data = {
            f"descuento_comision_{self.minorista.pk}": "1.0",
            f"descuento_comision_{self.corporativo.pk}": "no-num",
            f"descuento_comision_{self.vip.pk}": "3.0",
        }

        resp = client.post(url, data)
        # assert codigos de redireccion.
        assert resp.status_code in (302, 303)

        # Corporativo no debe cambiar
        self.corporativo.refresh_from_db()
        assert self.corporativo.descuento_sobre_comision == Decimal("5.0")
