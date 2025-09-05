"""Tests unitarios para el modelo CuentaBancaria."""

import pytest
from django.core.exceptions import ValidationError

from apps.transacciones.models import CuentaBancaria


@pytest.mark.django_db
class TestCuentaBancaria:
    """Tests unitarios para el modelo CuentaBancaria."""

    def test_cuenta_bancaria_creation(self, cliente):
        """Test creación de cuenta bancaria."""
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            banco="Banco Test",
            titular_cuenta="Juan Perez",
            documento_titular="12345678",
            alias="Mi Cuenta Principal"
        )

        assert cuenta.numero_cuenta == "1234567890"
        assert cuenta.banco == "Banco Test"
        assert cuenta.titular_cuenta == "Juan Perez"
        assert cuenta.documento_titular == "12345678"
        assert cuenta.alias == "Mi Cuenta Principal"
        assert cuenta.cliente == cliente

    def test_cuenta_bancaria_str(self, cliente):
        """Test representación en string de cuenta bancaria."""
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            banco="Banco Test",
            titular_cuenta="Juan Perez",
            documento_titular="12345678",
            alias="Mi Cuenta"
        )

        expected_str = f"CuentaBancaria - {cliente.nombre} (Mi Cuenta)"
        assert str(cuenta) == expected_str

    def test_get_numero_enmascarado(self, cliente):
        """Test obtención del número de cuenta enmascarado."""
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            banco="Banco Test",
            titular_cuenta="Juan Perez",
            documento_titular="12345678"
        )

        numero_enmascarado = cuenta.get_numero_enmascarado()
        assert numero_enmascarado == "****7890"

    def test_generar_alias_automatico(self, cliente):
        """Test generación automática de alias."""
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            banco="Banco Test",
            titular_cuenta="Juan Perez",
            documento_titular="12345678"
        )

        alias_generado = cuenta.generar_alias()
        expected_alias = "Banco Test ****7890"
        assert alias_generado == expected_alias

    def test_validacion_ruc_valido(self, cliente):
        """Test validación de RUC válido."""
        # RUC válido formato paraguayo
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            banco="Banco Test",
            titular_cuenta="Juan Perez",
            documento_titular="7653142-2"  # RUC válido
        )

        cuenta.refresh_from_db()
        # Si llega aquí significa que no se lanzó una excepción, por lo que el RUC es válido
        assert cuenta.documento_titular == "7653142-2"

    def test_validacion_cedula_solo_digitos(self, cliente):
        """Test validación con cédula (solo dígitos)."""
        cuenta = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            banco="Banco Test",
            titular_cuenta="Juan Perez",
            documento_titular="12345678"  # Solo dígitos
        )

        cuenta.refresh_from_db()
        assert cuenta.documento_titular == "12345678"

    def test_cuenta_duplicada_mismo_cliente_mismo_banco(self, cliente):
        """Test que no se permitan cuentas duplicadas para el mismo cliente y banco."""
        CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            banco="Banco Test",
            titular_cuenta="Juan Perez",
            documento_titular="12345678"
        )

        with pytest.raises(ValidationError) as exc_info:
            CuentaBancaria.objects.create(
                cliente=cliente,
                numero_cuenta="1234567890",
                banco="Banco Test",
                titular_cuenta="Maria Garcia",
                documento_titular="87654321"
            )

        assert "numero_cuenta" in exc_info.value.message_dict
        assert "Ya tienes una cuenta con este número en Banco Test" in exc_info.value.message_dict["numero_cuenta"]

    def test_cuenta_mismo_numero_diferente_banco(self, cliente):
        """Test que sí se permita el mismo número de cuenta en diferentes bancos."""
        CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            banco="Banco Test",
            titular_cuenta="Juan Perez",
            documento_titular="12345678"
        )

        # Crear cuenta con mismo número pero diferente banco - debería ser válido
        cuenta2 = CuentaBancaria.objects.create(
            cliente=cliente,
            numero_cuenta="1234567890",
            banco="Otro Banco",
            titular_cuenta="Juan Perez",
            documento_titular="12345678"
        )

        assert cuenta2.numero_cuenta == "1234567890"
        assert cuenta2.banco == "Otro Banco"
