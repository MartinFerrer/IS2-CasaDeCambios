"""Módulo de pruebas para la creación de usuarios y envío de correos de verificación.

Este módulo valida la correcta creación de usuarios mediante el manager personalizado
y el envío de correos electrónicos tras el registro exitoso.

Verifica:
- Creación de usuarios válidos y superusuarios
- Manejo de errores al crear usuarios sin email
- Envío correcto de correos de verificación mediante `django.core.mail.send_mail`

Las pruebas utilizan el decorador `@patch` de `unittest.mock` para interceptar
las llamadas a `send_mail`, evitando el envío real de correos y permitiendo
verificar los argumentos utilizados.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RegistroUsuarioTests(TestCase):
    """Suite de pruebas para el registro y creación de usuarios."""

    def test_creacion_usuario_valido(self):
        """Verifica la creación correcta de un usuario válido.

        Este test comprueba que:
        - El usuario se crea correctamente mediante el manager
        - La contraseña se guarda y verifica adecuadamente
        - El usuario queda activo tras la creación
        """
        usuario = User.objects.create_user(
            email="nuevo@example.com",
            nombre="Nuevo Usuario",
            password="passwordSeguro123",
        )

        self.assertEqual(usuario.email, "nuevo@example.com")
        self.assertTrue(usuario.check_password("passwordSeguro123"))
        self.assertTrue(usuario.activo)

    def test_creacion_usuario_sin_email_falla(self):
        """Verifica que no se pueda crear un usuario sin email.

        Este test asegura que:
        - El método `create_user` lanza un ValueError si el email está vacío
        """
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="",
                nombre="SinEmail",
                password="12345678",
            )

    def test_creacion_superusuario(self):
        """Verifica la creación de un superusuario con permisos correctos.

        Este test comprueba que:
        - El superusuario tiene las banderas `is_staff` y `is_superuser` activas
        """
        admin = User.objects.create_superuser(
            email="admin@example.com",
            nombre="Admin",
            password="admin123",
        )

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    @patch("apps.seguridad.views.send_mail")
    def test_envio_correo_al_registrar_usuario(self, mock_send_mail):
        """Verifica el envío del correo de verificación al registrar un usuario.

        Este test verifica que:
        - Se llama al método `send_mail` desde la vista de registro
        - El correo se dirige al usuario recién registrado
        - El asunto del correo contiene la palabra “verifica”

        :param mock_send_mail: Objeto simulado que intercepta la llamada al método `send_mail`
        """
        datos = {
            "nombre": "Usuario Test",
            "email": "correo@prueba.com",
            "password1": "segura12345",
            "password2": "segura12345",
        }

        # Ejecutar la solicitud de registro
        response = self.client.post(reverse("seguridad:registro"), datos)

        # Verificar que el registro fue exitoso (redirección)
        self.assertEqual(response.status_code, 302)

        # Verificar que se llamó al método send_mail
        mock_send_mail.assert_called_once()

        # Comprobar los argumentos utilizados
        args = mock_send_mail.call_args[0]
        self.assertIn(datos["email"], args[3])  # Verificar destinatario
        self.assertIn("verifica", args[0].lower())  # Verificar asunto
