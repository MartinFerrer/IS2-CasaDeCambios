from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from apps.usuarios.forms import CustomUserCreationForm

# -----------------------------
# REGISTRO
# -----------------------------
def registro_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()      # se guarda en la BD
            login(request, user)    # autologin
            return redirect("/admin/") # redirigir a home
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = CustomUserCreationForm()
    return render(request, "registro.html", {"form": form})


# -----------------------------
# LOGIN
# -----------------------------


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)  # 👈 email, no username

        if user is not None:
            login(request, user)
            # Redirigir automáticamente al admin si es staff
            if user.is_staff:
                return redirect("/admin/")
            else:
                return redirect("/admin/")  # o la página que quieras
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, "login.html")



# -----------------------------
# LOGOUT
# -----------------------------
def logout_view(request):
    logout(request)
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect("/seguridad/login/")
