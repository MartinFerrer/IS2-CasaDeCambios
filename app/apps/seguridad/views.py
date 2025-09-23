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


# -----------------------------
# REGISTRO con verificación
# -----------------------------
def registro_view(request):
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


# -----------------------------
# VERIFICAR CUENTA
# -----------------------------
def verificar_cuenta(request, uid, token):
    user = get_object_or_404(Usuario, pk=uid)
    if token_generator.check_token(user, token):
        user.activo = True
        user.is_active = True
        user.save()
        messages.success(request, "Tu cuenta ha sido verificada. Ya puedes iniciar sesión.")
        return redirect("seguridad:login")
    messages.error(request, "El enlace de verificación no es válido o ha expirado.")
    return redirect("seguridad:registro")


# -----------------------------
# LOGIN
# -----------------------------
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            if not user.is_active or not user.is_active:
                messages.error(request, "Debes verificar tu correo antes de iniciar sesión.")
                return redirect("seguridad:login")

            # Loguear usuario
            login(request, user)

            # Redirigir a la selección de cliente
            return redirect("seguridad:seleccionar_cliente")

        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, "login.html")


# -----------------------------
# LOGOUT
# -----------------------------
def logout_view(request):
    logout(request)
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect("seguridad:login")


# -----------------------------
# CAMBIAR CLIENTE
# -----------------------------
@login_required
def cambiar_cliente(request):
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        if request.user.clientes.filter(id=cliente_id).exists():
            request.session["cliente_id"] = int(cliente_id)
            messages.success(request, "Cliente cambiado correctamente.")
            return redirect("presentacion:home")
        messages.error(request, "Cliente inválido.")
    clientes = request.user.clientes.all()
    return render(request, "cambiar_cliente.html", {"clientes": clientes})


# -----------------------------
# OBTENER CLIENTES (AJAX)
# -----------------------------
@csrf_exempt
def obtener_clientes(request):
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
    user = request.user
    clientes = user.clientes.all()

    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        if clientes.filter(id=cliente_id).exists():
            request.session["cliente_id"] = int(cliente_id)
            messages.success(request, "Cliente seleccionado correctamente.")
            return redirect("presentacion:home")
        else:
            messages.error(request, "Cliente inválido")

    return render(request, "seleccionar_cliente.html", {"clientes": clientes})
