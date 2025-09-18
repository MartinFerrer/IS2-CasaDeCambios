"""Vistas para la aplicación panel_admin.

Este módulo contiene operaciones CRUD para los modelos Usuario, Cliente y Rol,
así como la lógica de asociación entre Cliente y Usuario.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from apps.transacciones.models import EntidadMedioPago
from apps.usuarios.models import Cliente, TipoCliente, Usuario
from django.contrib import messages
from django.contrib.auth.models import Group
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ClienteForm, UsuarioForm


def panel_inicio(request: HttpRequest) -> HttpResponse:
    """Renderiza la página de inicio del panel de administración.

    Args:
        request: HttpRequest object.

    Retorna:
        HttpResponse: Rendered panel_inicio.html template.

    """
    return render(request, "panel_inicio.html")


def configuracion(request: HttpRequest) -> HttpResponse:
    """Renderiza la página de configuracion de opciones.

    Se pasan los siguentes queryset para la configuracion:
        - TipoCliente: Configuración de descuento sobre la comisión
        - EntidadMedioPago: Gestión de entidades de medios de pago

    Args:
        request: HttpRequest object.

    Retorna:
        HttpResponse: Rendered configuracion.html template.

    """
    tipos_clientes = TipoCliente.objects.all()
    entidades = EntidadMedioPago.objects.all().order_by('tipo', 'nombre')
    return render(request, "configuracion.html", {
        "tipos_clientes": tipos_clientes,
        "entidades": entidades
    })


@require_POST
def guardar_comisiones(request: HttpRequest) -> HttpResponse:
    """Guarda los descuentos de comisión enviados por el formulario.

    Lee los campos POST generados dinámicamente por la plantilla para cada
    TipoCliente con el patrón:
      - 'descuento_comision_<pk>'  (donde <pk> es el id del TipoCliente mostrado)

    Por cada TipoCliente mostrado en la página valida que el valor recibido
    sea un decimal entre 0.0 y 20.0 (inclusive) con 1 decimal y persiste el
    cambio en el campo `descuento_sobre_comision`.

    Args:
        request (HttpRequest): Petición HTTP POST que contiene los
            campos numéricos del formulario con los porcentajes de descuento.

    Retorna:
        HttpResponse: Redirige a la vista 'configuracion'. En caso de error
        añade mensajes mediante `django.contrib.messages` y luego redirige
        también a 'configuracion'.

    """
    tipos_clientes = TipoCliente.objects.all()

    valores_parseados = {}
    for tipo_cliente in tipos_clientes:
        campo = f"descuento_comision_{tipo_cliente.pk}"
        datos_campo = request.POST.get(campo)
        if datos_campo is None:
            messages.error(request, "Faltan valores en el formulario de comisiones.")
            return redirect("configuracion")
        try:
            # Cuantizar a tipo Decimal
            valor_decimal = Decimal(datos_campo).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            messages.error(request, f"Valor no válido para {tipo_cliente.nombre}: {datos_campo}")
            return redirect("configuracion")
        if valor_decimal < Decimal("0.0") or valor_decimal > Decimal("20.0"):
            messages.error(request, f"El valor para {tipo_cliente.nombre} debe estar entre 0 y 20.")
            return redirect("configuracion")
        valores_parseados[tipo_cliente] = valor_decimal

    # Guardar los valores de forma atómica
    try:
        with transaction.atomic():
            for tipo_obj, valor in valores_parseados.items():
                tipo_obj.descuento_sobre_comision = valor
                tipo_obj.save()
    except Exception as e:
        messages.error(request, f"Error al guardar las comisiones: {e}")
        return redirect("configuracion")

    messages.success(request, "Cambios guardados exitosamente.")
    return redirect("configuracion")


# CRUD de Usuarios
def usuario_list(request: HttpRequest) -> HttpResponse:
    """Renderiza la lista de usuarios y roles en el panel de administración.

    Args:
        request: HttpRequest object.

    Retorna:
        HttpResponse: Rendered usuario_list.html template.

    """
    usuarios = Usuario.objects.all()
    grupos = Group.objects.all()
    return render(request, "usuario_list.html", {"usuarios": usuarios, "grupos": grupos})


def usuario_create(request: HttpRequest) -> HttpResponse:
    """Crea un nuevo usuario en el panel de administración.

    Args:
        request: HttpRequest object.

    Retorna:
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


def usuario_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edita un usuario existente en el panel de administración.

    Args:
        request: HttpRequest object.
        pk: int, identificador primario del usuario a editar.

    Retorna:
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


def usuario_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Elimina un usuario existente en el panel de administración.

    Args:
        request: HttpRequest object.
        pk: int, identificador primario del usuario a eliminar.

    Retorna:
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
def rol_list(request: HttpRequest) -> HttpResponse:
    """Renderiza la lista de roles (grupos) y sus permisos asociados.

    Args:
        request: HttpRequest object.

    Retorna:
        HttpResponse: Rendered rol_list.html template.

    """
    grupos = Group.objects.prefetch_related("permissions").all()
    return render(request, "rol_list.html", {"grupos": grupos})


# CRUD de Clientes
def cliente_list(request: HttpRequest) -> HttpResponse:
    """Renderiza la lista de clientes, tipos de cliente y usuarios en el panel de administración.

    Args:
        request: HttpRequest object.

    Retorna:
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


def cliente_create(request: HttpRequest) -> HttpResponse:
    """Valida el formulario de creación de cliente y renderiza la lista de clientes con el nuevo cliente.

    Args:
        request: HttpRequest object.

    Retorna:
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


def cliente_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Valida el formulario de creación de cliente y renderiza la lista de clientes con el nuevo cliente.

    Args:
        request: HttpRequest object.
        pk: int, identificador primario del cliente a editar.

    Retorna:
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


def cliente_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Elimina al cliente y renderiza la lista de clientes actualizada.

    Args:
        request: HttpRequest object.
        pk: int, identificador primario del cliente a eliminar.

    Retorna:
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


def asociar_cliente_usuario_form(request: HttpRequest) -> HttpResponse:
    """Muestra el formulario para asociar un cliente a un usuario.

    Args:
        request: HttpRequest object.

    Retorna:
        HttpResponse: Rendered cliente_list.html template.

    """
    clientes = Cliente.objects.all()
    usuarios = Usuario.objects.all()

    # Para cada usuario, calcular los clientes disponibles (que no están asociados)
    for usuario in usuarios:
        # TODO: solucionar implementando de otra forma para no tener errores de Pylance/Intellisense
        usuario.clientes_disponibles = clientes.exclude(id__in=usuario.clientes.values_list("id", flat=True))
        # También guardar referencia a los clientes asociados para facilitar la desasociación
        usuario.clientes_asociados = usuario.clientes.all()

    return render(request, "asociar_cliente_usuario.html", {"clientes": clientes, "usuarios": usuarios})


def asociar_cliente_usuario_post(request: HttpRequest, usuario_id: int) -> HttpResponse:
    """Asocia un cliente a un usuario.

    Args:
        request: HttpRequest object.
        usuario_id: int, identificador del usuario a asociar con el cliente.

    Retorna:
        HttpResponse: Rendered cliente_list.html template.

    """
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        cliente = Cliente.objects.get(pk=cliente_id)
        usuario = Usuario.objects.get(pk=usuario_id)
        cliente.usuarios.add(usuario)
        
        # Cambiar rol si el usuario tiene el rol "Usuario Registrado"
        try:
            rol_usuario_registrado = Group.objects.get(name="Usuario Registrado")
            rol_usuario_asociado = Group.objects.get(name="Usuario Asociado a Cliente")
            
            if rol_usuario_registrado in usuario.groups.all():
                usuario.groups.remove(rol_usuario_registrado)
                usuario.groups.add(rol_usuario_asociado)
        except Group.DoesNotExist:
            pass  # Los grupos no existen, continuar sin cambiar roles
        
        return redirect("asociar_cliente_usuario_form")
    return redirect("asociar_cliente_usuario_form")


def desasociar_cliente_usuario(request: HttpRequest, usuario_id: int) -> HttpResponse:
    """Desasocia un cliente a un usuario.

    Args:
        request: HttpRequest object.
        usuario_id: int, identificador del usuario a desasociar del cliente.

    Retorna:
        HttpResponse: Rendered cliente_list.html template.

    """
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        cliente = Cliente.objects.get(pk=cliente_id)
        usuario = Usuario.objects.get(pk=usuario_id)
        cliente.usuarios.remove(usuario)
        
        # Cambiar rol si el usuario tiene el rol "Usuario Asociado a Cliente" y ya no tiene clientes
        try:
            rol_usuario_registrado = Group.objects.get(name="Usuario Registrado")
            rol_usuario_asociado = Group.objects.get(name="Usuario Asociado a Cliente")
            
            if rol_usuario_asociado in usuario.groups.all():
                # Verificar si el usuario ya no tiene clientes asociados
                clientes_asociados = Cliente.objects.filter(usuarios=usuario)
                if not clientes_asociados.exists():
                    usuario.groups.remove(rol_usuario_asociado)
                    usuario.groups.add(rol_usuario_registrado)
        except Group.DoesNotExist:
            pass  # Los grupos no existen, continuar sin cambiar roles
        
        return redirect("asociar_cliente_usuario_form")
    return redirect("asociar_cliente_usuario_form")


# CRUD de Entidades de Medios de Pago
def entidad_create(request: HttpRequest) -> HttpResponse:
    """Crea una nueva entidad de medio de pago.

    Args:
        request: HttpRequest object.

    Retorna:
        HttpResponse: Redirect to configuracion with entidades tab.

    """
    if request.method == "POST":
        try:
            nombre = request.POST.get("nombre", "").strip()
            tipo = request.POST.get("tipo")
            comision_compra = Decimal(request.POST.get("comision_compra", "0"))
            comision_venta = Decimal(request.POST.get("comision_venta", "0"))
            activo = request.POST.get("activo") == "on"
            
            if not nombre or not tipo:
                messages.error(request, "Nombre y tipo son obligatorios.")
                return redirect("configuracion")
            
            # Verificar que no exista ya esa combinación nombre-tipo
            if EntidadMedioPago.objects.filter(nombre=nombre, tipo=tipo).exists():
                messages.error(request, f"Ya existe una entidad {tipo} con el nombre '{nombre}'.")
                return redirect("configuracion")
            
            EntidadMedioPago.objects.create(
                nombre=nombre,
                tipo=tipo,
                comision_compra=comision_compra,
                comision_venta=comision_venta,
                activo=activo
            )
            messages.success(request, f"Entidad '{nombre}' creada exitosamente.")
            
        except (ValueError, InvalidOperation):
            messages.error(request, "Los valores de comisión deben ser números válidos.")
        except Exception as e:
            messages.error(request, f"Error al crear la entidad: {e}")
    
    return redirect("configuracion")


def entidad_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edita una entidad de medio de pago existente.

    Args:
        request: HttpRequest object.
        pk: int, identificador primario de la entidad a editar.

    Retorna:
        HttpResponse: Redirect to configuracion with entidades tab.

    """
    entidad = get_object_or_404(EntidadMedioPago, pk=pk)
    
    if request.method == "POST":
        try:
            nombre = request.POST.get("nombre", "").strip()
            tipo = request.POST.get("tipo")
            comision_compra = Decimal(request.POST.get("comision_compra", "0"))
            comision_venta = Decimal(request.POST.get("comision_venta", "0"))
            activo = request.POST.get("activo") == "on"
            
            if not nombre or not tipo:
                messages.error(request, "Nombre y tipo son obligatorios.")
                return redirect("configuracion")
            
            # Verificar que no exista ya esa combinación nombre-tipo (excepto esta misma entidad)
            if EntidadMedioPago.objects.filter(nombre=nombre, tipo=tipo).exclude(pk=pk).exists():
                messages.error(request, f"Ya existe otra entidad {tipo} con el nombre '{nombre}'.")
                return redirect("configuracion")
            
            entidad.nombre = nombre
            entidad.tipo = tipo
            entidad.comision_compra = comision_compra
            entidad.comision_venta = comision_venta
            entidad.activo = activo
            entidad.save()
            
            messages.success(request, f"Entidad '{nombre}' actualizada exitosamente.")
            
        except (ValueError, InvalidOperation):
            messages.error(request, "Los valores de comisión deben ser números válidos.")
        except Exception as e:
            messages.error(request, f"Error al actualizar la entidad: {e}")
    
    return redirect("configuracion")


def entidad_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Elimina una entidad de medio de pago.

    Args:
        request: HttpRequest object.
        pk: int, identificador primario de la entidad a eliminar.

    Retorna:
        HttpResponse: Redirect to configuracion with entidades tab.

    """
    entidad = get_object_or_404(EntidadMedioPago, pk=pk)
    
    if request.method == "POST":
        try:
            # Verificar si la entidad está siendo usada por algún medio de pago
            from apps.transacciones.models import (BilleteraElectronica,
                                                   CuentaBancaria,
                                                   TarjetaCredito)
            
            en_uso = (
                TarjetaCredito.objects.filter(entidad=entidad).exists() or 
                CuentaBancaria.objects.filter(entidad=entidad).exists() or 
                BilleteraElectronica.objects.filter(entidad=entidad).exists()
            )
            
            if en_uso:
                messages.error(
                    request, 
                    f"No se puede eliminar la entidad '{entidad.nombre}' porque está siendo utilizada por medios de pago existentes."
                )
            else:
                nombre = entidad.nombre
                entidad.delete()
                messages.success(request, f"Entidad '{nombre}' eliminada exitosamente.")
                
        except Exception as e:
            messages.error(request, f"Error al eliminar la entidad: {e}")
    
    return redirect("configuracion")
