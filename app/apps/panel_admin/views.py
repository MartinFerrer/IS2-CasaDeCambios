from django.shortcuts import get_object_or_404, redirect, render

from .models import Usuario, Rol
from .forms import UsuarioForm

# View Panel inicio
def panel_inicio(request):
    return render(request, "panel_inicio.html")

# Usuarios
def usuario_list(request):
    usuarios = Usuario.objects.all()
    roles = Rol.objects.all()
    return render(request, "usuario_list.html", {"usuarios": usuarios, "roles": roles})

def usuario_create(request):
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("usuario_listar")

def usuario_edit(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == "POST":
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            return redirect("usuario_listar")

def usuario_delete(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == "POST":
        usuario.delete()
        return redirect("usuario_listar")

# Crud de Roles
def rol_list(request):
    return render(request, "rol_list.html")

def rol_create(request):
    return render(request, "rol_form.html")

def rol_edit(request, pk):
    return render(request, "rol_form.html")

def rol_delete(request, pk):
    return render(request, "rol_confirm_delete.html")
