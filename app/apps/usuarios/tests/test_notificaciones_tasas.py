from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.operaciones.models import Divisa, TasaCambio, TasaCambioHistorial
from apps.usuarios.models import Cliente, PreferenciaNotificacion
from apps.usuarios.tasks import send_grouped_notifications, send_single_notification, ventana_para_frecuencia


@pytest.fixture
def setup_data(db):
    """Fixture para configurar datos base necesarios para las pruebas."""
    cliente = Cliente(ruc="1817708-5", nombre="Test Cliente", email="test@example.com")
    cliente.save()
    preferencia = PreferenciaNotificacion.objects.create(cliente=cliente, habilitado=True, frecuencia="diario")

    # Use get_or_create to avoid duplicate key errors
    divisa_pyg, _ = Divisa.objects.get_or_create(codigo="PYG", defaults={"nombre": "Guaraní"})
    divisa_usd, _ = Divisa.objects.get_or_create(codigo="USD", defaults={"nombre": "Dólar"})

    tasa_cambio, _ = TasaCambio.objects.get_or_create(
        divisa_origen=divisa_usd,
        divisa_destino=divisa_pyg,
        defaults={
            "precio_base": Decimal("7500"),
            "comision_compra": Decimal("50"),
            "comision_venta": Decimal("100"),
        },
    )

    TasaCambioHistorial.objects.create(
        tasa_cambio_original=tasa_cambio,
        divisa_origen=divisa_usd,
        divisa_destino=divisa_pyg,
        precio_base=Decimal("7400"),
        comision_compra=Decimal("50"),
        comision_venta=Decimal("100"),
        motivo="Creación",
    )

    return cliente, preferencia


@pytest.mark.django_db
class TestNotificationTasks:
    """Tests para las tareas de notificaciones de tasas de cambio."""

    # --- Tests para ventana_para_frecuencia ---
    def test_ventana_para_frecuencia_logic(self):
        """Calculo de ventana para diferentes frecuencias."""
        # Nota: El valor 'diario' se espera que sea 5 segundos si el tasks.py de prueba está activo.
        # Asumo la lógica de producción para este test (timedelta(days=1))
        assert ventana_para_frecuencia("diario") in [timedelta(days=1), timedelta(seconds=5)]
        assert ventana_para_frecuencia("semanal") == timedelta(weeks=1)
        assert ventana_para_frecuencia("mensual") == timedelta(days=30)
        assert ventana_para_frecuencia("invalid") == timedelta(days=30)  # default

    # --- Tests para send_single_notification ---

    @patch("apps.usuarios.tasks.EmailMultiAlternatives")
    def test_send_single_notification_success(self, mock_email, setup_data):
        """Envio exitoso de notificación individual."""
        _, preferencia = setup_data

        mock_email_instance = MagicMock()
        mock_email.return_value = mock_email_instance

        subject = "Test Subject"
        text_body = "Test text body"
        html_body = "<p>Test HTML body</p>"

        old_ultimo_envio = preferencia.ultimo_envio

        send_single_notification(preferencia.id, subject, text_body, html_body)

        mock_email.assert_called_once()
        mock_email_instance.send.assert_called_once_with(fail_silently=False)

        preferencia.refresh_from_db()
        assert preferencia.ultimo_envio is not None
        assert preferencia.ultimo_envio != old_ultimo_envio

    def test_send_single_notification_preferencia_not_found(self, db):
        """Manejo de PreferenciaNotificacion no encontrada."""
        result = send_single_notification(99999, "Subject", "Text", "HTML")
        assert result is None

    @patch("apps.usuarios.tasks.send_single_notification.retry")
    @patch("apps.usuarios.tasks.EmailMultiAlternatives")
    def test_send_single_notification_email_failure_retries(self, mock_email, mock_retry, setup_data):
        """Test email sending failure triggers Celery retry."""
        _, preferencia = setup_data

        mock_email_instance = MagicMock()
        # Simula un fallo de envío (ej. error SMTP)
        mock_email_instance.send.side_effect = Exception("SMTP error")
        mock_email.return_value = mock_email_instance

        # Simula que se llama al método retry
        send_single_notification(preferencia.id, "Subject", "Text", "HTML")

        mock_retry.assert_called_once()

    # --- Tests para send_grouped_notifications ---

    @patch("apps.usuarios.tasks.send_single_notification.delay")
    def test_grouped_notifications_no_changes(self, mock_send_single, setup_data):
        """Notificaciones agrupadas cuando NO existen cambios recientes."""
        # Se asume que el cambio en el fixture fue hace tiempo o no existe
        # Hacemos que la única TasaCambioHistorial sea vieja
        TasaCambioHistorial.objects.all().update(fecha_registro=timezone.now() - timedelta(days=50))

        send_grouped_notifications("diario")

        mock_send_single.assert_not_called()

    @patch("apps.usuarios.tasks.send_single_notification.delay")
    def test_grouped_notifications_preferencia_disabled(self, mock_send_single, setup_data):
        """Test que las preferencias deshabilitadas son omitidas."""
        cliente, preferencia = setup_data

        preferencia.habilitado = False
        preferencia.save()

        send_grouped_notifications("diario")

        mock_send_single.assert_not_called()

    @patch("apps.usuarios.tasks.send_single_notification.delay")
    def test_grouped_notifications_exception_handling(self, mock_send_single, setup_data):
        """Manejo de excepciones durante la obtención de preferencias."""
        # Mock para simular un fallo en el queryset de PreferenciaNotificacion
        with patch("apps.usuarios.tasks.PreferenciaNotificacion.objects.select_related") as mock_prefs_qs:
            mock_prefs_qs.side_effect = Exception("DB error")

            result = send_grouped_notifications("diario")

            assert result is None
