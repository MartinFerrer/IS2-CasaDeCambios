"""Tests unitarios para el modelo EntidadFinanciera."""

from decimal import Decimal

import pytest
from apps.transacciones.models import EntidadFinanciera
from django.core.exceptions import ValidationError


@pytest.mark.django_db
class TestEntidadFinanciera:
    """Tests unitarios para EntidadFinanciera."""

    def test_entidad_financiera_creation(self):
        """Test creación básica de entidad financiera."""
        entidad = EntidadFinanciera.objects.create(
            nombre="Banco Nacional", tipo="banco", comision_compra=Decimal("2.5"), comision_venta=Decimal("3.0")
        )

        assert entidad.nombre == "Banco Nacional"
        assert entidad.tipo == "banco"
        assert entidad.comision_compra == Decimal("2.5")
        assert entidad.comision_venta == Decimal("3.0")
        assert entidad.activo is True
        assert entidad.fecha_creacion is not None
        assert entidad.fecha_modificacion is not None

    def test_entidad_financiera_str(self):
        """Test método __str__ de EntidadFinanciera."""
        entidad = EntidadFinanciera(nombre="Visa", tipo="emisor_tarjeta")

        expected = "Visa (Emisor de Tarjeta)"
        assert str(entidad) == expected

    def test_entidad_financiera_str_with_invalid_type(self):
        """Test método __str__ con tipo inválido."""
        entidad = EntidadFinanciera(nombre="Entidad Test", tipo="tipo_invalido")

        expected = "Entidad Test (tipo_invalido)"
        assert str(entidad) == expected

    def test_clean_comision_compra_negativa(self):
        """Test validación de comisión de compra negativa."""
        entidad = EntidadFinanciera(
            nombre="Banco Test", tipo="banco", comision_compra=Decimal("-1.0"), comision_venta=Decimal("2.0")
        )

        with pytest.raises(ValidationError) as exc_info:
            entidad.clean()

        assert "comision_compra" in exc_info.value.message_dict
        assert "La comisión de compra no puede ser negativa." in exc_info.value.message_dict["comision_compra"]

    def test_clean_comision_venta_negativa(self):
        """Test validación de comisión de venta negativa."""
        entidad = EntidadFinanciera(
            nombre="Banco Test", tipo="banco", comision_compra=Decimal("2.0"), comision_venta=Decimal("-1.0")
        )

        with pytest.raises(ValidationError) as exc_info:
            entidad.clean()

        assert "comision_venta" in exc_info.value.message_dict
        assert "La comisión de venta no puede ser negativa." in exc_info.value.message_dict["comision_venta"]

    def test_clean_comisiones_validas(self):
        """Test validación exitosa con comisiones válidas."""
        entidad = EntidadFinanciera(
            nombre="Banco Test", tipo="banco", comision_compra=Decimal("2.0"), comision_venta=Decimal("3.0")
        )

        # No debe lanzar excepción
        entidad.clean()

    def test_save_calls_full_clean(self):
        """Test que save() llama a full_clean() para validaciones."""
        entidad = EntidadFinanciera(
            nombre="Banco Test",
            tipo="banco",
            comision_compra=Decimal("-1.0"),  # Inválida
            comision_venta=Decimal("2.0"),
        )

        with pytest.raises(ValidationError):
            entidad.save()

    def test_unique_together_constraint(self):
        """Test restricción unique_together para nombre y tipo."""
        # Crear primera entidad
        EntidadFinanciera.objects.create(nombre="Banco Nacional", tipo="banco")

        # Intentar crear segunda entidad con mismo nombre y tipo
        with pytest.raises(ValidationError) as exc_info:
            EntidadFinanciera.objects.create(nombre="Banco Nacional", tipo="banco")

        assert "Entidad Financiera with this Nombre and Tipo already exists" in str(exc_info.value)

    def test_different_names_same_type_allowed(self):
        """Test que se permite diferentes nombres con mismo tipo."""
        EntidadFinanciera.objects.create(nombre="Banco Nacional", tipo="banco")

        # Debe poder crear otra entidad con diferente nombre
        entidad2 = EntidadFinanciera.objects.create(nombre="Banco Internacional", tipo="banco")

        assert entidad2.pk is not None

    def test_same_name_different_type_allowed(self):
        """Test que se permite mismo nombre con diferentes tipos."""
        EntidadFinanciera.objects.create(nombre="Visa", tipo="emisor_tarjeta")

        # Debe poder crear otra entidad con mismo nombre pero diferente tipo
        entidad2 = EntidadFinanciera.objects.create(nombre="Visa", tipo="proveedor_billetera")

        assert entidad2.pk is not None

    def test_default_values(self):
        """Test valores por defecto."""
        entidad = EntidadFinanciera(nombre="Test", tipo="banco")

        assert entidad.comision_compra == Decimal("0.00")
        assert entidad.comision_venta == Decimal("0.00")
        assert entidad.activo is True

    def test_meta_configuration(self):
        """Test configuración de metadatos del modelo."""
        meta = EntidadFinanciera._meta

        assert meta.verbose_name == "Entidad Financiera"
        assert meta.verbose_name_plural == "Entidades Financieras"
        assert meta.ordering == ["tipo", "nombre"]
        assert ("nombre", "tipo") in meta.unique_together

    def test_choices_validation(self):
        """Test validación de opciones válidas para tipo."""
        valid_types = ["banco", "emisor_tarjeta", "proveedor_billetera"]

        for tipo in valid_types:
            entidad = EntidadFinanciera.objects.create(nombre=f"Test {tipo}", tipo=tipo)
            assert entidad.tipo == tipo
