from apps.usuarios.forms import CustomUserCreationForm
from apps.usuarios.models import Usuario
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

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
            # Definir grupo de usuario creado
            grupo, _ = Group.objects.get_or_create(name="Usuario Registrado")
            user.groups.add(grupo)
            # Generar token
            token = token_generator.make_token(user)
            uid = user.pk

            # Construir enlace
            verification_link = request.build_absolute_uri(
                reverse("seguridad:verificar_cuenta", kwargs={"uid": uid, "token": token}),
            )

            # Enviar correo
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
            usuario = Usuario.objects.get(pk=user.pk)
            if not usuario.activo or not usuario.is_active:
                messages.error(request, "Debes verificar tu correo antes de iniciar sesión.")
                return redirect("seguridad:login")

            login(request, user)
            if user.is_staff:
                return redirect("/admin/")
            return redirect("/admin/")  # o página para usuarios normales
        messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, "login.html")


# -----------------------------
# LOGOUT
# -----------------------------
def logout_view(request):
    logout(request)
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect("/seguridad/login/")
