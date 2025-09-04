"""Testeos Unitarios para el modelo TipoCliente."""

from decimal import Decimal

import pytest

from apps.usuarios.models import TipoCliente


@pytest.mark.django_db
class TestTipoClienteModel:
    """Testeos Unitarios para el modelo TipoCliente."""

    def test_tipocliente_creation_and_str(self):
        """Testear creación de TipoCliente."""
        tc = TipoCliente.objects.create(nombre="Regular", descuento_sobre_comision=Decimal("7.0"))
        assert tc.nombre == "Regular"
        assert tc.descuento_sobre_comision == Decimal("7.0")
        assert str(tc) == "Regular"

    def test_descuento_sobre_comision_se_redondea_a_un_decimal_al_guardar(self):
        """Testear redondeo de descuento sobre la comision.

        Si se crea con más de 1 decimal (p.ej. 5.25), el campo DecimalField con
        decimal_places=1 debe almacenar el valor redondeado/quantizado a 1 decimal.
        """
        tc = TipoCliente.objects.create(nombre="Redondeo", descuento_sobre_comision=Decimal("5.25"))
        tc.refresh_from_db()
        # Django quantiza a la cantidad de decimal_places definida (1)
        assert tc.descuento_sobre_comision == Decimal("5.3")

    def test_descuento_sobre_comision_valor_maximo_aceptable(self):
        """Testear el valor maximo del descuento sobre la comision.

        Verificamos que valores dentro del rango de max_digits y decimal_places
        se guarden correctamente (p.ej. 99.9 si max_digits=3, decimal_places=1).
        """
        tc = TipoCliente.objects.create(nombre="Maximo", descuento_sobre_comision=Decimal("99.9"))
        tc.refresh_from_db()
        assert tc.descuento_sobre_comision == Decimal("99.9")
