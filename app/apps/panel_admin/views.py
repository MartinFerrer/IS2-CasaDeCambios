from django.shortcuts import get_object_or_404, redirect, render

from .models import Usuario, Rol, Cliente, TipoCliente
from .forms import UsuarioForm, ClienteForm
from django.forms import ModelForm

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
    else:
        form = UsuarioForm()
    usuarios = Usuario.objects.all()
    roles = Rol.objects.all()
    return render(request, "usuario_list.html", {"usuarios": usuarios, "roles": roles, "form": form})

def usuario_edit(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == "POST":
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            return redirect("usuario_listar")
    else:
        form = UsuarioForm()
    usuarios = Usuario.objects.all()
    roles = Rol.objects.all()
    return render(request, "usuario_list.html", {"usuarios": usuarios, "roles": roles, "form": form})

def usuario_delete(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == "POST":
        usuario.delete()
        return redirect("usuario_listar")
    usuarios = Usuario.objects.all()
    roles = Rol.objects.all()
    return render(request, "usuario_list.html", {"usuarios": usuarios, "roles": roles})

# Crud de Roles
def rol_list(request):
    return render(request, "rol_list.html")

def rol_create(request):
    return render(request, "rol_form.html")

def rol_edit(request, pk):
    return render(request, "rol_form.html")

def rol_delete(request, pk):
    return render(request, "rol_confirm_delete.html")

# Clientes
def cliente_list(request):
    clientes = Cliente.objects.all()
    tipos_cliente = TipoCliente.objects.all()
    usuarios = Usuario.objects.all()
    return render(request, "cliente_list.html", {
        "clientes": clientes,
        "tipos_cliente": tipos_cliente,
        "usuarios": usuarios
    })

def cliente_create(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("cliente_listar")
    else:
        form = ClienteForm()
    clientes = Cliente.objects.all()
    tipos_cliente = TipoCliente.objects.all()
    usuarios = Usuario.objects.all()
    return render(request, "cliente_list.html", {
        "clientes": clientes,
        "tipos_cliente": tipos_cliente,
        "usuarios": usuarios,
        "form": form
    })

def cliente_edit(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect("cliente_listar")
    else:
        form = ClienteForm(instance=cliente)
    clientes = Cliente.objects.all()
    tipos_cliente = TipoCliente.objects.all()
    usuarios = Usuario.objects.all()
    return render(request, "cliente_list.html", {
        "clientes": clientes,
        "tipos_cliente": tipos_cliente,
        "usuarios": usuarios,
        "form": form
    })

def cliente_delete(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        cliente.delete()
        return redirect("cliente_listar")
    clientes = Cliente.objects.all()
    tipos_cliente = TipoCliente.objects.all()
    usuarios = Usuario.objects.all()
    return render(request, "cliente_list.html", {
        "clientes": clientes,
        "tipos_cliente": tipos_cliente,
        "usuarios": usuarios
    })

def asociar_cliente_usuario_form(request):
    clientes = Cliente.objects.all()
    usuarios = Usuario.objects.all()
    
    # Para cada usuario, calcular los clientes disponibles (que no están asociados)
    for usuario in usuarios:
        usuario.clientes_disponibles = clientes.exclude(id__in=usuario.clientes.values_list('id', flat=True))
        # También guardar referencia a los clientes asociados para facilitar la desasociación
        usuario.clientes_asociados = usuario.clientes.all()
    
    return render(request, "asociar_cliente_usuario.html", {
        "clientes": clientes,
        "usuarios": usuarios
    })

def asociar_cliente_usuario_post(request, usuario_id):
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        cliente = Cliente.objects.get(pk=cliente_id)
        usuario = Usuario.objects.get(pk=usuario_id)
        cliente.usuarios.add(usuario)
        return redirect("asociar_cliente_usuario_form")
    return redirect('asociar_cliente_usuario_form')

def desasociar_cliente_usuario(request, usuario_id):
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        cliente = Cliente.objects.get(pk=cliente_id)
        usuario = Usuario.objects.get(pk=usuario_id)
        cliente.usuarios.remove(usuario)
        return redirect('asociar_cliente_usuario_form')
    return redirect('asociar_cliente_usuario_form')