from django.db import migrations


def create_pyg_divisa(apps, schema_editor):
    """Crea la divisa por defecto "PYG" si no existe."""
    Divisa = apps.get_model("operaciones", "Divisa")
    try:
        # Intenta obtener la divisa con código 'PYG'
        Divisa.objects.get(codigo="PYG")
    except Divisa.DoesNotExist:
        # Si no existe, la crea con los datos por defecto
        Divisa.objects.create(codigo="PYG", nombre="Guaraní", simbolo="₲")


def remove_pyg_divisa(apps, schema_editor):
    """Elimina la divisa por defecto "PYG"."""
    Divisa = apps.get_model("operaciones", "Divisa")
    try:
        # Intenta obtener la divisa con código 'PYG' y la elimina
        pyg = Divisa.objects.get(codigo="PYG")
        pyg.delete()
    except Divisa.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        # Asegúrate de que esta dependencia apunte a la migración donde se creó el modelo Divisa.
        ("operaciones", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_pyg_divisa, reverse_code=remove_pyg_divisa),
    ]
