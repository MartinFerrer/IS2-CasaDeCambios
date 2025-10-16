"""Módulo de pruebas para la funcionalidad de envío de correos electrónicos.

Este módulo contiene las pruebas relacionadas con el envío de correos de verificación
durante el proceso de registro de usuarios.

Verifica:
    * El envío correcto de correos después de un registro exitoso.
    * La no emisión de correos cuando el registro falla.
    * El contenido y destinatario correctos en los correos enviados.

Las pruebas utilizan el backend de pruebas de correo de Django (:mod:`django.core.mail`)
para verificar el envío sin necesidad de un servidor SMTP real.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class EnvioCorreoTests(TestCase):
    """Suite de pruebas para la verificación del sistema de correos.

    Esta clase agrupa las pruebas relacionadas con el envío de correos durante
    el registro de nuevos usuarios. Se enfoca en validar que el sistema invoque
    correctamente el método :func:`django.core.mail.send_mail` y que los datos
    enviados sean coherentes con la información del usuario registrado.
    """

    def setUp(self):
        """Configura el ambiente de pruebas antes de cada test.

        Inicializa la URL de registro obtenida mediante :func:`django.urls.reverse`.

        Attributes
        ----------
        url_registro : str
            URL de la vista de registro de usuarios.

        """
        self.url_registro = reverse("seguridad:registro")

    @patch("apps.seguridad.views.send_mail")
    def test_envio_correo_despues_registro(self, mock_send_mail):
        """Verifica el envío del correo de verificación post-registro.

        Este test comprueba que, al realizar un registro exitoso, se envíe un
        correo de verificación al nuevo usuario.

        Pasos verificados:
            1. El registro exitoso redirige correctamente al usuario.
            2. Se llama al método :func:`django.core.mail.send_mail` desde la vista.
            3. Se envía exactamente un correo.
            4. El correo se dirige al email registrado.
            5. El asunto contiene la palabra ``verifica``.
            6. El cuerpo incluye el nombre del usuario.

        Parameters
        ----------
        mock_send_mail : MagicMock
            Mock del método :func:`django.core.mail.send_mail` utilizado para
            interceptar y verificar la llamada de envío.

        """
        datos = {
            "nombre": "Usuario Prueba",
            "email": "correo@example.com",
            "password1": "segura12345",
            "password2": "segura12345",
        }

        # Ejecutar registro
        response = self.client.post(self.url_registro, datos)

        # 1. Verificar redirección (registro exitoso)
        self.assertEqual(response.status_code, 302)

        # 2. Verificar que se llamó al método send_mail desde la vista
        mock_send_mail.assert_called_once()

        # 3. Verificar que el correo se envió al usuario correcto
        args = mock_send_mail.call_args[0]
        self.assertIn(datos["email"], args[3])  # recipients
        self.assertIn("verifica", args[0].lower())  # subject
        self.assertIn(datos["nombre"], args[1])  # message body

    @patch("apps.seguridad.views.send_mail")
    def test_no_envia_correo_con_datos_invalidos(self, mock_send_mail):
        """Verifica que no se envíen correos con datos de registro inválidos.

        Este test asegura que el sistema **no intente enviar correos de verificación**
        cuando el formulario de registro contiene errores de validación, tales como:

            * Email con formato inválido.
            * Contraseñas que no coinciden.
            * Contraseñas demasiado cortas.

        Parameters
        ----------
        mock_send_mail : MagicMock
            Mock del método :func:`django.core.mail.send_mail` utilizado para
            comprobar que no haya sido invocado.

        """
        datos = {
            "nombre": "Usuario Fallo",
            "email": "correo_invalido",  # Email con formato inválido
            "password1": "abc",  # Contraseña muy corta
            "password2": "xyz",  # No coincide
        }

        # Ejecutar intento de registro con datos inválidos
        self.client.post(self.url_registro, datos)

        # No debe haberse llamado a send_mail con datos inválidos
        mock_send_mail.assert_not_called()
