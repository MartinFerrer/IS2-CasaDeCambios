"""Módulo de pruebas para la funcionalidad de envío de correos electrónicos.

Este módulo contiene las pruebas relacionadas con el envío de correos de verificación
durante el proceso de registro de usuarios. Verifica:
- El envío correcto de correos después de un registro exitoso
- La no emisión de correos cuando el registro falla
- El contenido y destinatario correctos en los correos enviados

Las pruebas utilizan el backend de pruebas de correo de Django (mail.outbox)
para verificar el envío sin necesidad de un servidor SMTP real.
"""

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

# Obtener el modelo de usuario personalizado configurado en settings.AUTH_USER_MODEL
User = get_user_model()


class EnvioCorreoTests(TestCase):
    """Suite de pruebas para la verificación del sistema de correos.

    Esta clase prueba el flujo completo de envío de correos durante el registro,
    asegurando que:
    1. Se envíen correos solo para registros válidos
    2. No se envíen correos para datos inválidos
    3. El contenido del correo sea el esperado
    4. El correo se envíe al destinatario correcto

    Attributes:
        url_registro (str): URL de la vista de registro obtenida mediante reverse()

    """

    def setUp(self):
        """Configura el ambiente de pruebas antes de cada test.

        Inicializa:
            - URL de registro usando la vista de seguridad:registro
        """
        self.url_registro = reverse("seguridad:registro")

    def test_envio_correo_despues_registro(self):
        """Verifica el envío del correo de verificación post-registro.

        Este test verifica que:
        1. El registro exitoso redirija al usuario
        2. Se envíe exactamente un correo
        3. El correo se envíe al email registrado
        4. El asunto contenga "verifica"
        5. El cuerpo incluya el nombre del usuario

        El test utiliza datos válidos de registro y verifica
        la respuesta HTTP y el contenido del correo enviado.
        """
        datos = {
            "nombre": "Usuario Prueba",
            "email": "correo@example.com",
            "password1": "segura12345",
            "password2": "segura12345",
        }

        response = self.client.post(self.url_registro, datos)

        # Se espera redirección al confirmar registro
        self.assertEqual(response.status_code, 302)

        # Verificar que se haya enviado un correo
        self.assertEqual(len(mail.outbox), 1)

        correo = mail.outbox[0]
        self.assertIn("correo@example.com", correo.to)
        self.assertIn("verifica", correo.subject.lower())
        self.assertIn("Usuario Prueba", correo.body)

    def test_no_envia_correo_con_datos_invalidos(self):
        """Verifica que no se envíen correos con datos de registro inválidos.

        Este test asegura que el sistema no envíe correos de verificación
        cuando el formulario de registro contiene errores, específicamente:
        1. Email con formato inválido
        2. Contraseñas que no coinciden
        3. Contraseñas demasiado cortas

        Se espera que el sistema valide los datos antes de intentar
        cualquier envío de correo.
        """
        datos = {
            "nombre": "Usuario Fallo",
            "email": "correo_invalido",  # Email con formato inválido
            "password1": "abc",  # Contraseña muy corta
            "password2": "xyz",  # No coincide con password1
        }

        self.client.post(self.url_registro, datos)

        # Verifica que no se haya enviado ningún correo
        self.assertEqual(len(mail.outbox), 0)
