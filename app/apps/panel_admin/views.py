"""Vistas para la aplicación panel_admin.

Este módulo contiene operaciones CRUD para los modelos Usuario, Cliente y Rol,
así como la lógica de asociación entre Cliente y Usuario.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import pycountry
from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from forex_python.converter import CurrencyCodes

from apps.operaciones.forms import DivisaForm, TasaCambioForm
from apps.operaciones.models import Divisa, TasaCambio, TasaCambioHistorial
from apps.transacciones.models import EntidadFinanciera, LimiteTransacciones
from apps.usuarios.models import Cliente, TipoCliente, Usuario

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
        - EntidadFinanciera: Gestión de entidades financieras
        - LimiteTransacciones: Configuración de límites de transacciones

    Args:
        request: HttpRequest object.

    Retorna:
        HttpResponse: Rendered configuracion.html template.

    """
    tipos_clientes = TipoCliente.objects.all()
    entidades = EntidadFinanciera.objects.all().order_by("tipo", "nombre")
    limite_actual = LimiteTransacciones.get_limite_actual()
    historial_limites = LimiteTransacciones.objects.all().order_by("-fecha_modificacion")

    return render(
        request,
        "configuracion.html",
        {
            "tipos_clientes": tipos_clientes,
            "entidades": entidades,
            "limite_actual": limite_actual,
            "historial_limites": historial_limites,
        },
    )


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


@require_POST
def guardar_limites(request: HttpRequest) -> HttpResponse:
    """Guarda los límites de transacciones enviados por el formulario.

    Args:
        request (HttpRequest): Petición HTTP POST con 'limite_diario' y 'limite_mensual'.

    Retorna:
        HttpResponse: Redirige a 'configuracion' con mensaje de éxito o error.

    """
    limite_diario_str = request.POST.get("limite_diario")
    limite_mensual_str = request.POST.get("limite_mensual")

    if not limite_diario_str or not limite_mensual_str:
        messages.error(request, "Faltan valores en el formulario de límites.")
        return redirect("configuracion")

    try:
        limite_diario = Decimal(limite_diario_str).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        limite_mensual = Decimal(limite_mensual_str).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        messages.error(request, "Los valores ingresados no son válidos.")
        return redirect("configuracion")

    try:
        with transaction.atomic():
            limite = LimiteTransacciones(limite_diario=limite_diario, limite_mensual=limite_mensual)
            limite.full_clean()  # Usa las validaciones del modelo
            limite.save()

        messages.success(
            request,
            f"Límites actualizados exitosamente. "
            f"Diario: ₲{limite.limite_diario:,.0f}, "
            f"Mensual: ₲{limite.limite_mensual:,.0f}",
        )
    except ValidationError as e:
        for error in e.messages:
            messages.error(request, error)
    except Exception as e:
        messages.error(request, f"Error al guardar los límites: {e}")

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
            usuario = form.save(commit=False)
            usuario.save()

            # Obtener los grupos seleccionados del formulario
            grupos_seleccionados = form.cleaned_data["groups"]

            # Limpiar grupos existentes y agregar los seleccionados
            usuario.groups.clear()
            usuario.groups.add(*grupos_seleccionados)

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
            # Guardar el usuario sin los grupos primero
            usuario = form.save(commit=False)
            usuario.save()

            # Verificar si el usuario tenía el rol "Usuario Asociado a Cliente"
            usuario_asociado_grupo = Group.objects.filter(name="Usuario Asociado a Cliente").first()
            tenia_usuario_asociado = usuario_asociado_grupo and usuario_asociado_grupo in usuario.groups.all()

            # Obtener los grupos seleccionados del formulario
            grupos_seleccionados = form.cleaned_data["groups"]

            # Limpiar grupos existentes y agregar los seleccionados
            usuario.groups.clear()
            usuario.groups.add(*grupos_seleccionados)

            # Si tenía el rol "Usuario Asociado a Cliente", preservarlo
            if tenia_usuario_asociado and usuario_asociado_grupo:
                usuario.groups.add(usuario_asociado_grupo)

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

        # Agregar rol de Usuario Asociado a Cliente
        try:
            rol_usuario_asociado = Group.objects.get(name="Usuario Asociado a Cliente")
            usuario.groups.add(rol_usuario_asociado)
        except Group.DoesNotExist:
            pass  # El grupo no existe, continuar sin cambiar roles

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

        # Quitar rol de Usuario Asociado a Cliente si ya no tiene clientes asociados
        try:
            rol_usuario_asociado = Group.objects.get(name="Usuario Asociado a Cliente")

            # Verificar si el usuario ya no tiene clientes asociados
            clientes_asociados = Cliente.objects.filter(usuarios=usuario)
            if not clientes_asociados.exists():
                usuario.groups.remove(rol_usuario_asociado)
        except Group.DoesNotExist:
            pass  # El grupo no existe, continuar sin cambiar roles

        return redirect("asociar_cliente_usuario_form")
    return redirect("asociar_cliente_usuario_form")


# Sección de Divisas:


def crear_divisa(request):
    """View para crear una nueva divisa.

    Argumento:
        request: La solicitud HTTP.
    Retorna:
        HttpResponse: el formulario de creación o la redirección después de guardar.

    """
    if request.method == "POST":
        form = DivisaForm(request.POST)
        if form.is_valid():
            divisa = form.save()
            return JsonResponse(
                {
                    "success": True,
                    "message": "Divisa creada exitosamente",
                    "divisa": {
                        "pk": str(divisa.pk),
                        "codigo": divisa.codigo,
                        "nombre": divisa.nombre,
                        "simbolo": divisa.simbolo,
                        "estado": divisa.estado,
                    },
                },
                status=201,
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    form = DivisaForm()
    return render(request, "divisa_list.html", {"form": form})


def edit_divisa(request, pk):
    """View para editar una divisa existente.

    Argumentos:
        request: La solicitud HTTP.
        pk: El identificador de la divisa a editar.
    Retorna:
        HttpResponse: el formulario de edición o la redirección después de guardar.

    """
    divisa = get_object_or_404(Divisa, pk=pk)
    if request.method == "POST":
        divisa.nombre = request.POST.get("nombre")
        divisa.simbolo = request.POST.get("simbolo")
        divisa.estado = request.POST.get("estado")
        divisa.save()
        return redirect("divisa_list")

    return redirect("divisa_list")


def delete_divisa(request, pk):
    """View para eliminar una divisa específica.

    Argumento:
        request: La solicitud HTTP.
        pk: El identificador de la divisa a eliminar.
    Retorna:
        HttpResponse: Redirige a la lista de divisas después de eliminar.

    """
    divisa = get_object_or_404(Divisa, pk=pk)
    if request.method == "POST":
        divisa.delete()
        return redirect("divisa_list")
    return redirect("divisa_detail", pk=pk)


def divisa_detail(request, pk):
    """View para mostrar los detalles de una divisa específica.

    Argumento:
        request: La solicitud HTTP.
        pk: El identificador de la divisa a mostrar.
    Retorna:
        HttpResponse: Renderiza el template divisa_detalle.html con el contexto de la divisa.

    """
    divisa = get_object_or_404(Divisa, pk=pk)
    return render(request, "divisa_detalle.html", {"divisa": divisa})


def divisa_listar(request: HttpRequest) -> object:
    """Muestra el listado de todas las divisas en el sistema.

    Argumentos:
        request: La solicitud HTTP.

    Retorna:
        HttpResponse: La página HTML con la lista de divisas.
    """
    divisas = Divisa.objects.all().order_by("codigo")
    print(f"DEBUG divisa_listar: Found {divisas.count()} currencies in database")
    for divisa in divisas:
        print(f"DEBUG: {divisa.pk} - {divisa.codigo} - {divisa.nombre}")
    return render(request, "divisa_list.html", {"object_list": divisas})


def obtener_divisas(request: HttpRequest) -> JsonResponse:
    """Obtiene las divisas disponibles en el sistema y las devuelve como un JSON.

    Esta vista utiliza la librería `pycountry` para obtener una lista de códigos
    ISO de divisas.

    Argumentos:
        request: La solicitud HTTP.

    Returns:
        JsonResponse: Una respuesta HTTP con una lista de diccionarios de divisas.

    """
    c = CurrencyCodes()
    data = []
    for currency in pycountry.currencies:
        codigo = getattr(currency, "alpha_3", None)
        if not codigo:
            continue
        nombre = getattr(currency, "name", "Desconocida")
        simbolo = c.get_symbol(codigo)
        data.append({"codigo": codigo, "nombre": nombre, "simbolo": simbolo})

    return JsonResponse(data, safe=False)


# CRUD de Entidades de Medios financiero
def entidad_create(request: HttpRequest) -> HttpResponse:
    """Crea una nueva entidad de medio financiero.

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
            if EntidadFinanciera.objects.filter(nombre=nombre, tipo=tipo).exists():
                messages.error(request, f"Ya existe una entidad {tipo} con el nombre '{nombre}'.")
                return redirect("configuracion")

            EntidadFinanciera.objects.create(
                nombre=nombre, tipo=tipo, comision_compra=comision_compra, comision_venta=comision_venta, activo=activo
            )
            messages.success(request, f"Entidad '{nombre}' creada exitosamente.")

        except (ValueError, InvalidOperation):
            messages.error(request, "Los valores de comisión deben ser números válidos.")
        except Exception as e:
            messages.error(request, f"Error al crear la entidad: {e}")

    return redirect("configuracion")


def entidad_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edita una entidad financiera existente.

    Args:
        request: HttpRequest object.
        pk: int, identificador primario de la entidad a editar.

    Retorna:
        HttpResponse: Redirect to configuracion with entidades tab.

    """
    entidad = get_object_or_404(EntidadFinanciera, pk=pk)

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
            if EntidadFinanciera.objects.filter(nombre=nombre, tipo=tipo).exclude(pk=pk).exists():
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
    """Elimina una entidad de medio financiero.

    Args:
        request: HttpRequest object.
        pk: int, identificador primario de la entidad a eliminar.

    Retorna:
        HttpResponse: Redirect to configuracion with entidades tab.

    """
    entidad = get_object_or_404(EntidadFinanciera, pk=pk)

    if request.method == "POST":
        try:
            # Verificar si la entidad está siendo usada por algún medio financiero
            from apps.transacciones.models import BilleteraElectronica, CuentaBancaria, TarjetaCredito

            en_uso = (
                TarjetaCredito.objects.filter(entidad=entidad).exists()
                or CuentaBancaria.objects.filter(entidad=entidad).exists()
                or BilleteraElectronica.objects.filter(entidad=entidad).exists()
            )

            if en_uso:
                messages.error(
                    request,
                    f"No se puede eliminar la entidad '{entidad.nombre}' porque está siendo utilizada por medios financiero existentes.",
                )
            else:
                nombre = entidad.nombre
                entidad.delete()
                messages.success(request, f"Entidad '{nombre}' eliminada exitosamente.")

        except Exception as e:
            messages.error(request, f"Error al eliminar la entidad: {e}")

    return redirect("configuracion")


# CRUD Tasas de Cambio


def tasa_cambio_listar(request: HttpRequest) -> object:
    """Renderiza la página de listado de tasas de cambio.

    Args:
        request: Objeto HttpRequest.

    Retorna:
        HttpResponse: Renderiza el template tasa_cambio_list.html con el contexto de las tasas de cambio.

    """
    tasas = TasaCambio.objects.all().order_by("-fecha_actualizacion")
    return render(request, "tasa_cambio_list.html", {"tasas_de_cambio": tasas})


def tasa_cambio_crear(request: HttpRequest):
    """Crea una nueva tasa de cambio.

    Argumento:
        request: Objeto HttpRequest.

    Retorna:
        HttpResponse: Redirige al listado de tasas o renderiza el formulario de creación.

    """
    if request.method == "POST":
        form = TasaCambioForm(request.POST)
        if form.is_valid():
            nueva_tasa = form.save()
            # Guardar registro inicial en el historial
            TasaCambioHistorial.objects.create(
                tasa_cambio_original=nueva_tasa,
                divisa_origen=nueva_tasa.divisa_origen,
                divisa_destino=nueva_tasa.divisa_destino,
                precio_base=nueva_tasa.precio_base,
                comision_compra=nueva_tasa.comision_compra,
                comision_venta=nueva_tasa.comision_venta,
                activo=nueva_tasa.activo,
                motivo="Creación de Tasa",
                fecha_registro=timezone.now(),
            )
            return redirect("tasa_cambio_listar")
    else:
        form = TasaCambioForm()
    return render(request, "tasa_cambio_form.html", {"form": form})


def tasa_cambio_editar(request: HttpRequest, pk: str) -> object:
    """Edita una tasa de cambio existente y guarda los cambios en el historial.

    Argumento:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a editar.

    Retorna:
        HttpResponse: Redirige al listado de tasas o renderiza el formulario de edición.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)

    # Guardar valores originales para comparar
    valores_originales = {
        "precio_base": tasa.precio_base,
        "comision_compra": tasa.comision_compra,
        "comision_venta": tasa.comision_venta,
        "activo": tasa.activo,
    }

    if request.method == "POST":
        form = TasaCambioForm(request.POST, instance=tasa)
        if form.is_valid():
            # Verificar si hubo cambios reales
            cambios = []
            if tasa.precio_base != valores_originales["precio_base"]:
                cambios.append(f"Precio base: {valores_originales['precio_base']} → {tasa.precio_base}")
            if tasa.comision_compra != valores_originales["comision_compra"]:
                cambios.append(f"Comisión compra: {valores_originales['comision_compra']} → {tasa.comision_compra}")
            if tasa.comision_venta != valores_originales["comision_venta"]:
                cambios.append(f"Comisión venta: {valores_originales['comision_venta']} → {tasa.comision_venta}")
            if tasa.activo != valores_originales["activo"]:
                cambios.append(
                    f"Estado: {'Activo' if valores_originales['activo'] else 'Inactivo'} → {'Activo' if tasa.activo else 'Inactivo'}"
                )

            # Solo guardar en historial si hubo cambios
            if cambios:
                tasa_editada = form.save()
                # Actualizar fecha de modificación
                tasa_editada.fecha_actualizacion = timezone.now()
                tasa_editada.save()

                # Guardar en el historial con detalles de los cambios
                motivo_detallado = f"Edición de Tasa - Cambios: {'; '.join(cambios)}"
                TasaCambioHistorial.objects.create(
                    tasa_cambio_original=tasa_editada,
                    divisa_origen=tasa_editada.divisa_origen,
                    divisa_destino=tasa_editada.divisa_destino,
                    precio_base=tasa_editada.precio_base,
                    comision_compra=tasa_editada.comision_compra,
                    comision_venta=tasa_editada.comision_venta,
                    activo=tasa_editada.activo,
                    motivo=motivo_detallado,
                    fecha_registro=timezone.now(),
                )
            return redirect("tasa_cambio_listar")
    else:
        form = TasaCambioForm(instance=tasa)
    return render(request, "tasa_cambio_form.html", {"form": form})


def tasa_cambio_desactivar(request: HttpRequest, pk: str) -> object:
    """Desactiva una tasa de cambio existente.

    Argumento:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a desactivar.

    Retorna:
        HttpResponse: Redirige al listado de tasas.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)
    if request.method == "POST" and tasa.activo:  # Solo desactivar si está activa
        tasa.activo = False
        tasa.fecha_actualizacion = timezone.now()
        tasa.save()
        # Guardar en el historial
        TasaCambioHistorial.objects.create(
            tasa_cambio_original=tasa,
            divisa_origen=tasa.divisa_origen,
            divisa_destino=tasa.divisa_destino,
            precio_base=tasa.precio_base,
            comision_compra=tasa.comision_compra,
            comision_venta=tasa.comision_venta,
            activo=tasa.activo,
            motivo="Desactivación de Tasa",
            fecha_registro=timezone.now(),
        )
    return redirect("tasa_cambio_listar")


def tasa_cambio_activar(request: HttpRequest, pk: str) -> object:
    """Activa una tasa de cambio existente.

    Argumento:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a activar.

    Retorna:
        HttpResponse: Redirige al listado de tasas.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)
    if request.method == "POST" and not tasa.activo:  # Solo activar si está inactiva:
        tasa.activo = True
        tasa.fecha_actualizacion = timezone.now()
        tasa.save()
        # Guardar en el historial
        TasaCambioHistorial.objects.create(
            tasa_cambio_original=tasa,
            divisa_origen=tasa.divisa_origen,
            divisa_destino=tasa.divisa_destino,
            precio_base=tasa.precio_base,
            comision_compra=tasa.comision_compra,
            comision_venta=tasa.comision_venta,
            activo=tasa.activo,
            motivo="Activación de Tasa",
            fecha_registro=timezone.now(),
        )
    return redirect("tasa_cambio_listar")
