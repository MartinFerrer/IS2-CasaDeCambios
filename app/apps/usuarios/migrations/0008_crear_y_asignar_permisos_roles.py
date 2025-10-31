"""Migración de datos: asignar todos los permisos al grupo 'Administrador'.

Esta migración asegura que el grupo denominado "Administrador" tenga
asignados todos los permisos existentes en el sistema. Es idempotente y
puede ejecutarse varias veces sin efectos adversos.
"""

from django.contrib.auth.management import create_permissions
from django.db import migrations


def asignar_permisos(apps, schema_editor):
    """Asignar todos los permisos actuales al grupo Administrador.

    Se crean previamente los permisos de cada app (si fuera necesario)
    y luego se asignan todos los permisos al grupo Administrador.
    """
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    # Garantizar que los permisos estén creados para todas las aplicaciones
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, verbosity=0)
        app_config.models_module = None

    # Crear permisos custom añadidos en este PR (si no existen).
    # Están asociados a content types ya existentes en las apps correspondientes.
    ContentType = apps.get_model("contenttypes", "ContentType")

    custom_permisos = [
        # (codename, nombre legible, app_label, modelo)
        ("change_comisiones", "Modificar comisiones", "usuarios", "tipocliente"),
        ("change_limites", "Modificar límites del sistema", "transacciones", "limitetransacciones"),
        ("view_reportes", "Ver reportes", "transacciones", "transaccion"),
        ("generate_reportes", "Generar reportes", "transacciones", "transaccion"),
        ("asociar_cliente", "Asociar cliente a usuario", "usuarios", "usuario"),
        ("desasociar_cliente", "Desasociar cliente de usuario", "usuarios", "usuario"),
        ("view_rol", "Ver roles", "auth", "group"),
        ("asignar_permiso_rol", "Asignar permiso a rol", "auth", "group"),
        ("desasignar_permiso_rol", "Desasignar permiso de rol", "auth", "group"),
    ]

    for codename, nombre, app_label, model in custom_permisos:
        try:
            ct = ContentType.objects.filter(app_label=app_label, model=model).first()
            if ct is None:
                # Intentar por app_label si no encontramos el modelo exacto
                ct = ContentType.objects.filter(app_label=app_label).first()
            if ct is None:
                # No existe content type apropiado en este momento; saltar
                continue
            if not Permission.objects.filter(codename=codename, content_type=ct).exists():
                Permission.objects.create(codename=codename, name=nombre, content_type=ct)
        except Exception:
            # No interrumpir la migración por un permiso fallido
            continue

    # Asignar permisos a roles específicos además de Administrador
    # Definimos listas de codenames razonables para cada rol. Si algún
    # codename no existe en la tabla Permission, simplemente no será asignado.
    analista_codenames = [
        "add_divisa",
        "change_divisa",
        "delete_divisa",
        "view_divisa",
        "add_tasacambio",
        "change_tasacambio",
        "delete_tasacambio",
        "view_tasacambio",
        "add_tasacambiohistorial",
        "change_tasacambiohistorial",
        "delete_tasacambiohistorial",
        "view_tasacambiohistorial",
        "view_reportes",
        "generate_reportes",
    ]

    usuario_asociado_codenames = [
        "add_transaccion",
        "change_transaccion",
        "view_transaccion",
    ]

    # Crear/obtener grupos y asignar permisos filtrando por codename
    grupo_analista, _ = Group.objects.get_or_create(name="Analista Cambiario")
    permisos_analista = Permission.objects.filter(codename__in=analista_codenames)
    grupo_analista.permissions.set(permisos_analista)

    grupo_usuario_asociado, _ = Group.objects.get_or_create(name="Usuario Asociado a Cliente")
    permisos_usuario_asociado = Permission.objects.filter(codename__in=usuario_asociado_codenames)
    grupo_usuario_asociado.permissions.set(permisos_usuario_asociado)

    # Finalmente, asignar todos los permisos actuales (incluidos los custom creados)
    # al grupo Administrador
    grupo_admin, _ = Group.objects.get_or_create(name="Administrador")
    permisos = Permission.objects.all()
    grupo_admin.permissions.set(permisos)


class Migration(migrations.Migration):
    """Migración que asigna todos los permisos al grupo Administrador."""

    dependencies = [
        ("usuarios", "0007_alter_cliente_ruc"),
    ]

    operations = [
        migrations.RunPython(asignar_permisos, migrations.RunPython.noop),
    ]
