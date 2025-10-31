"""Tests unitarios para el modelo CuentaBancaria."""

import pytest
from django.core.exceptions import ValidationError

from apps.transacciones.models import CuentaBancaria


@pytest.fixture
def entidad_bancaria2():
    """Fixture para crear una segunda entidad bancaria."""
    from apps.transacciones.models import EntidadFinanciera
    return EntidadFinanciera.objects.create(
        nombre="Banco Nacional",
        tipo="banco",
        activo=True
    )


@pytest.mark.django_db
class TestCuentaBancaria:
    """Tests unitarios para el modelo CuentaBancaria."""

    def test_cuenta_bancaria_creation(self, cliente, entidad_bancaria):
        """Test creación de cuenta bancaria."""
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            entidad=entidad_bancaria,
            titular_cuenta="Juan Perez",
            documento_titular="12345678",
            alias="Mi Cuenta Principal",
            habilitado_para_pago=True,
            habilitado_para_cobro=True
        )

        assert cuenta.numero_cuenta == "1234567890"
        assert cuenta.entidad == entidad_bancaria
        assert cuenta.titular_cuenta == "Juan Perez"
        assert cuenta.documento_titular == "12345678"
        assert cuenta.alias == "Mi Cuenta Principal"
        assert cuenta.cliente == cliente
        assert cuenta.habilitado_para_pago is True
        assert cuenta.habilitado_para_cobro is True

    def test_cuenta_bancaria_str(self, cliente, entidad_bancaria):
        """Test representación en string de cuenta bancaria."""
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            entidad=entidad_bancaria,
            titular_cuenta="Juan Perez",
            documento_titular="12345678",
            alias="Mi Cuenta"
        )

        expected_str = f"CuentaBancaria - {cliente.nombre} (Mi Cuenta)"
        assert str(cuenta) == expected_str

    def test_get_numero_enmascarado(self, cliente, entidad_bancaria):
        """Test obtención del número de cuenta enmascarado."""
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            entidad=entidad_bancaria,
            titular_cuenta="Juan Perez",
            documento_titular="12345678"
        )

        numero_enmascarado = cuenta.get_numero_enmascarado()
        assert numero_enmascarado == "****7890"

    def test_generar_alias_automatico(self, cliente, entidad_bancaria):
        """Test generación automática de alias."""
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            entidad=entidad_bancaria,
            titular_cuenta="Juan Perez",
            documento_titular="12345678"
        )

        alias_generado = cuenta.generar_alias()
        expected_alias = "Banco Test ****7890"
        assert alias_generado == expected_alias

    def test_validacion_ruc_valido(self, cliente, entidad_bancaria):
        """Test validación de RUC válido."""
        # RUC válido formato paraguayo
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            entidad=entidad_bancaria,
            titular_cuenta="Juan Perez",
            documento_titular="7653142-2"  # RUC válido
        )

        cuenta.refresh_from_db()
        # Si llega aquí significa que no se lanzó una excepción, por lo que el RUC es válido
        assert cuenta.documento_titular == "7653142-2"

    def test_validacion_cedula_solo_digitos(self, cliente, entidad_bancaria):
        """Test validación con cédula (solo dígitos)."""
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            entidad=entidad_bancaria,
            titular_cuenta="Juan Perez",
            documento_titular="12345678"  # Solo dígitos
        )

        cuenta.refresh_from_db()
        assert cuenta.documento_titular == "12345678"

    def test_cuenta_duplicada_mismo_cliente_misma_entidad(self, cliente, entidad_bancaria):
        """Test que no se permitan cuentas duplicadas para el mismo cliente y entidad."""
        CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            entidad=entidad_bancaria,
            titular_cuenta="Juan Perez",
            documento_titular="12345678"
        )

        with pytest.raises(ValidationError) as exc_info:
            CuentaBancaria.objects.create(
                cliente=cliente,
                numero_cuenta="1234567890",
                entidad=entidad_bancaria,
                titular_cuenta="Maria Garcia",
                documento_titular="87654321"
            )

        assert "numero_cuenta" in exc_info.value.message_dict
        error_message = exc_info.value.message_dict["numero_cuenta"]
        assert "Ya tienes una cuenta con este número en Banco Test" in str(error_message)

    def test_cuenta_mismo_numero_diferente_entidad(self, cliente, entidad_bancaria, entidad_bancaria2):
        """Test que sí se permita el mismo número de cuenta en diferentes entidades."""
        CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            entidad=entidad_bancaria,
            titular_cuenta="Juan Perez",
            documento_titular="12345678"
        )

        # Crear cuenta con mismo número pero diferente entidad - debería ser válido
        cuenta2 = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            entidad=entidad_bancaria2,
            titular_cuenta="Juan Perez",
            documento_titular="12345678"
        )

        assert cuenta2.numero_cuenta == "1234567890"
        assert cuenta2.entidad == entidad_bancaria2
