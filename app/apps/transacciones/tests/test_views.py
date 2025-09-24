"""Tests unitarios para las vistas de transacciones."""

from datetime import date, timedelta

import pytest
from django.test import Client

from apps.transacciones.models import TarjetaCredito


@pytest.mark.django_db
class TestTransaccionesViews:
    """Tests para las vistas de transacciones."""

    def test_simular_cambio_view_get(self):
        """Test GET a la vista de simulación de cambio."""
        client = Client()
        response = client.get('/transacciones/simular-cambio/')

        assert response.status_code == 200

    def test_comprar_divisa_view_get(self):
        """Test GET a la vista de comprar divisa."""
        client = Client()
        response = client.get('/transacciones/comprar-divisa/')

        assert response.status_code == 200

    def test_vender_divisa_view_get(self):
        """Test GET a la vista de vender divisa."""
        client = Client()
        response = client.get('/transacciones/vender-divisa/')

        assert response.status_code == 200

    def test_configuracion_medios_pago_requiere_login(self):
        """Test que configuración de medios de pago requiere login."""
        client = Client()
        response = client.get('/transacciones/configuracion/')

        # Debe redirigir al login
        assert response.status_code == 302

    def test_configuracion_medios_pago_usuario_logueado(self, client_logueado, cliente_con_usuario):
        """Test configuración de medios de pago con usuario logueado."""
        response = client_logueado.get('/transacciones/configuracion/')

        assert response.status_code == 200
        assert 'clientes' in response.context
        assert cliente_con_usuario in response.context['clientes']

    def test_medios_pago_cliente_requiere_login(self, cliente):
        """Test que medios de pago de cliente requiere login."""
        client = Client()
        url = f'/transacciones/configuracion/cliente/{cliente.id}/'
        response = client.get(url)

        # Debe redirigir al login
        assert response.status_code == 302

    def test_medios_pago_cliente_usuario_logueado(self, client_logueado, cliente_con_usuario):
        """Test medios de pago de cliente con usuario logueado."""
        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/'
        response = client_logueado.get(url)

        assert response.status_code == 200
        assert response.context['cliente'] == cliente_con_usuario
        assert 'tarjetas' in response.context
        assert 'cuentas' in response.context
        assert 'billeteras' in response.context

    def test_medios_pago_cliente_no_autorizado(self, client_logueado, cliente):
        """Test que usuario no puede ver medios de pago de cliente no asociado."""
        url = f'/transacciones/configuracion/cliente/{cliente.id}/'
        response = client_logueado.get(url)

        # Debe retornar 404 porque el cliente no está asociado al usuario
        assert response.status_code == 404

    def test_crear_tarjeta_get(self, client_logueado, cliente_con_usuario):
        """Test GET para crear tarjeta."""
        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/tarjeta/crear/'
        response = client_logueado.get(url)

        assert response.status_code == 200
        assert response.context['cliente'] == cliente_con_usuario

    def test_crear_tarjeta_post_valida(self, client_logueado, cliente_con_usuario):
        """Test POST para crear tarjeta con datos válidos."""
        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/tarjeta/crear/'
        fecha_futura = date.today() + timedelta(days=365)

        data = {
            'numero_tarjeta': '1234567890123456',
            'nombre_titular': 'Juan Perez',
            'fecha_expiracion': fecha_futura.strftime('%Y-%m-%d'),
            'cvv': '123',
            'alias': 'Mi Tarjeta'
        }

        response = client_logueado.post(url, data)

        # Debe redirigir después de crear exitosamente
        assert response.status_code == 302

        # Verificar que la tarjeta se creó
        tarjeta = TarjetaCredito.objects.filter(
            cliente=cliente_con_usuario,
            numero_tarjeta='1234567890123456'
        ).first()
        assert tarjeta is not None
        assert tarjeta.nombre_titular == 'Juan Perez'

    def test_crear_tarjeta_post_invalida(self, client_logueado, cliente_con_usuario):
        """Test POST para crear tarjeta con datos inválidos."""
        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/tarjeta/crear/'
        fecha_pasada = date.today() - timedelta(days=1)

        data = {
            'numero_tarjeta': '1234567890123456',
            'nombre_titular': 'Juan Perez',
            'fecha_expiracion': fecha_pasada.strftime('%Y-%m-%d'),  # Fecha inválida (pasada)
            'cvv': '123'
        }

        response = client_logueado.post(url, data)

        # Debe quedarse en la misma página con errores
        assert response.status_code == 200

    def test_crear_tarjeta_cliente_no_autorizado(self, client_logueado, cliente):
        """Test crear tarjeta para cliente no asociado al usuario."""
        url = f'/transacciones/configuracion/cliente/{cliente.id}/tarjeta/crear/'
        response = client_logueado.get(url)

        # Debe retornar 404
        assert response.status_code == 404

    def test_crear_billetera_get(self, client_logueado, cliente_con_usuario):
        """Test GET para crear billetera electrónica."""
        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/billetera/crear/'
        response = client_logueado.get(url)

        assert response.status_code == 200
        assert response.context['cliente'] == cliente_con_usuario

    def test_crear_billetera_post_valida(self, client_logueado, cliente_con_usuario, entidad_billetera):
        """Test POST para crear billetera electrónica con datos válidos."""
        from apps.transacciones.models import BilleteraElectronica

        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/billetera/crear/'
        data = {
            'entidad': entidad_billetera.id,
            'identificador': 'mi_billetera@gmail.com',
            'numero_telefono': '0981123456',
            'email_asociado': 'mi_billetera@gmail.com',
            'alias': 'Mi Billetera',
            'habilitado_para_pago': 'on',
            'habilitado_para_cobro': 'on'
        }

        response = client_logueado.post(url, data)

        # Debe redirigir después de crear exitosamente
        assert response.status_code == 302

        # Verificar que la billetera se creó
        billetera = BilleteraElectronica.objects.filter(
            cliente=cliente_con_usuario,
            numero_telefono='0981123456'
        ).first()
        assert billetera is not None
        assert billetera.entidad == entidad_billetera
        assert billetera.habilitado_para_pago is True
        assert billetera.habilitado_para_cobro is True

    def test_crear_billetera_post_invalida(self, client_logueado, cliente_con_usuario):
        """Test POST para crear billetera electrónica con datos inválidos."""
        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/billetera/crear/'

        data = {
            'proveedor': 'personal_pay',
            'identificador': 'mi_billetera@gmail.com',
            'numero_telefono': '',  # Campo requerido vacío
            'email_asociado': 'email_invalido',  # Email inválido
        }

        response = client_logueado.post(url, data)

        # Debe quedarse en la misma página con errores
        assert response.status_code == 200

    def test_crear_billetera_cliente_no_autorizado(self, client_logueado, cliente):
        """Test crear billetera para cliente no asociado al usuario."""
        url = f'/transacciones/configuracion/cliente/{cliente.id}/billetera/crear/'
        response = client_logueado.get(url)

        # Debe retornar 404
        assert response.status_code == 404

    def test_crear_cuenta_bancaria_get(self, client_logueado, cliente_con_usuario):
        """Test GET para crear cuenta bancaria."""
        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/cuenta/crear/'
        response = client_logueado.get(url)

        assert response.status_code == 200
        assert response.context['cliente'] == cliente_con_usuario

    def test_crear_cuenta_bancaria_post_valida(self, client_logueado, cliente_con_usuario, entidad_bancaria):
        """Test POST para crear cuenta bancaria con datos válidos."""
        from apps.transacciones.models import CuentaBancaria

        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/cuenta/crear/'
        data = {
            'numero_cuenta': '1234567890',
            'entidad': entidad_bancaria.id,
            'titular_cuenta': 'Juan Perez',
            'documento_titular': '1234567-9',
            'alias': 'Mi Cuenta',
            'habilitado_para_pago': 'on',
            'habilitado_para_cobro': 'on'
        }

        response = client_logueado.post(url, data)

        # Debe redirigir después de crear exitosamente
        assert response.status_code == 302

        # Verificar que la cuenta se creó
        cuenta = CuentaBancaria.objects.filter(
            cliente=cliente_con_usuario,
            numero_cuenta='1234567890'
        ).first()
        assert cuenta is not None
        assert cuenta.entidad == entidad_bancaria
        assert cuenta.habilitado_para_pago is True
        assert cuenta.habilitado_para_cobro is True

    def test_crear_cuenta_bancaria_post_invalida(self, client_logueado, cliente_con_usuario):
        """Test POST para crear cuenta bancaria con datos inválidos."""
        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/cuenta/crear/'

        data = {
            'numero_cuenta': '',  # Campo requerido vacío
            'banco': 'Banco Nacional',
            'titular_cuenta': 'Juan Perez',
            'documento_titular': '1234567-9',
        }

        response = client_logueado.post(url, data)

        # Debe quedarse en la misma página con errores
        assert response.status_code == 200

    def test_crear_cuenta_bancaria_cliente_no_autorizado(self, client_logueado, cliente):
        """Test crear cuenta bancaria para cliente no asociado al usuario."""
        url = f'/transacciones/configuracion/cliente/{cliente.id}/cuenta/crear/'
        response = client_logueado.get(url)

        # Debe retornar 404
        assert response.status_code == 404

    def test_editar_tarjeta_get(self, client_logueado, cliente_con_usuario):
        """Test GET para editar tarjeta."""
        # Crear una tarjeta para editar
        tarjeta = TarjetaCredito.objects.create(
            cliente=cliente_con_usuario,
            numero_tarjeta='1111222233334444',
            nombre_titular='Juan Perez',
            fecha_expiracion=date.today() + timedelta(days=365),
            cvv='123',
            alias='Tarjeta Original'
        )

        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/tarjeta/{tarjeta.pk}/editar/'
        response = client_logueado.get(url)

        assert response.status_code == 200
        assert response.context['cliente'] == cliente_con_usuario
        assert response.context['tarjeta'] == tarjeta

    def test_editar_tarjeta_post_valida(self, client_logueado, cliente_con_usuario):
        """Test POST para editar tarjeta con datos válidos."""
        # Crear una tarjeta para editar
        tarjeta = TarjetaCredito.objects.create(
            cliente=cliente_con_usuario,
            numero_tarjeta='1111222233334444',
            nombre_titular='Juan Perez Original',
            fecha_expiracion=date.today() + timedelta(days=365),
            cvv='123',
            alias='Tarjeta Original'
        )

        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/tarjeta/{tarjeta.pk}/editar/'
        fecha_nueva = date.today() + timedelta(days=730)

        data = {
            'numero_tarjeta': '1111222233334444',
            'nombre_titular': 'Juan Perez Editado',
            'fecha_expiracion': fecha_nueva.strftime('%Y-%m-%d'),
            'cvv': '456',
            'alias': 'Tarjeta Editada'
        }

        response = client_logueado.post(url, data)

        # Debe redirigir después de editar exitosamente
        assert response.status_code == 302

        # Verificar que la tarjeta se actualizó
        tarjeta.refresh_from_db()
        assert tarjeta.nombre_titular == 'Juan Perez Editado'
        assert tarjeta.alias == 'Tarjeta Editada'
        assert tarjeta.cvv == '456'

    def test_editar_billetera_get(self, client_logueado, cliente_con_usuario, entidad_billetera):
        """Test GET para editar billetera electrónica."""
        from apps.transacciones.models import BilleteraElectronica

        # Crear una billetera para editar
        billetera = BilleteraElectronica.objects.create(
            cliente=cliente_con_usuario,
            entidad=entidad_billetera,
            identificador='original@gmail.com',
            numero_telefono='0981123456',
            email_asociado='original@gmail.com',
            alias='Billetera Original'
        )

        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/billetera/{billetera.pk}/editar/'
        response = client_logueado.get(url)

        assert response.status_code == 200
        assert response.context['cliente'] == cliente_con_usuario
        assert response.context['billetera'] == billetera

    def test_editar_billetera_post_valida(
        self, client_logueado, cliente_con_usuario, entidad_billetera, entidad_billetera2
    ):
        """Test POST para editar billetera electrónica con datos válidos."""
        from apps.transacciones.models import BilleteraElectronica

        # Crear una billetera para editar
        billetera = BilleteraElectronica.objects.create(
            cliente=cliente_con_usuario,
            entidad=entidad_billetera,
            identificador='original@gmail.com',
            numero_telefono='0981123456',
            email_asociado='original@gmail.com',
            alias='Billetera Original'
        )

        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/billetera/{billetera.pk}/editar/'

        data = {
            'entidad': entidad_billetera2.pk,
            'identificador': 'editado@gmail.com',
            'numero_telefono': '0981654321',
            'email_asociado': 'editado@gmail.com',
            'alias': 'Billetera Editada',
            'habilitado_para_pago': 'on',
            'habilitado_para_cobro': ''  # Solo pago habilitado
        }

        response = client_logueado.post(url, data)

        # Debe redirigir después de editar exitosamente
        assert response.status_code == 302

        # Verificar que la billetera se actualizó
        billetera.refresh_from_db()
        assert billetera.entidad == entidad_billetera2
        assert billetera.alias == 'Billetera Editada'
        assert billetera.numero_telefono == '0981654321'
        assert billetera.habilitado_para_pago is True
        assert billetera.habilitado_para_cobro is False

    def test_editar_cuenta_bancaria_get(self, client_logueado, cliente_con_usuario, entidad_bancaria):
        """Test GET para editar cuenta bancaria."""
        from apps.transacciones.models import CuentaBancaria

        # Crear una cuenta para editar
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente_con_usuario,
            numero_cuenta='1111222233334444',
            entidad=entidad_bancaria,
            titular_cuenta='Juan Perez Original',
            documento_titular='1234567-9',
            alias='Cuenta Original'
        )

        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/cuenta/{cuenta.pk}/editar/'
        response = client_logueado.get(url)

        assert response.status_code == 200
        assert response.context['cliente'] == cliente_con_usuario
        assert response.context['cuenta'] == cuenta

    def test_editar_cuenta_bancaria_post_valida(self, client_logueado, cliente_con_usuario, entidad_bancaria):
        """Test POST para editar cuenta bancaria con datos válidos."""
        from apps.transacciones.models import CuentaBancaria

        # Crear una cuenta para editar
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente_con_usuario,
            numero_cuenta='1111222233334444',
            entidad=entidad_bancaria,
            titular_cuenta='Juan Perez Original',
            documento_titular='1234567-9',
            alias='Cuenta Original'
        )

        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/cuenta/{cuenta.pk}/editar/'

        data = {
            'numero_cuenta': '1111222233334444',
            'entidad': entidad_bancaria.pk,
            'titular_cuenta': 'Juan Perez Editado',
            'documento_titular': '1234567-9',
            'alias': 'Cuenta Editada'
        }

        response = client_logueado.post(url, data)

        # Debe redirigir después de editar exitosamente
        assert response.status_code == 302

        # Verificar que la cuenta se actualizó
        cuenta.refresh_from_db()
        assert cuenta.entidad == entidad_bancaria
        assert cuenta.alias == 'Cuenta Editada'
        assert cuenta.titular_cuenta == 'Juan Perez Editado'

    def test_editar_tarjeta_cliente_no_autorizado(self, client_logueado, cliente):
        """Test editar tarjeta de cliente no asociado al usuario."""
        # Crear una tarjeta para un cliente no asociado
        tarjeta = TarjetaCredito.objects.create(
            cliente=cliente,
            numero_tarjeta='1111222233334444',
            nombre_titular='Juan Perez',
            fecha_expiracion=date.today() + timedelta(days=365),
            cvv='123',
            alias='Tarjeta no autorizada'
        )

        url = f'/transacciones/configuracion/cliente/{cliente.id}/tarjeta/{tarjeta.pk}/editar/'
        response = client_logueado.get(url)

        # Debe retornar 404
        assert response.status_code == 404

    def test_eliminar_tarjeta(self, client_logueado, cliente_con_usuario):
        """Test eliminar tarjeta de un cliente asociado."""
        # Crear una tarjeta para eliminar
        tarjeta = TarjetaCredito.objects.create(
            cliente=cliente_con_usuario,
            numero_tarjeta='1111222233334444',
            nombre_titular='Juan Perez',
            fecha_expiracion=date.today() + timedelta(days=365),
            cvv='123',
            alias='Tarjeta a eliminar'
        )

        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/tarjeta/{tarjeta.pk}/eliminar/'
        response = client_logueado.post(url)

        # Debe redirigir después de eliminar
        assert response.status_code == 302
        # Verificar que la tarjeta ya no existe
        assert not TarjetaCredito.objects.filter(pk=tarjeta.pk).exists()

    def test_eliminar_billetera(self, client_logueado, cliente_con_usuario, entidad_billetera):
        """Test eliminar billetera electrónica de un cliente asociado."""
        from apps.transacciones.models import BilleteraElectronica

        # Crear una billetera para eliminar
        billetera = BilleteraElectronica.objects.create(
            cliente=cliente_con_usuario,
            entidad=entidad_billetera,
            identificador='test@gmail.com',
            numero_telefono='0981123456',
            email_asociado='test@gmail.com',
            alias='Billetera a eliminar'
        )

        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/billetera/{billetera.pk}/eliminar/'
        response = client_logueado.post(url)

        # Debe redirigir después de eliminar
        assert response.status_code == 302
        # Verificar que la billetera ya no existe
        assert not BilleteraElectronica.objects.filter(pk=billetera.pk).exists()

    def test_eliminar_cuenta_bancaria(self, client_logueado, cliente_con_usuario, entidad_bancaria):
        """Test eliminar cuenta bancaria de un cliente asociado."""
        from apps.transacciones.models import CuentaBancaria

        # Crear una cuenta para eliminar
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente_con_usuario,
            numero_cuenta='9999888877776666',
            entidad=entidad_bancaria,
            titular_cuenta='Juan Perez',
            documento_titular='1234567-9',
            alias='Cuenta a eliminar'
        )

        url = f'/transacciones/configuracion/cliente/{cliente_con_usuario.id}/cuenta/{cuenta.pk}/eliminar/'
        response = client_logueado.post(url)

        # Debe redirigir después de eliminar
        assert response.status_code == 302
        # Verificar que la cuenta ya no existe
        assert not CuentaBancaria.objects.filter(pk=cuenta.pk).exists()

    def test_eliminar_tarjeta_cliente_no_autorizado(self, client_logueado, cliente):
        """Test eliminar tarjeta de cliente no asociado al usuario."""
        # Crear una tarjeta para un cliente no asociado
        tarjeta = TarjetaCredito.objects.create(
            cliente=cliente,
            numero_tarjeta='1111222233334444',
            nombre_titular='Juan Perez',
            fecha_expiracion=date.today() + timedelta(days=365),
            cvv='123',
            alias='Tarjeta no autorizada'
        )

        url = f'/transacciones/configuracion/cliente/{cliente.id}/tarjeta/{tarjeta.pk}/eliminar/'
        response = client_logueado.post(url)

        # Debe retornar 404
        assert response.status_code == 404
        # Verificar que la tarjeta sigue existiendo
        assert TarjetaCredito.objects.filter(pk=tarjeta.pk).exists()
