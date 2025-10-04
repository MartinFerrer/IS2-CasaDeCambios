"""Utilidades para funcionalidades de MFA (Multi-Factor Authentication).

Este módulo contiene funciones de utilidad para manejar la autenticación
multifactor en el sistema.
"""

import io

import qrcode
from django.contrib.auth import get_user_model
from django.http import HttpResponse

from .models import PerfilMFA, RegistroMFA

User = get_user_model()


def obtener_ip_cliente(request):
    """Obtiene la dirección IP del cliente desde el request.

    Args:
        request: Objeto HttpRequest de Django

    Returns:
        str: Dirección IP del cliente

    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def obtener_user_agent(request):
    """Obtiene el user agent del navegador desde el request.

    Args:
        request: Objeto HttpRequest de Django

    Returns:
        str: User agent del navegador

    """
    return request.META.get("HTTP_USER_AGENT", "")


def crear_perfil_mfa(usuario):
    """Crea un perfil MFA para un usuario si no existe.

    Args:
        usuario: Instancia del modelo Usuario

    Returns:
        PerfilMFA: Perfil MFA creado o existente

    """
    perfil_mfa, created = PerfilMFA.objects.get_or_create(usuario=usuario)
    return perfil_mfa


def generar_qr_response(perfil_mfa):
    """Genera una respuesta HTTP con el código QR para configurar MFA.

    Args:
        perfil_mfa: Instancia de PerfilMFA

    Returns:
        HttpResponse: Respuesta HTTP con imagen PNG del código QR

    """
    # Generar código QR
    qr_uri = perfil_mfa.generar_qr_uri()
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_uri)
    qr.make(fit=True)

    # Crear imagen
    img = qr.make_image(fill_color="black", back_color="white")

    # Convertir a bytes
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    # Crear respuesta HTTP
    response = HttpResponse(img_buffer.getvalue(), content_type="image/png")
    response["Content-Disposition"] = f'inline; filename="qr_mfa_{perfil_mfa.usuario.email}.png"'

    return response


def registrar_intento_mfa(usuario, tipo_operacion, resultado, request, referencia_transaccion=None):
    """Registra un intento de autenticación MFA.

    Args:
        usuario: Instancia del modelo Usuario
        tipo_operacion: Tipo de operación ('login' o 'transaccion')
        resultado: Resultado del intento ('exitoso', 'fallido', 'expirado')
        request: Objeto HttpRequest de Django
        referencia_transaccion: UUID de la transacción si aplica

    Returns:
        RegistroMFA: Registro creado

    """
    return RegistroMFA.objects.create(
        usuario=usuario,
        tipo_operacion=tipo_operacion,
        resultado=resultado,
        direccion_ip=obtener_ip_cliente(request),
        user_agent=obtener_user_agent(request),
        referencia_transaccion=referencia_transaccion,
    )


def verificar_codigo_usuario(usuario, codigo):
    """Verifica un código TOTP para un usuario específico.

    Args:
        usuario: Instancia del modelo Usuario
        codigo: Código TOTP de 6 dígitos

    Returns:
        bool: True si el código es válido, False en caso contrario

    """
    try:
        perfil_mfa = PerfilMFA.objects.get(usuario=usuario)
        return perfil_mfa.verificar_codigo(codigo)
    except PerfilMFA.DoesNotExist:
        return False


def usuario_requiere_mfa_login(usuario):
    """Verifica si un usuario tiene habilitado MFA para login.

    Args:
        usuario: Instancia del modelo Usuario

    Returns:
        bool: True si el usuario tiene MFA habilitado para login

    """
    try:
        perfil_mfa = PerfilMFA.objects.get(usuario=usuario)
        return perfil_mfa.mfa_habilitado_login
    except PerfilMFA.DoesNotExist:
        return False


def usuario_tiene_mfa_configurado(usuario):
    """Verifica si un usuario tiene MFA configurado (perfil creado).

    Args:
        usuario: Instancia del modelo Usuario

    Returns:
        bool: True si el usuario tiene perfil MFA

    """
    return PerfilMFA.objects.filter(usuario=usuario).exists()
