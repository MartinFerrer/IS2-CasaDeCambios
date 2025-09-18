
from django.db import migrations


def poblar_entidades(apps, schema_editor):
    EntidadMedioPago = apps.get_model('transacciones', 'EntidadMedioPago')
    
    # Bancos principales de Argentina
    bancos = [
        {"nombre": "Banco Nacional de Fomento", "tipo": "banco", "comision_compra": 2.5, "comision_venta": 2.8},
        {"nombre": "Banco Familiar", "tipo": "banco", "comision_compra": 2.3, "comision_venta": 2.6},
        {"nombre": "Banco Itaú", "tipo": "banco", "comision_compra": 2.4, "comision_venta": 2.7},
        {"nombre": "Banco Continental", "tipo": "banco", "comision_compra": 2.8, "comision_venta": 3.1},
        {"nombre": "Banco BASA", "tipo": "banco", "comision_compra": 2.7, "comision_venta": 3.0},
        {"nombre": "BBVA", "tipo": "banco", "comision_compra": 2.9, "comision_venta": 3.2},
        {"nombre": "Banco GNB", "tipo": "banco", "comision_compra": 2.6, "comision_venta": 2.9},
        {"nombre": "Sudameris Bank", "tipo": "banco", "comision_compra": 2.8, "comision_venta": 3.1},
        {"nombre": "Ueno Bank", "tipo": "banco", "comision_compra": 2.7, "comision_venta": 3.0},
        {"nombre": "Banco Atlas", "tipo": "banco", "comision_compra": 2.5, "comision_venta": 2.8},
        {"nombre": "Zeta Banco", "tipo": "banco", "comision_compra": 2.6, "comision_venta": 2.9},
        {"nombre": "Interfisa Banco", "tipo": "banco", "comision_compra": 2.8, "comision_venta": 3.1},
    ]
    
    # Emisores de tarjetas
    emisores_tarjeta = [
        {"nombre": "Banco Nacional de Fomento", "tipo": "emisor_tarjeta", "comision_compra": 2.5, "comision_venta": 2.8},
        {"nombre": "Banco Familiar", "tipo": "emisor_tarjeta", "comision_compra": 2.3, "comision_venta": 2.6},
        {"nombre": "Banco Itaú", "tipo": "emisor_tarjeta", "comision_compra": 2.4, "comision_venta": 2.7},
        {"nombre": "Banco Continental", "tipo": "emisor_tarjeta", "comision_compra": 2.8, "comision_venta": 3.1},
        {"nombre": "Banco BASA", "tipo": "emisor_tarjeta", "comision_compra": 2.7, "comision_venta": 3.0},
        {"nombre": "BBVA", "tipo": "emisor_tarjeta", "comision_compra": 2.9, "comision_venta": 3.2},
        {"nombre": "Banco GNB", "tipo": "emisor_tarjeta", "comision_compra": 2.6, "comision_venta": 2.9},
        {"nombre": "Sudameris Bank", "tipo": "emisor_tarjeta", "comision_compra": 2.8, "comision_venta": 3.1},
        {"nombre": "Ueno Bank", "tipo": "emisor_tarjeta", "comision_compra": 2.7, "comision_venta": 3.0},
        {"nombre": "Banco Atlas", "tipo": "emisor_tarjeta", "comision_compra": 2.5, "comision_venta": 2.8},
        {"nombre": "Zeta Banco", "tipo": "emisor_tarjeta", "comision_compra": 2.6, "comision_venta": 2.9},
        {"nombre": "Interfisa Banco", "tipo": "emisor_tarjeta", "comision_compra": 2.8, "comision_venta": 3.1},
    ]
    
    # Proveedores de billeteras electrónicas
    proveedores_billetera = [
        {"nombre": "Tigo Money", "tipo": "proveedor_billetera", "comision_compra": 1.8, "comision_venta": 2.1},
        {"nombre": "ZIMPLE", "tipo": "proveedor_billetera", "comision_compra": 1.5, "comision_venta": 1.8},
        {"nombre": "Mango", "tipo": "proveedor_billetera", "comision_compra": 1.6, "comision_venta": 1.9},
        {"nombre": "Personal Pay", "tipo": "proveedor_billetera", "comision_compra": 1.7, "comision_venta": 2.0},
        {"nombre": "Upay", "tipo": "proveedor_billetera", "comision_compra": 1.4, "comision_venta": 1.7},
        {"nombre": "Eko", "tipo": "proveedor_billetera", "comision_compra": 2.0, "comision_venta": 2.3},
        {"nombre": "Billetera Bancard", "tipo": "proveedor_billetera", "comision_compra": 1.9, "comision_venta": 2.2},
        {"nombre": "Vaquita", "tipo": "proveedor_billetera", "comision_compra": 1.3, "comision_venta": 1.6},
    ]
    
    # Crear todas las entidades
    todas_las_entidades = bancos + emisores_tarjeta + proveedores_billetera
    
    for entidad_data in todas_las_entidades:
        EntidadMedioPago.objects.get_or_create(
            nombre=entidad_data["nombre"],
            tipo=entidad_data["tipo"],
            defaults={
                "comision_compra": entidad_data["comision_compra"],
                "comision_venta": entidad_data["comision_venta"],
                "activo": True
            }
        )

def eliminar_entidades(apps, schema_editor):
    EntidadMedioPago = apps.get_model('transacciones', 'EntidadMedioPago')
    EntidadMedioPago.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('transacciones', '0002_entidadmediopago_and_more'),
    ]

    operations = [
        migrations.RunPython(poblar_entidades, eliminar_entidades),
    ]
