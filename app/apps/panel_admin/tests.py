from django.test import TestCase

from .models import Rol, Usuario

# Make the unit tests about the usuario model


class UsuarioModelTest(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create(
            nombre="Test User", email="test@example.com", password="testpassword", rol="admin", activo=True
        )

    def test_usuario_creation(self):
        self.assertEqual(self.usuario.nombre, "Test User")
        self.assertEqual(self.usuario.email, "test@example.com")
        self.assertTrue(self.usuario.check_password("testpassword"))
        self.assertEqual(self.usuario.rol, "admin")
        self.assertTrue(self.usuario.activo)

    def test_usuario_str(self):
        self.assertEqual(str(self.usuario), "Test User")


# How can I try those tests?
# You can run the tests using the Django test runner.
# How can i run the django test runner
# You can run the test suite using the following command:
# python manage.py test panel_admin

# Create your tests here.
