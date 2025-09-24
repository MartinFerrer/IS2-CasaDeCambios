"""Tests unitarios para el modelo TarjetaCredito."""

from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError

from apps.transacciones.models import EntidadFinanciera, TarjetaCredito


@pytest.fixture
def entidad_emisora():
    """Fixture para crear una entidad emisora de tarjetas."""
    return EntidadFinanciera.objects.create(
        nombre="Visa",
        tipo="emisor_tarjeta",
        activo=True
    )


@pytest.mark.django_db
class TestTarjetaCredito:
    """Tests unitarios para el modelo TarjetaCredito."""

    def test_tarjeta_credito_creation(self, cliente, entidad_emisora):
        """Test creación de tarjeta de crédito."""
        fecha_futura = date.today() + timedelta(days=365)
        tarjeta = TarjetaCredito.objects.create(
            cliente=cliente,
            numero_tarjeta="1234567890123456",
            nombre_titular="Juan Perez",
            fecha_expiracion=fecha_futura,
            cvv="123",
            alias="Mi Tarjeta Principal",
            entidad=entidad_emisora,
            habilitado_para_pago=True,
            habilitado_para_cobro=False
        )

        assert tarjeta.numero_tarjeta == "1234567890123456"
        assert tarjeta.nombre_titular == "Juan Perez"
        assert tarjeta.fecha_expiracion == fecha_futura
        assert tarjeta.cvv == "123"
        assert tarjeta.alias == "Mi Tarjeta Principal"
        assert tarjeta.cliente == cliente
        assert tarjeta.entidad == entidad_emisora
        assert tarjeta.habilitado_para_pago is True
        assert tarjeta.habilitado_para_cobro is False

    def test_tarjeta_credito_str(self, cliente, entidad_emisora):
        """Test representación en string de tarjeta de crédito."""
        fecha_futura = date.today() + timedelta(days=365)
        tarjeta = TarjetaCredito.objects.create(
            cliente=cliente,
            numero_tarjeta="1234567890123456",
            nombre_titular="Juan Perez",
            fecha_expiracion=fecha_futura,
            cvv="123",
            alias="Mi Tarjeta",
            entidad=entidad_emisora
        )

        expected_str = f"TarjetaCredito - {cliente.nombre} (Mi Tarjeta)"
        assert str(tarjeta) == expected_str

    def test_generar_alias_automatico(self, cliente, entidad_emisora):
        """Test generación automática de alias."""
        fecha_futura = date.today() + timedelta(days=365)
        tarjeta = TarjetaCredito.objects.create(
            cliente=cliente,
            numero_tarjeta="1234567890123456",
            nombre_titular="Juan Perez",
            fecha_expiracion=fecha_futura,
            cvv="123",
            entidad=entidad_emisora
        )

        alias_generado = tarjeta.generar_alias()
        expected_alias = "Visa - ****3456"
        assert alias_generado == expected_alias

    def test_get_numero_enmascarado(self, cliente, entidad_emisora):
        """Test obtención del número de tarjeta enmascarado."""
        fecha_futura = date.today() + timedelta(days=365)
        tarjeta = TarjetaCredito.objects.create(
            cliente=cliente,
            numero_tarjeta="1234567890123456",
            nombre_titular="Juan Perez",
            fecha_expiracion=fecha_futura,
            cvv="123",
            entidad=entidad_emisora
        )

        numero_enmascarado = tarjeta.get_numero_enmascarado()
        assert numero_enmascarado == "****-****-****-3456"

    def test_validar_fecha_vencimiento_tarjeta_vencida(self, cliente, entidad_emisora):
        """Test validación de fecha de vencimiento con tarjeta vencida."""
        fecha_pasada = date.today() - timedelta(days=1)

        with pytest.raises(ValidationError) as exc_info:
            TarjetaCredito.objects.create(
                cliente=cliente,
                numero_tarjeta="1234567890123456",
                nombre_titular="Juan Perez",
                fecha_expiracion=fecha_pasada,
                cvv="123",
                entidad=entidad_emisora
            )

        assert "fecha_expiracion" in exc_info.value.message_dict
        error_message = exc_info.value.message_dict["fecha_expiracion"]
        assert "La tarjeta no puede estar vencida." in str(error_message)

    def test_tarjeta_duplicada_mismo_cliente(self, cliente, entidad_emisora):
        """Test que no se permitan tarjetas duplicadas para el mismo cliente."""
        fecha_futura = date.today() + timedelta(days=365)
        TarjetaCredito.objects.create(
            cliente=cliente,
            numero_tarjeta="1234567890123456",
            nombre_titular="Juan Perez",
            fecha_expiracion=fecha_futura,
            cvv="123",
            entidad=entidad_emisora
        )

        with pytest.raises(ValidationError) as exc_info:
            TarjetaCredito.objects.create(
                cliente=cliente,
                numero_tarjeta="1234567890123456",
                nombre_titular="Maria Garcia",
                fecha_expiracion=fecha_futura,
                cvv="456",
                entidad=entidad_emisora
            )

        assert "numero_tarjeta" in exc_info.value.message_dict
        error_message = exc_info.value.message_dict["numero_tarjeta"]
        assert "Ya tienes asociada una tarjeta con este número." in str(error_message)

    def test_tarjeta_mismo_numero_diferente_cliente(self, cliente, cliente2, entidad_emisora):
        """Test que sí se permita el mismo número de tarjeta para diferentes clientes."""
        fecha_futura = date.today() + timedelta(days=365)

        # Crear primera tarjeta
        TarjetaCredito.objects.create(
            cliente=cliente,
            numero_tarjeta="1234567890123456",
            nombre_titular="Juan Perez",
            fecha_expiracion=fecha_futura,
            cvv="123",
            entidad=entidad_emisora
        )

        # Crear segunda tarjeta con mismo número pero diferente cliente - debería ser válido
        tarjeta2 = TarjetaCredito.objects.create(
            cliente=cliente2,
            numero_tarjeta="1234567890123456",
            nombre_titular="Maria Garcia",
            fecha_expiracion=fecha_futura,
            cvv="456",
            entidad=entidad_emisora
        )

        assert tarjeta2.numero_tarjeta == "1234567890123456"
        assert tarjeta2.cliente == cliente2
