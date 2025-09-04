"""Vistas para la aplicación panel_admin.

Este módulo contiene operaciones CRUD para los modelos Usuario, Cliente y Rol,
así como la lógica de asociación entre Cliente y Usuario.
"""

from django.contrib.auth.models import Group
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render

from apps.usuarios.models import Cliente, TipoCliente, Usuario

from .forms import ClienteForm, UsuarioForm


def panel_inicio(request: HttpRequest) -> object:
    """Renderiza la página de inicio del panel de administración.

    Args:
        request: HttpRequest object.

    Returns:
        HttpResponse: Rendered panel_inicio.html template.

    """
    return render(request, "panel_inicio.html")


# CRUD de Usuarios
def usuario_list(request: HttpRequest) -> object:
    """Renderiza la lista de usuarios y roles en el panel de administración.

    Args:
        request: HttpRequest object.

    Returns:
        HttpResponse: Rendered usuario_list.html template.

    """
    usuarios = Usuario.objects.all()
    grupos = Group.objects.all()
    return render(request, "usuario_list.html", {"usuarios": usuarios, "grupos": grupos})


def usuario_create(request: HttpRequest) -> object:
    """Crea un nuevo usuario en el panel de administración.

    Args:
        request: HttpRequest object.

    Returns:
        HttpResponse: Rendered usuario_list.html template or redirect to usuario_listar.

    """
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            form.save()  # Django maneja automáticamente los campos ManyToMany
            return redirect("usuario_listar")
    else:
        form = UsuarioForm()
    usuarios = Usuario.objects.all()
    grupos = Group.objects.all()
    return render(request, "usuario_list.html", {"usuarios": usuarios, "grupos": grupos, "form": form})


def usuario_edit(request: HttpRequest, pk: int) -> object:
    """Edita un usuario existente en el panel de administración.

    Args:
        request: HttpRequest object.
        pk: int, identificador primario del usuario a editar.

    Returns:
        HttpResponse: Renderiza el template usuario_list.html con el formulario de edición.

    """
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == "POST":
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()  # Django maneja automáticamente los campos ManyToMany
            return redirect("usuario_listar")
    else:
        form = UsuarioForm(instance=usuario)  # Inicializar con datos del usuario
    usuarios = Usuario.objects.all()
    grupos = Group.objects.all()
    return render(request, "usuario_list.html", {"usuarios": usuarios, "grupos": grupos, "form": form})


def usuario_delete(request: HttpRequest, pk: int) -> object:
    """Elimina un usuario existente en el panel de administración.

    Args:
        request: HttpRequest object.
        pk: int, identificador primario del usuario a eliminar.

    Returns:
        HttpResponse: Redirige a la lista de usuarios o renderiza el template usuario_list.html.

    """
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == "POST":
        usuario.delete()
        return redirect("usuario_listar")
    usuarios = Usuario.objects.all()
    grupos = Group.objects.all()
    return render(request, "usuario_list.html", {"usuarios": usuarios, "grupos": grupos})


# CRUD de Roles
def rol_list(request: HttpRequest) -> object:
    """Renderiza la lista de roles (grupos) y sus permisos asociados.

    Args:
        request: HttpRequest object.

    Returns:
        HttpResponse: Rendered rol_list.html template.

    """
    grupos = Group.objects.prefetch_related("permissions").all()
    return render(request, "rol_list.html", {"grupos": grupos})


# CRUD de Clientes
def cliente_list(request: HttpRequest) -> object:
    """Renderiza la lista de clientes, tipos de cliente y usuarios en el panel de administración.

    Args:
        request: HttpRequest object.

    Returns:
        HttpResponse: Rendered cliente_list.html template.

    """
    clientes = Cliente.objects.all()
    tipos_cliente = TipoCliente.objects.all()
    usuarios = Usuario.objects.all()
    return render(
        request,
        "cliente_list.html",
        {"clientes": clientes, "tipos_cliente": tipos_cliente, "usuarios": usuarios},
    )


def cliente_create(request: HttpRequest) -> object:
    """Valida el formulario de creación de cliente y renderiza la lista de clientes con el nuevo cliente.

    Args:
        request: HttpRequest object.

    Returns:
        HttpResponse: Rendered cliente_list.html template.

    """
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
    return render(
        request,
        "cliente_list.html",
        {"clientes": clientes, "tipos_cliente": tipos_cliente, "usuarios": usuarios, "form": form},
    )


def cliente_edit(request: HttpRequest, pk: int) -> object:
    """Valida el formulario de creación de cliente y renderiza la lista de clientes con el nuevo cliente.

    Args:
        request: HttpRequest object.
        pk: int, identificador primario del cliente a editar.

    Returns:
        HttpResponse: Rendered cliente_list.html template.

    """
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
    return render(
        request,
        "cliente_list.html",
        {"clientes": clientes, "tipos_cliente": tipos_cliente, "usuarios": usuarios, "form": form},
    )


def cliente_delete(request: HttpRequest, pk: int) -> object:
    """Elimina al cliente y renderiza la lista de clientes actualizada.

    Args:
        request: HttpRequest object.
        pk: int, identificador primario del cliente a eliminar.

    Returns:
        HttpResponse: Rendered cliente_list.html template.

    """
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        cliente.delete()
        return redirect("cliente_listar")
    clientes = Cliente.objects.all()
    tipos_cliente = TipoCliente.objects.all()
    usuarios = Usuario.objects.all()
    return render(
        request,
        "cliente_list.html",
        {"clientes": clientes, "tipos_cliente": tipos_cliente, "usuarios": usuarios},
    )


def asociar_cliente_usuario_form(request: HttpRequest) -> object:
    """Muestra el formulario para asociar un cliente a un usuario.

    Args:
        request: HttpRequest object.

    Returns:
        HttpResponse: Rendered cliente_list.html template.

    """
    clientes = Cliente.objects.all()
    usuarios = Usuario.objects.all()

    # Para cada usuario, calcular los clientes disponibles (que no están asociados)
    for usuario in usuarios:
        usuario.clientes_disponibles = clientes.exclude(id__in=usuario.clientes.values_list("id", flat=True))
        # También guardar referencia a los clientes asociados para facilitar la desasociación
        usuario.clientes_asociados = usuario.clientes.all()

    return render(request, "asociar_cliente_usuario.html", {"clientes": clientes, "usuarios": usuarios})


def asociar_cliente_usuario_post(request: HttpRequest, usuario_id: int) -> object:
    """Asocia un cliente a un usuario.

    Args:
        request: HttpRequest object.
        usuario_id: int, identificador del usuario a asociar con el cliente.

    Returns:
        HttpResponse: Rendered cliente_list.html template.

    """
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        cliente = Cliente.objects.get(pk=cliente_id)
        usuario = Usuario.objects.get(pk=usuario_id)
        cliente.usuarios.add(usuario)
        return redirect("asociar_cliente_usuario_form")
    return redirect("asociar_cliente_usuario_form")


def desasociar_cliente_usuario(request: HttpRequest, usuario_id: int) -> object:
    """Desasocia un cliente a un usuario.

    Args:
        request: HttpRequest object.
        usuario_id: int, identificador del usuario a desasociar del cliente.

    Returns:
        HttpResponse: Rendered cliente_list.html template.

    """
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        cliente = Cliente.objects.get(pk=cliente_id)
        usuario = Usuario.objects.get(pk=usuario_id)
        cliente.usuarios.remove(usuario)
        return redirect("asociar_cliente_usuario_form")
    return redirect("asociar_cliente_usuario_form")
