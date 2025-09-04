import pytest

from apps.usuarios.models import Usuario


@pytest.mark.django_db
class TestUsuarioModel:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.usuario = Usuario.objects.create(
            nombre="Test User",
            email="test@example.com",
            password="testpassword",
            activo=True,
        )

    def test_usuario_creation(self):
        assert self.usuario.nombre == "Test User"
        assert self.usuario.email == "test@example.com"
        assert self.usuario.activo is True

    def test_usuario_str(self):
        assert str(self.usuario) == "Test User"

    def test_create_user_without_email(self):
        with pytest.raises(ValueError):
            Usuario.objects.create_user(
                email="",
                nombre="Test User",
                password="testpassword",
            )

    def test_create_superuser(self):
        superuser = Usuario.objects.create_superuser(
            email="admin@example.com",
            nombre="Admin User",
            password="adminpass",
        )
        assert superuser.is_staff
        assert superuser.is_superuser

    def test_email_normalize(self):
        user = Usuario.objects.create_user(
            email="TEST@EXAMPLE.COM",
            nombre="Test User",
            password="testpass",
        )
        assert user.email == "TEST@example.com"
