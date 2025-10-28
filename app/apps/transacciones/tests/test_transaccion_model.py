"""Tests unitarios para el modelo Transaccion y sus métodos."""

import uuid
from decimal import Decimal

import pytest
from apps.operaciones.models import Divisa, TasaCambio
from apps.transacciones.models import Transaccion
from apps.usuarios.models import Cliente, TipoCliente, Usuario
from django.core.exceptions import ValidationError


@pytest.mark.django_db
class TestTransaccionModel:
    """Tests unitarios para el modelo Transaccion."""

    @pytest.fixture
    def usuario(self):
        """Usuario de prueba."""
        return Usuario.objects.create(email="test@example.com", nombre="Usuario Test")

    @pytest.fixture
    def cliente(self, usuario):
        """Cliente de prueba."""
        tipo_cliente = TipoCliente.objects.create(nombre="Tipo Test", descuento_sobre_comision=Decimal("5.0"))
        cliente = Cliente.objects.create(
            nombre="Cliente Test", ruc="4396117-7", email="cliente@test.com", tipo_cliente=tipo_cliente
        )
        cliente.usuarios.add(usuario)
        return cliente

    @pytest.fixture
    def divisas(self):
        """Divisas de prueba."""
        pyg, _ = Divisa.objects.get_or_create(codigo="PYG", defaults={"nombre": "Guaraní", "simbolo": "₷"})
        usd, _ = Divisa.objects.get_or_create(codigo="USD", defaults={"nombre": "Dólar", "simbolo": "$"})
        return {"PYG": pyg, "USD": usd}

    @pytest.fixture
    def tasa_cambio(self, divisas):
        """Tasa de cambio de prueba."""
        return TasaCambio.objects.create(
            divisa_origen=divisas["PYG"],
            divisa_destino=divisas["USD"],
            precio_base=Decimal("7000.0"),
            comision_compra=Decimal("50.0"),
            comision_venta=Decimal("75.0"),
            activo=True,
        )

    @pytest.fixture
    def transaccion(self, usuario, cliente, divisas, tasa_cambio):
        """Transacción de prueba."""
        tasa_efectiva = Decimal("7071.25")
        return Transaccion.objects.create(
            cliente=cliente,
            usuario=usuario,
            tipo_operacion="compra",
            divisa_origen=divisas["PYG"],
            divisa_destino=divisas["USD"],
            tasa_aplicada=tasa_efectiva,
            monto_origen=Decimal("70712.5"),
            monto_destino=Decimal("10.0"),
            tasa_original=tasa_efectiva,
        )

    def test_transaccion_str_method(self, transaccion):
        """Test método __str__ de Transaccion."""
        expected = f"Transacción {transaccion.tipo_operacion} - {transaccion.cliente.nombre} - {transaccion.estado}"
        assert str(transaccion) == expected

    def test_clean_divisas_diferentes(self, usuario, cliente, divisas):
        """Test validación de divisas diferentes."""
        transaccion = Transaccion(
            cliente=cliente,
            usuario=usuario,
            tipo_operacion="compra",
            divisa_origen=divisas["USD"],  # Misma divisa
            divisa_destino=divisas["USD"],  # Misma divisa
            tasa_aplicada=Decimal("7050.0"),
            monto_origen=Decimal("10.0"),
            monto_destino=Decimal("70500.0"),
        )

        with pytest.raises(ValidationError) as exc_info:
            transaccion.clean()

        assert "Las divisas de origen y destino deben ser diferentes." in str(exc_info.value)

    def test_clean_divisas_diferentes_success(self, usuario, cliente, divisas):
        """Test validación exitosa con divisas diferentes."""
        transaccion = Transaccion(
            cliente=cliente,
            usuario=usuario,
            tipo_operacion="compra",
            divisa_origen=divisas["PYG"],
            divisa_destino=divisas["USD"],
            tasa_aplicada=Decimal("7050.0"),
            monto_origen=Decimal("70500.0"),
            monto_destino=Decimal("10.0"),
        )

        # No debe lanzar excepción
        transaccion.clean()

    def test_verificar_cambio_cotizacion_sin_tasa_actual(self, transaccion):
        """Test verificar cambio de cotización sin tasa en BD."""
        # Eliminar la tasa para simular que no hay tasa activa
        TasaCambio.objects.all().delete()

        resultado = transaccion.verificar_cambio_cotizacion()

        assert resultado["cambio_detectado"] is False
        assert "error" in resultado
        assert "No se encontró tasa de cambio activa" in resultado["error"]

    def test_verificar_cambio_cotizacion_sin_cambio(self, transaccion, tasa_cambio):
        """Test verificar cotización sin cambios significativos."""
        # La tasa actual debería ser la misma que la original
        resultado = transaccion.verificar_cambio_cotizacion()

        assert resultado["cambio_detectado"] is False

    def test_verificar_cambio_cotizacion_con_cambio_significativo(self, transaccion, tasa_cambio):
        """Test verificar cotización con cambio significativo."""
        # Cambiar la tasa base para simular un cambio
        tasa_cambio.precio_base = Decimal("8000.0")  # Cambio significativo
        tasa_cambio.save()

        resultado = transaccion.verificar_cambio_cotizacion()

        assert resultado["cambio_detectado"] is True
        assert "tasa_original" in resultado
        assert "tasa_actual" in resultado
        assert "porcentaje_cambio" in resultado
        assert "cambio_absoluto" in resultado

    def test_verificar_cambio_cotizacion_compra_con_descuento(self, transaccion, tasa_cambio):
        """Test verificar cotización para compra con descuento del cliente."""
        # Cambiar la tasa para simular cambio
        tasa_cambio.precio_base = Decimal("8000.0")
        tasa_cambio.save()

        resultado = transaccion.verificar_cambio_cotizacion()

        # Para COMPRA: cliente compra divisa (nosotros vendemos)
        # Debe incluir el descuento del 5% del cliente sobre la comisión de VENTA
        expected_comision = Decimal("75.0") - (Decimal("75.0") * Decimal("5.0") / Decimal("100"))
        expected_tasa = Decimal("8000.0") + expected_comision

        assert resultado["tasa_actual"] == expected_tasa.quantize(Decimal("0.001"))

    def test_verificar_cambio_cotizacion_venta(self, usuario, cliente, divisas, tasa_cambio):
        """Test verificar cotización para operación de venta."""
        transaccion_venta = Transaccion.objects.create(
            cliente=cliente,
            usuario=usuario,
            tipo_operacion="venta",
            divisa_origen=divisas["USD"],
            divisa_destino=divisas["PYG"],
            tasa_aplicada=Decimal("6925.0"),  # precio_base - comision_venta con descuento
            monto_origen=Decimal("10.0"),
            monto_destino=Decimal("69250.0"),
            tasa_original=Decimal("6925.0"),
        )

        # Cambiar la tasa para simular cambio
        tasa_cambio.precio_base = Decimal("8000.0")
        tasa_cambio.save()

        resultado = transaccion_venta.verificar_cambio_cotizacion()

        # Para VENTA: cliente vende divisa (nosotros compramos)
        # Usamos comisión de COMPRA y restamos del precio base
        expected_comision = Decimal("50.0") - (Decimal("50.0") * Decimal("5.0") / Decimal("100"))
        expected_tasa = Decimal("8000.0") - expected_comision

        assert resultado["tasa_actual"] == expected_tasa.quantize(Decimal("0.001"))

    def test_cancelar_por_cotizacion(self, transaccion):
        """Test cancelar transacción por cambio de cotización."""
        motivo_custom = "Precio cambió demasiado"
        transaccion.cancelar_por_cotizacion(motivo_custom)

        assert transaccion.estado == "cancelada_cotizacion"
        assert transaccion.motivo_cancelacion == motivo_custom

    def test_cancelar_por_cotizacion_sin_motivo(self, transaccion):
        """Test cancelar transacción sin motivo específico."""
        transaccion.cancelar_por_cotizacion()

        assert transaccion.estado == "cancelada_cotizacion"
        assert "cambio significativo en la cotización" in transaccion.motivo_cancelacion

    def test_marcar_como_vencida(self, transaccion):
        """Test marcar transacción como vencida."""
        transaccion.marcar_como_vencida()

        assert transaccion.estado == "vencida"
        assert "cotización ya no vigente" in transaccion.motivo_cancelacion

    def test_aceptar_nueva_cotizacion(self, transaccion):
        """Test aceptar nueva cotización."""
        nueva_tasa = Decimal("7200.0")
        transaccion.tasa_actual = nueva_tasa
        transaccion.cambio_cotizacion_notificado = True

        transaccion.aceptar_nueva_cotizacion()

        assert transaccion.tasa_aplicada == nueva_tasa
        assert transaccion.tasa_original == nueva_tasa
        assert transaccion.cambio_cotizacion_notificado is False

    def test_aceptar_nueva_cotizacion_sin_tasa_actual(self, transaccion):
        """Test aceptar nueva cotización sin tasa_actual establecida."""
        transaccion.tasa_actual = None
        original_tasa = transaccion.tasa_aplicada

        transaccion.aceptar_nueva_cotizacion()

        # No debe cambiar si no hay tasa_actual
        assert transaccion.tasa_aplicada == original_tasa

    def test_save_calls_full_clean(self, usuario, cliente, divisas):
        """Test que save() llama a full_clean()."""
        transaccion = Transaccion(
            cliente=cliente,
            usuario=usuario,
            tipo_operacion="compra",
            divisa_origen=divisas["USD"],  # Inválido - misma divisa
            divisa_destino=divisas["USD"],  # Inválido - misma divisa
            tasa_aplicada=Decimal("7050.0"),
            monto_origen=Decimal("70500.0"),
            monto_destino=Decimal("10.0"),
        )

        with pytest.raises(ValidationError):
            transaccion.save()

    def test_meta_configuration(self):
        """Test configuración de metadatos del modelo."""
        meta = Transaccion._meta

        assert meta.verbose_name == "Transacción"
        assert meta.verbose_name_plural == "Transacciones"
        assert meta.ordering == ["-fecha_creacion"]

    def test_transaccion_default_values(self, usuario, cliente, divisas):
        """Test valores por defecto de la transacción."""
        transaccion = Transaccion(
            cliente=cliente,
            usuario=usuario,
            tipo_operacion="compra",
            divisa_origen=divisas["PYG"],
            divisa_destino=divisas["USD"],
            tasa_aplicada=Decimal("7050.0"),
            monto_origen=Decimal("70500.0"),
            monto_destino=Decimal("10.0"),
        )

        assert transaccion.estado == "pendiente"
        assert transaccion.cambio_cotizacion_notificado is False
        assert transaccion.id_transaccion is not None
        assert isinstance(transaccion.id_transaccion, uuid.UUID)

    def test_verificar_cambio_cotizacion_exception_handling(self, transaccion):
        """Test manejo de excepciones en verificar_cambio_cotizacion."""
        # Simular error eliminando la divisa destino
        transaccion.divisa_destino = None

        resultado = transaccion.verificar_cambio_cotizacion()

        assert resultado["cambio_detectado"] is False
        assert "error" in resultado

    def test_estados_transaccion_choices(self):
        """Test que las opciones de estado están bien definidas."""
        expected_states = ["pendiente", "completada", "cancelada", "cancelada_cotizacion", "vencida", "anulada"]

        for state, _ in Transaccion.ESTADOS_TRANSACCION:
            assert state in expected_states

    def test_tipos_operacion_choices(self):
        """Test que los tipos de operación están bien definidos."""
        expected_types = ["compra", "venta"]

        for tipo, _ in Transaccion.TIPOS_OPERACION:
            assert tipo in expected_types
