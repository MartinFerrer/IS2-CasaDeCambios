"""Tests unitarios para el modelo BilleteraElectronica."""

import pytest
from django.core.exceptions import ValidationError

from apps.transacciones.models import BilleteraElectronica


@pytest.mark.django_db
class TestBilleteraElectronica:
    """Tests unitarios para el modelo BilleteraElectronica."""

    def test_billetera_electronica_creation(self, cliente):
        """Test creación de billetera electrónica."""
        billetera = BilleteraElectronica.objects.create(
            cliente=cliente,
            proveedor="personal_pay",
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com",
            alias="Mi Personal Pay"
        )

        assert billetera.proveedor == "personal_pay"
        assert billetera.identificador == "juan.perez@email.com"
        assert billetera.numero_telefono == "0981123456"
        assert billetera.email_asociado == "juan.perez@email.com"
        assert billetera.alias == "Mi Personal Pay"
        assert billetera.cliente == cliente

    def test_billetera_electronica_str(self, cliente):
        """Test representación en string de billetera electrónica."""
        billetera = BilleteraElectronica.objects.create(
            cliente=cliente,
            proveedor="mango",
            identificador="0981123456",
            numero_telefono="0981123456",
            email_asociado="juan@email.com",
            alias="Mi Mango"
        )

        expected_str = f"BilleteraElectronica - {cliente.nombre} (Mi Mango)"
        assert str(billetera) == expected_str

    def test_generar_alias_automatico(self, cliente):
        """Test generación automática de alias."""
        billetera = BilleteraElectronica.objects.create(
            cliente=cliente,
            proveedor="personal_pay",
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com"
        )

        alias_generado = billetera.generar_alias()
        expected_alias = "Personal Pay (juan.perez...)"
        assert alias_generado == expected_alias

    def test_proveedores_disponibles(self):
        """Test que todos los proveedores están disponibles."""
        proveedores_esperados = [
            "personal_pay", "mango", "wally", "eko", "vaquita", "otros"
        ]

        proveedores_disponibles = [choice[0] for choice in BilleteraElectronica.PROVEEDORES]

        for proveedor in proveedores_esperados:
            assert proveedor in proveedores_disponibles

    def test_billetera_duplicada_mismo_cliente_mismo_proveedor(self, cliente):
        """Test que no se permitan billeteras duplicadas para el mismo cliente y proveedor."""
        BilleteraElectronica.objects.create(
            cliente=cliente,
            proveedor="personal_pay",
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com"
        )

        with pytest.raises(ValidationError) as exc_info:
            BilleteraElectronica.objects.create(
                cliente=cliente,
                proveedor="personal_pay",
                identificador="juan.perez@email.com",
                numero_telefono="0981654321",
                email_asociado="otro@email.com"
            )

        assert "identificador" in exc_info.value.message_dict
        assert "Ya tienes una billetera de Personal Pay con este identificador" in exc_info.value.message_dict["identificador"]

    def test_billetera_mismo_identificador_diferente_proveedor(self, cliente):
        """Test que sí se permita el mismo identificador en diferentes proveedores."""
        BilleteraElectronica.objects.create(
            cliente=cliente,
            proveedor="personal_pay",
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com"
        )

        # Crear billetera con mismo identificador pero diferente proveedor - debería ser válido
        billetera2 = BilleteraElectronica.objects.create(
            cliente=cliente,
            proveedor="mango",
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com"
        )

        assert billetera2.identificador == "juan.perez@email.com"
        assert billetera2.proveedor == "mango"

    def test_billetera_mismo_identificador_diferente_cliente(self, cliente, cliente2):
        """Test que sí se permita el mismo identificador para diferentes clientes."""
        BilleteraElectronica.objects.create(
            cliente=cliente,
            proveedor="personal_pay",
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com"
        )

        # Crear billetera con mismo identificador y proveedor pero diferente cliente - debería ser válido
        billetera2 = BilleteraElectronica.objects.create(
            cliente=cliente2,
            proveedor="personal_pay",
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com"
        )

        assert billetera2.identificador == "juan.perez@email.com"
        assert billetera2.cliente == cliente2
