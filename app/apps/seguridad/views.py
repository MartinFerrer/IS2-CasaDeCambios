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
