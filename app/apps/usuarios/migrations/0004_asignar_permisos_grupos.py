from django.contrib.auth.management import create_permissions
from django.db import migrations


def asignar_permisos_a_grupos(apps, schema_editor):
    """Asignar permisos específicos a cada grupo de usuarios."""
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    # Los permisos deben crearse antes de aplicarlos
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, verbosity=0)
        app_config.models_module = None

    # Obtener los grupos creados
    try:
        admin_group = Group.objects.get(name="Administrador")
        analista_group = Group.objects.get(name="Analista Cambiario")
        usuario_cliente_group = Group.objects.get(name="Usuario Asociado a Cliente")
        usuario_registrado_group = Group.objects.get(name="Usuario Registrado")
    except Group.DoesNotExist:
        return  # Si no existen los grupos, no hacer nada

    # Permisos para Administrador (todos los permisos)
    # Todos los permisos de todo
    admin_permisos = Permission.objects.all()
    admin_group.permissions.set(admin_permisos)

    # Permisos para Analista Cambiario
    analista_permisos = Permission.objects.filter(
        codename__in=[
            "view_usuario",
            "view_cliente",
            "view_tipocliente",
            "change_cliente",  # Puede modificar datos de clientes
        ],
    )
    analista_group.permissions.set(analista_permisos)

    # Permisos para Usuario Asociado a Cliente
    usuario_cliente_permisos = Permission.objects.filter(
        codename__in=[
            "view_cliente",  # Solo puede ver los datos del cliente al que está asociado
        ],
    )
    usuario_cliente_group.permissions.set(usuario_cliente_permisos)

    # Permisos para Usuario Registrado (permisos mínimos)
    usuario_registrado_permisos = Permission.objects.filter(
        codename__in=[
            # Permisos básicos, puede que no necesite ninguno específico
        ],
    )
    usuario_registrado_group.permissions.set(usuario_registrado_permisos)


class Migration(migrations.Migration):
    """Migración para asignar permisos a los grupos de usuarios."""

    dependencies = [
        ("usuarios", "0003_insertar_grupos"),
    ]

    operations = [
        migrations.RunPython(asignar_permisos_a_grupos),
    ]
