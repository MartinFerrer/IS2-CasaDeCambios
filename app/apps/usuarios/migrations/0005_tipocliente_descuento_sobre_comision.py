"""Esta migración agrega el campo descuento_sobre_comision al modelo de TipoCliente."""

from decimal import Decimal

from django.db import migrations, models


def set_descuentos_default(apps, schema_editor):
    """Este metodo setea los valores predeterminados según el segmento del tipo de cliente."""
    TipoCliente = apps.get_model("usuarios", "TipoCliente")
    mapping = {
        "Minorista": Decimal("0.0"),
        "Corporativo": Decimal("5.0"),
        "VIP": Decimal("10.0"),
    }
    for nombre, val in mapping.items():
        tc = TipoCliente.objects.filter(nombre=nombre).first()
        if tc:
            tc.descuento_sobre_comision = val
            tc.save()
        else:
            # si por algún motivo falta el registro, lo creamos con el valor
            TipoCliente.objects.create(nombre=nombre, descuento_sobre_comision=val)


class Migration(migrations.Migration):
    """Migración que agrega el campo descuento_sobre_comision al modelo de TipoCliente."""

    dependencies = [
        ("usuarios", "0004_asignar_permisos_grupos"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipocliente",
            name="descuento_sobre_comision",
            field=models.DecimalField(decimal_places=1, default=Decimal("0.0"), max_digits=3),
            preserve_default=False,
        ),
        migrations.RunPython(set_descuentos_default, reverse_code=migrations.RunPython.noop),
    ]
