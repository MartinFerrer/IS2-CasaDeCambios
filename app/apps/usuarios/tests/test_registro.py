from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class RegistroUsuarioTests(TestCase):
    """Pruebas para el registro y creación de usuarios."""

    def test_creacion_usuario_valido(self):
        """Debe crear un usuario correctamente mediante el manager."""
        usuario = User.objects.create_user(
            email="nuevo@example.com", nombre="Nuevo Usuario", password="passwordSeguro123"
        )
        self.assertEqual(usuario.email, "nuevo@example.com")
        self.assertTrue(usuario.check_password("passwordSeguro123"))
        self.assertTrue(usuario.activo)

    def test_creacion_usuario_sin_email_falla(self):
        """Debe fallar al intentar crear un usuario sin email."""
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", nombre="SinEmail", password="12345678")

    def test_creacion_superusuario(self):
        """Debe crear un superusuario con permisos de staff y superuser."""
        admin = User.objects.create_superuser(email="admin@example.com", nombre="Admin", password="admin123")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
