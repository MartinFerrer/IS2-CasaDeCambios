"""Tests unitarios para el modelo BilleteraElectronica."""

import pytest
from django.core.exceptions import ValidationError

from apps.transacciones.models import BilleteraElectronica


@pytest.mark.django_db
class TestBilleteraElectronica:
    """Tests unitarios para el modelo BilleteraElectronica."""

    def test_billetera_electronica_creation(self, cliente, entidad_billetera):
        """Test creación de billetera electrónica."""
        billetera = BilleteraElectronica.objects.create(
            cliente=cliente,
            entidad=entidad_billetera,
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com",
            alias="Mi Personal Pay",
            habilitado_para_pago=True,
            habilitado_para_cobro=True
        )

        assert billetera.entidad == entidad_billetera
        assert billetera.identificador == "juan.perez@email.com"
        assert billetera.numero_telefono == "0981123456"
        assert billetera.email_asociado == "juan.perez@email.com"
        assert billetera.alias == "Mi Personal Pay"
        assert billetera.cliente == cliente
        assert billetera.habilitado_para_pago is True
        assert billetera.habilitado_para_cobro is True

    def test_billetera_electronica_str(self, cliente, entidad_billetera):
        """Test representación en string de billetera electrónica."""
        billetera = BilleteraElectronica.objects.create(
            cliente=cliente,
            entidad=entidad_billetera,
            identificador="0981123456",
            numero_telefono="0981123456",
            email_asociado="juan@email.com",
            alias="Mi Personal Pay"
        )

        expected_str = f"BilleteraElectronica - {cliente.nombre} (Mi Personal Pay)"
        assert str(billetera) == expected_str

    def test_generar_alias_automatico(self, cliente, entidad_billetera):
        """Test generación automática de alias."""
        billetera = BilleteraElectronica.objects.create(
            cliente=cliente,
            entidad=entidad_billetera,
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com"
        )

        alias_generado = billetera.generar_alias()
        expected_alias = "Personal Pay Test (juan.perez...)"
        assert alias_generado == expected_alias

    def test_billetera_duplicada_mismo_cliente_misma_entidad(self, cliente, entidad_billetera):
        """Test que no se permitan billeteras duplicadas para el mismo cliente y entidad."""
        BilleteraElectronica.objects.create(
            cliente=cliente,
            entidad=entidad_billetera,
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com"
        )

        with pytest.raises(ValidationError) as exc_info:
            BilleteraElectronica.objects.create(
                cliente=cliente,
                entidad=entidad_billetera,
                identificador="juan.perez@email.com",
                numero_telefono="0981654321",
                email_asociado="otro@email.com"
            )

        assert "identificador" in exc_info.value.message_dict
        error_message = exc_info.value.message_dict["identificador"]
        assert "Ya tienes una billetera de Personal Pay Test con este identificador" in str(error_message)

    def test_billetera_mismo_identificador_diferente_entidad(self, cliente, entidad_billetera, entidad_billetera2):
        """Test que sí se permita el mismo identificador en diferentes entidades."""
        BilleteraElectronica.objects.create(
            cliente=cliente,
            entidad=entidad_billetera,
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com"
        )

        # Crear billetera con mismo identificador pero diferente entidad - debería ser válido
        billetera2 = BilleteraElectronica.objects.create(
            cliente=cliente,
            entidad=entidad_billetera2,
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com"
        )

        assert billetera2.identificador == "juan.perez@email.com"
        assert billetera2.entidad == entidad_billetera2

    def test_billetera_mismo_identificador_diferente_cliente(self, cliente, cliente2, entidad_billetera):
        """Test que sí se permita el mismo identificador para diferentes clientes."""
        BilleteraElectronica.objects.create(
            cliente=cliente,
            entidad=entidad_billetera,
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com"
        )

        # Crear billetera con mismo identificador y entidad pero diferente cliente - debería ser válido
        billetera2 = BilleteraElectronica.objects.create(
            cliente=cliente2,
            entidad=entidad_billetera,
            identificador="juan.perez@email.com",
            numero_telefono="0981123456",
            email_asociado="juan.perez@email.com"
        )

        assert billetera2.identificador == "juan.perez@email.com"
        assert billetera2.cliente == cliente2
