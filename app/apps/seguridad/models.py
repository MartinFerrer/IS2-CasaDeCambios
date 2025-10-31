"""Modelos para la aplicación de seguridad.

Este módulo contiene los modelos relacionados con la autenticación multifactor (MFA)
y otros aspectos de seguridad del sistema.
"""

import pyotp
from django.conf import settings
from django.db import models


class PerfilMFA(models.Model):
    """Modelo para gestionar configuración MFA de usuarios.

    Almacena la configuración de autenticación multifactor para cada usuario,
    incluyendo el secreto TOTP y las preferencias de uso.
    """

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_mfa")
    secreto_totp = models.CharField(max_length=32, help_text="Secreto base32 para generar códigos TOTP")
    mfa_habilitado_login = models.BooleanField(
        default=False, help_text="Si está habilitado MFA para el login del usuario"
    )
    mfa_habilitado_transacciones = models.BooleanField(
        default=True, help_text="Si está habilitado MFA para confirmar transacciones (recomendado)"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def generar_qr_uri(self):
        """Genera la URI para el código QR de Google Authenticator.

        Returns:
            str: URI para generar el código QR

        """
        totp = pyotp.TOTP(self.secreto_totp)
        return totp.provisioning_uri(name=self.usuario.email, issuer_name="Global Exchange - Casa de Cambios")

    def verificar_codigo(self, codigo):
        """Verifica un código TOTP.

        Args:
            codigo (str): Código de 6 dígitos a verificar

        Returns:
            bool: True si el código es válido, False en caso contrario

        """
        totp = pyotp.TOTP(self.secreto_totp)
        return totp.verify(codigo, valid_window=1)

    def obtener_codigo_actual(self):
        """Obtiene el código TOTP actual (solo para testing).

        Returns:
            str: Código TOTP de 6 dígitos

        """
        totp = pyotp.TOTP(self.secreto_totp)
        return totp.now()

    def save(self, *args, **kwargs):
        """Sobrescribe save para generar secreto automáticamente."""
        if not self.secreto_totp:
            self.secreto_totp = pyotp.random_base32()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"MFA - {self.usuario.email}"

    class Meta:
        """Configuración de metadatos para el modelo PerfilMFA."""

        verbose_name = "Perfil MFA"
        verbose_name_plural = "Perfiles MFA"


class RegistroMFA(models.Model):
    """Modelo para registrar intentos de autenticación MFA.

    Mantiene un log de los intentos de autenticación MFA para auditoría
    y detección de patrones de seguridad.
    """

    TIPOS_OPERACION = [
        ("login", "Login"),
        ("transaccion", "Confirmación de Transacción"),
    ]

    RESULTADOS = [
        ("exitoso", "Exitoso"),
        ("fallido", "Fallido"),
        ("expirado", "Código Expirado"),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registros_mfa")
    tipo_operacion = models.CharField(
        max_length=20, choices=TIPOS_OPERACION, help_text="Tipo de operación que requirió MFA"
    )
    resultado = models.CharField(max_length=20, choices=RESULTADOS, help_text="Resultado del intento de autenticación")
    direccion_ip = models.GenericIPAddressField(
        null=True, blank=True, help_text="Dirección IP desde donde se realizó el intento"
    )
    user_agent = models.TextField(blank=True, help_text="User agent del navegador")
    referencia_transaccion = models.UUIDField(null=True, blank=True, help_text="ID de transacción si aplica")
    fecha_intento = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.email} - {self.tipo_operacion} - {self.resultado}"

    class Meta:
        """Configuración de metadatos para el modelo RegistroMFA."""

        verbose_name = "Registro MFA"
        verbose_name_plural = "Registros MFA"
        ordering = ["-fecha_intento"]
