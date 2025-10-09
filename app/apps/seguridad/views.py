"""Módulo de vistas para la aplicación de seguridad.

Este módulo contiene las vistas relacionadas con la autenticación de usuarios,
registro con verificación por email, login, logout, y gestión de clientes
en el sistema de casa de cambios.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from apps.usuarios.forms import CustomUserCreationForm
from apps.usuarios.models import Usuario

from .forms import CodigoMFAForm, ConfiguracionMFAForm
from .models import PerfilMFA
from .utils import (
    crear_perfil_mfa,
    generar_qr_response,
    registrar_intento_mfa,
    usuario_requiere_mfa_login,
    verificar_codigo_usuario,
)

token_generator = PasswordResetTokenGenerator()


def registro_view(request):
    """Vista para el registro de nuevos usuarios.

    Maneja el formulario de registro, crea un usuario inactivo, asigna al grupo
    'Usuario Registrado', genera un token de verificación y envía un email
    con el enlace de verificación. Redirige al login tras el envío.

    Args:
    request: Objeto HttpRequest de Django.

    Retorna:
    HttpResponse: Renderiza la plantilla 'registro.html' con el formulario,
    o redirige a 'seguridad:login' tras el registro exitoso.

    """
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.activo = False
            user.is_active = False
            user.save()
            grupo, _ = Group.objects.get_or_create(name="Usuario Registrado")
            user.groups.add(grupo)
            token = token_generator.make_token(user)
            uid = user.pk
            verification_link = request.build_absolute_uri(
                reverse("seguridad:verificar_cuenta", kwargs={"uid": uid, "token": token}),
            )
            send_mail(
                "Verifica tu cuenta",
                f"Hola {user.nombre}, confirma tu correo haciendo clic en este enlace:\n{verification_link}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            messages.success(request, "Se ha enviado un correo de verificación. Revisa tu bandeja de entrada.")
            return redirect("seguridad:login")
        messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = CustomUserCreationForm()
    return render(request, "registro.html", {"form": form})


def verificar_cuenta(request, uid, token):
    """Vista para verificar la cuenta de usuario mediante token.

    Valida el token y activa la cuenta del usuario si es válido.
    Redirige al login con mensaje de éxito o error.

    Args:
        request: Objeto HttpRequest de Django.
        uid (int): ID del usuario.
        token (str): Token de verificación.

    Retorna:
        HttpResponse: Redirige a 'seguridad:login' o 'seguridad:registro'
        con mensajes correspondientes.

    """
    user = get_object_or_404(Usuario, pk=uid)
    if token_generator.check_token(user, token):
        user.activo = True
        user.is_active = True
        user.save()
        messages.success(request, "Tu cuenta ha sido verificada. Ya puedes iniciar sesión.")
        return redirect("seguridad:login")
    messages.error(request, "El enlace de verificación no es válido o ha expirado.")
    return redirect("seguridad:registro")


def login_view(request):
    """Vista para el inicio de sesión de usuarios.

    Autentica al usuario con email y contraseña. Si el usuario no está activo,
    muestra un mensaje de error. Tras login exitoso, redirige a la selección
    de cliente.

    Args:
        request: Objeto HttpRequest de Django.

    Retorna:
        HttpResponse: Renderiza 'login.html' o redirige a 'seguridad:seleccionar_cliente'.

    """
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            if not user.is_active or not user.activo:
                messages.error(request, "Debes verificar tu correo antes de iniciar sesión.")
                return redirect("seguridad:login")

            # Verificar si el usuario requiere MFA para login
            if usuario_requiere_mfa_login(user):
                # Guardar el usuario temporalmente en la sesión
                request.session["mfa_user_id"] = user.pk
                request.session["mfa_pre_auth"] = True
                return redirect("seguridad:verificar_mfa_login")

            login(request, user)
            # Redirigir directamente a selección de cliente
            return redirect("seguridad:seleccionar_cliente")

        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, "login.html")


def logout_view(request):
    """Vista para cerrar sesión de usuarios.

    Cierra la sesión del usuario actual y redirige al login con mensaje de éxito.

    Args:
        request: Objeto HttpRequest de Django.

    Retorna:
        HttpResponse: Redirige a 'seguridad:login'.

    """
    logout(request)
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect("seguridad:login")


@login_required
def cambiar_cliente(request):
    """Vista para cambiar el cliente seleccionado por el usuario.

    Actualiza la sesión con el nuevo cliente_id si es válido y pertenece al usuario.
    Redirige al home o muestra error.

    Args:
        request: Objeto HttpRequest de Django (requiere login).

    Retorna:
        HttpResponse: Renderiza 'cambiar_cliente.html' o redirige a 'presentacion:home'.

    """
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        if request.user.clientes.filter(id=cliente_id).exists():
            request.session["cliente_id"] = int(cliente_id)
            messages.success(request, "Cliente cambiado correctamente.")
            return redirect("presentacion:home")
        messages.error(request, "Cliente inválido.")
    clientes = request.user.clientes.all()
    return render(request, "cambiar_cliente.html", {"clientes": clientes})


@csrf_exempt
def obtener_clientes(request):
    """Vista AJAX para obtener la lista de clientes de un usuario.

    Autentica al usuario y devuelve una lista de clientes en formato JSON.

    Args:
        request: Objeto HttpRequest de Django (POST).

    Retorna:
        JsonResponse: Lista de clientes o error.

    """
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)
        if user is not None:
            clientes = user.clientes.all().values("id", "nombre")
            return JsonResponse({"success": True, "clientes": list(clientes)})
        return JsonResponse({"success": False, "clientes": []})
    return JsonResponse({"success": False, "error": "Método no permitido"})


@login_required
def seleccionar_cliente(request):
    """Vista para seleccionar un cliente al iniciar sesión.

    Muestra los clientes del usuario y permite seleccionar uno, actualizando la sesión.
    Redirige al home tras selección exitosa.

    Args:
    request: Objeto HttpRequest de Django (requiere login).

    Retorna:
    HttpResponse: Renderiza 'seleccionar_cliente.html' o redirige a 'presentacion:home'.

    """
    user = request.user
    clientes = user.clientes.all()

    # Si no hay clientes, seguir directo al home
    if not clientes.exists():
        request.session["cliente_id"] = None
        return redirect("presentacion:home")

    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        if clientes.filter(id=cliente_id).exists():
            request.session["cliente_id"] = int(cliente_id)
            messages.success(request, "Cliente seleccionado correctamente.")
            return redirect("presentacion:home")
        else:
            messages.error(request, "Cliente inválido")

    return render(request, "seleccionar_cliente.html", {"clientes": clientes})


def verificar_mfa_login(request):
    """Vista para verificar código MFA durante el login.

    Args:
        request: Objeto HttpRequest de Django.

    Returns:
        HttpResponse: Renderiza 'mfa_login.html' o redirige según el resultado.

    """
    # Verificar que tenemos un usuario pre-autenticado
    if not request.session.get("mfa_pre_auth") or not request.session.get("mfa_user_id"):
        messages.error(request, "Sesión inválida. Por favor, inicia sesión nuevamente.")
        return redirect("seguridad:login")

    user_id = request.session.get("mfa_user_id")
    try:
        user = Usuario.objects.get(id=user_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect("seguridad:login")

    if request.method == "POST":
        form = CodigoMFAForm(request.POST)
        if form.is_valid():
            codigo = form.cleaned_data["codigo"]

            # Verificar el código TOTP
            if verificar_codigo_usuario(user, codigo):
                # Código válido - registrar intento exitoso
                registrar_intento_mfa(user, "login", "exitoso", request)

                # Limpiar sesión temporal
                del request.session["mfa_pre_auth"]
                del request.session["mfa_user_id"]

                # Hacer login efectivo
                login(request, user)
                messages.success(request, "Autenticación exitosa.")
                return redirect("seguridad:seleccionar_cliente")
            else:
                # Código inválido - registrar intento fallido
                registrar_intento_mfa(user, "login", "fallido", request)
                messages.error(request, "Código de verificación incorrecto.")
    else:
        form = CodigoMFAForm()

    context = {"form": form, "usuario_email": user.email}
    return render(request, "mfa_login.html", context)


@login_required
def configurar_mfa(request):
    """Vista para configurar MFA del usuario.

    Args:
        request: Objeto HttpRequest de Django.

    Returns:
        HttpResponse: Renderiza 'configurar_mfa.html' o redirige según el resultado.

    """
    # Obtener o crear perfil MFA
    perfil_mfa = crear_perfil_mfa(request.user)

    # Guardar valores originales para comparación en mensajes
    mfa_login_original = perfil_mfa.mfa_habilitado_login
    mfa_transacciones_original = perfil_mfa.mfa_habilitado_transacciones

    if request.method == "POST":
        form = ConfiguracionMFAForm(request.POST, instance=perfil_mfa, usuario=request.user, perfil_mfa=perfil_mfa)
        if form.is_valid():
            form.save()
            # Mensajes específicos según lo que se activó/desactivó
            mfa_login_nuevo = form.cleaned_data.get("mfa_habilitado_login", False)
            mfa_transacciones_nuevo = form.cleaned_data.get("mfa_habilitado_transacciones", False)

            if mfa_login_nuevo and not mfa_login_original:
                messages.success(request, "MFA para login activado.")
            elif not mfa_login_nuevo and mfa_login_original:
                messages.success(request, "MFA para login desactivado.")

            if mfa_transacciones_nuevo != mfa_transacciones_original:
                if mfa_transacciones_nuevo:
                    messages.success(request, "MFA para transacciones activado.")
                else:
                    messages.success(request, "MFA para transacciones desactivado.")

            return redirect("seguridad:configurar_mfa")
        else:
            # Si hay errores, recargar el perfil desde la BD para mostrar el estado real
            perfil_mfa.refresh_from_db()
    else:
        form = ConfiguracionMFAForm(instance=perfil_mfa, usuario=request.user, perfil_mfa=perfil_mfa)

    context = {
        "form": form,
        "perfil_mfa": perfil_mfa,  # Estado real de la BD (recargado si hay errores)
        "qr_url": request.build_absolute_uri(f"/seguridad/mfa/qr/{perfil_mfa.pk}/"),
    }
    return render(request, "configurar_mfa.html", context)


@login_required
def generar_qr_mfa(request, perfil_id):
    """Vista para generar código QR de MFA.

    Args:
        request: Objeto HttpRequest de Django.
        perfil_id: ID del perfil MFA.

    Returns:
        HttpResponse: Imagen PNG del código QR.

    """
    perfil_mfa = get_object_or_404(PerfilMFA, id=perfil_id, usuario=request.user)
    return generar_qr_response(perfil_mfa)


@login_required
def verificar_mfa_transaccion(request):
    """Vista para verificar MFA antes de crear una transacción.

    Maneja tanto el formulario de verificación como la creación de la transacción
    una vez verificado el MFA.

    Args:
        request: Objeto HttpRequest de Django.

    Returns:
        HttpResponse: Renderiza el formulario MFA o redirige al procesamiento.

    """
    # Verificar que tenemos datos de transacción en la sesión
    datos_transaccion = request.session.get("datos_transaccion_mfa")
    if not datos_transaccion:
        messages.error(request, "No hay datos de transacción válidos. Inicia el proceso nuevamente.")
        return redirect("transacciones:realizar_transaccion")

    if request.method == "POST":
        form = CodigoMFAForm(request.POST)
        if form.is_valid():
            codigo = form.cleaned_data["codigo"]

            # Verificar el código TOTP
            if verificar_codigo_usuario(request.user, codigo):
                # Código válido - registrar intento exitoso
                registrar_intento_mfa(request.user, "pre_transaccion", "exitoso", request)

                # Limpiar datos de la sesión
                del request.session["datos_transaccion_mfa"]

                # Crear la transacción usando la lógica normal (misma que el flujo sin MFA)
                try:
                    import json
                    import time

                    from django.http import QueryDict

                    from apps.transacciones.views import api_crear_transaccion

                    # Agregar un token MFA válido para bypasear la verificación en api_crear_transaccion
                    mfa_token = str(int(time.time()))
                    request.session[f"mfa_token_valido_{mfa_token}"] = True

                    # Agregar el token a los datos
                    datos_transaccion["mfa_token"] = mfa_token

                    # Crear un GET request mock con los datos

                    # Guardar la querystring original
                    original_get = request.GET

                    # Crear nuevo QueryDict con los datos de transacción
                    query_dict = QueryDict("", mutable=True)
                    for key, value in datos_transaccion.items():
                        query_dict[key] = value

                    # Asignar temporalmente para la llamada
                    request.GET = query_dict
                    request.method = "GET"

                    # Llamar a la API de creación
                    response = api_crear_transaccion(request)

                    # Restaurar valores originales
                    request.GET = original_get
                    request.method = "POST"

                    # Procesar respuesta
                    if response.status_code == 200:
                        data = json.loads(response.content)
                        if data.get("success"):
                            return redirect("transacciones:procesar_transaccion", transaccion_id=data["transaccion_id"])
                        else:
                            error_msg = data.get("error", "Error desconocido")
                            messages.error(request, f"Error al crear la transacción: {error_msg}")
                    else:
                        messages.error(request, "Error al crear la transacción")

                    return redirect("transacciones:realizar_transaccion")

                except Exception as e:
                    messages.error(request, f"Error al crear la transacción: {e!s}")
                    return redirect("transacciones:realizar_transaccion")
            else:
                # Código inválido - registrar intento fallido
                registrar_intento_mfa(request.user, "pre_transaccion", "fallido", request)
                messages.error(request, "Código de verificación incorrecto.")
    else:
        form = CodigoMFAForm()

    context = {"form": form, "datos_transaccion": datos_transaccion}
    return render(request, "mfa_verificar_transaccion.html", context)
