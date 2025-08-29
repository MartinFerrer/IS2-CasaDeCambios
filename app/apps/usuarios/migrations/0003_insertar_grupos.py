from django.db import migrations


def crear_grupos_y_asociar(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    # Crear grupos
    roles = [
        "Usuario Registrado",
        "Usuario Asociado a Cliente",
        "Analista Cambiario",
        "Administrador",
    ]
    grupos = {}
    for nombre in roles:
        grupo, _ = Group.objects.get_or_create(name=nombre)
        grupos[nombre] = grupo

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0002_insertar_tipo_clientes"),
    ]
    operations = [
        migrations.RunPython(crear_grupos_y_asociar),
    ]
