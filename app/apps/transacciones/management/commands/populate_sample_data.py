"""Django management command to populate sample data for testing.

This command creates sample data for:
- TipoCliente
- Cliente
- Usuario
- Divisa
- TasaCambio
- EntidadFinanciera
- MediosFinancieros (TarjetaCredito, CuentaBancaria, BilleteraElectronica)
"""

from datetime import date, timedelta
from decimal import Decimal

from apps.operaciones.models import Divisa, TasaCambio
from apps.transacciones.models import BilleteraElectronica, CuentaBancaria, EntidadFinanciera, TarjetaCredito
from apps.usuarios.models import Cliente, TipoCliente
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

Usuario = get_user_model()


class Command(BaseCommand):
    """Management command to populate sample data."""

    help = "Populate database with sample data for testing"

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before populating",
        )

    def handle(self, *args, **options):
        """Handle the management command."""
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            self.clear_data()

        try:
            with transaction.atomic():
                self.create_divisas()
                self.create_tasas_cambio()
                self.create_usuarios()
                self.create_clientes()
                self.create_medios_financieros()

            self.stdout.write(self.style.SUCCESS("Successfully populated database with sample data"))
        except Exception as e:
            raise CommandError(f"Error populating data: {e}")

    def clear_data(self):
        """Clear existing sample data."""
        # Clear in reverse order of dependencies
        TarjetaCredito.objects.all().delete()
        CuentaBancaria.objects.all().delete()
        BilleteraElectronica.objects.all().delete()
        # EntidadFinanciera.objects.all().delete()  # Skipped per user request
        TasaCambio.objects.all().delete()
        Cliente.objects.all().delete()
        Usuario.objects.filter(email__contains="test").delete()
        # Don't delete Divisa as they might be used by other data

    def create_divisas(self):
        """Create sample divisas."""
        self.stdout.write("Creating divisas...")

        divisas_data = [
            {"codigo": "PYG", "nombre": "Guaraní Paraguayo", "simbolo": "₲"},
            {"codigo": "USD", "nombre": "Dólar Estadounidense", "simbolo": "$"},
            {"codigo": "EUR", "nombre": "Euro", "simbolo": "€"},
            {"codigo": "BRL", "nombre": "Real Brasileño", "simbolo": "R$"},
            {"codigo": "ARS", "nombre": "Peso Argentino", "simbolo": "$"},
        ]

        for divisa_data in divisas_data:
            divisa, created = Divisa.objects.get_or_create(
                codigo=divisa_data["codigo"],
                defaults={"nombre": divisa_data["nombre"], "simbolo": divisa_data["simbolo"], "estado": "activa"},
            )
            if created:
                self.stdout.write(f"  Created divisa: {divisa.codigo}")

    def create_tasas_cambio(self):
        """Create sample exchange rates."""
        self.stdout.write("Creating tasas de cambio...")

        pyg = Divisa.objects.get(codigo="PYG")

        tasas_data = [
            {
                "destino": "USD",
                "precio_base": Decimal("7500.00"),
                "comision_compra": Decimal("50.00"),
                "comision_venta": Decimal("75.00"),
            },
            {
                "destino": "EUR",
                "precio_base": Decimal("8200.00"),
                "comision_compra": Decimal("60.00"),
                "comision_venta": Decimal("85.00"),
            },
            {
                "destino": "BRL",
                "precio_base": Decimal("1450.00"),
                "comision_compra": Decimal("30.00"),
                "comision_venta": Decimal("45.00"),
            },
            {
                "destino": "ARS",
                "precio_base": Decimal("8.50"),
                "comision_compra": Decimal("5.00"),
                "comision_venta": Decimal("8.00"),
            },
        ]

        for tasa_data in tasas_data:
            divisa_destino = Divisa.objects.get(codigo=tasa_data["destino"])

            tasa, created = TasaCambio.objects.get_or_create(
                divisa_origen=pyg,
                divisa_destino=divisa_destino,
                defaults={
                    "precio_base": tasa_data["precio_base"],
                    "comision_compra": tasa_data["comision_compra"],
                    "comision_venta": tasa_data["comision_venta"],
                    "activo": True,
                },
            )
            if created:
                self.stdout.write(f"  Created tasa: {tasa.divisa_origen.codigo} -> {tasa.divisa_destino.codigo}")

    def create_tipos_cliente(self):
        """Create sample client types."""
        self.stdout.write("Creating tipos de cliente...")

        tipos_data = [
            {"nombre": "Minorista", "descuento": Decimal("0.0")},
            {"nombre": "VIP", "descuento": Decimal("20.0")},
            {"nombre": "Corporativo", "descuento": Decimal("15.0")},
        ]

        for tipo_data in tipos_data:
            tipo, created = TipoCliente.objects.get_or_create(
                nombre=tipo_data["nombre"], defaults={"descuento_sobre_comision": tipo_data["descuento"]}
            )
            if created:
                self.stdout.write(f"  Created tipo cliente: {tipo.nombre}")

    def create_usuarios(self):
        """Create sample users."""
        self.stdout.write("Creating usuarios...")

        usuarios_data = [
            {"email": "admin@test.com", "nombre": "Administrador Test", "is_staff": True},
            {"email": "operador1@test.com", "nombre": "Operador Test 1", "is_staff": False},
            {"email": "operador2@test.com", "nombre": "Operador Test 2", "is_staff": False},
        ]

        for usuario_data in usuarios_data:
            usuario, created = Usuario.objects.get_or_create(
                email=usuario_data["email"],
                defaults={"nombre": usuario_data["nombre"], "is_staff": usuario_data["is_staff"], "activo": True},
            )
            if created:
                usuario.set_password("123")
                usuario.save()
                self.stdout.write(f"  Created usuario: {usuario.email}")

    def create_clientes(self):
        """Create sample clients."""
        self.stdout.write("Creating clientes...")

        tipos = list(TipoCliente.objects.all())
        usuarios = list(Usuario.objects.filter(email__contains="test"))

        clientes_data = [
            {
                "ruc": "3640896-4",
                "nombre": "Empresa ABC S.A.",
                "email": "contacto@empresaabc.com.py",
                "telefono": "+595981123456",
                "direccion": "Av. Mariscal López 1234, Asunción",
                "tipo": "Corporativo",
            },
            {
                "ruc": "2021243-7",
                "nombre": "Juan Pérez",
                "email": "juan.perez@email.com",
                "telefono": "+595981234567",
                "direccion": "Calle Palma 567, Asunción",
                "tipo": "VIP",
            },
            {
                "ruc": "458246-2",
                "nombre": "María González",
                "email": "maria.gonzalez@email.com",
                "telefono": "+595981345678",
                "direccion": "Av. España 890, San Lorenzo",
                "tipo": "VIP",
            },
            {
                "ruc": "1817708-5",
                "nombre": "Carlos López",
                "email": "carlos.lopez@email.com",
                "telefono": "+595981456789",
                "direccion": "Calle Chile 123, Fernando de la Mora",
                "tipo": "Minorista",
            },
            {
                "ruc": "1258812-1",
                "nombre": "Ana Martínez",
                "email": "ana.martinez@email.com",
                "telefono": "+595981567890",
                "direccion": "Av. Eusebio Ayala 456, Asunción",
                "tipo": "VIP",
            },
            {
                "ruc": "6209944-2",
                "nombre": "Roberto Silva",
                "email": "roberto.silva@email.com",
                "telefono": "+595981678901",
                "direccion": "Av. Artigas 789, Capiatá",
                "tipo": "Minorista",
            },
        ]

        for cliente_data in clientes_data:
            tipo_cliente = next((t for t in tipos if t.nombre == cliente_data["tipo"]), tipos[0])

            cliente, created = Cliente.objects.get_or_create(
                ruc=cliente_data["ruc"],
                defaults={
                    "nombre": cliente_data["nombre"],
                    "email": cliente_data["email"],
                    "telefono": cliente_data["telefono"],
                    "direccion": cliente_data["direccion"],
                    "tipo_cliente": tipo_cliente,
                },
            )

            if created:
                # Associate with users
                cliente.usuarios.set(usuarios[:2])  # Associate with first 2 users
                self.stdout.write(f"  Created cliente: {cliente.nombre}")

    def create_entidades_financieras(self):
        """Create sample financial entities."""
        self.stdout.write("Creating entidades financieras...")

        entidades_data = [
            # Bancos
            {
                "nombre": "Banco Nacional de Fomento",
                "tipo": "banco",
                "comision_compra": Decimal("1.5"),
                "comision_venta": Decimal("2.0"),
            },
            {
                "nombre": "Itaú Paraguay",
                "tipo": "banco",
                "comision_compra": Decimal("1.8"),
                "comision_venta": Decimal("2.2"),
            },
            {
                "nombre": "Banco Continental",
                "tipo": "banco",
                "comision_compra": Decimal("1.6"),
                "comision_venta": Decimal("2.1"),
            },
            # Emisores de tarjeta
            {
                "nombre": "Visa",
                "tipo": "emisor_tarjeta",
                "comision_compra": Decimal("2.5"),
                "comision_venta": Decimal("2.8"),
            },
            {
                "nombre": "Mastercard",
                "tipo": "emisor_tarjeta",
                "comision_compra": Decimal("2.4"),
                "comision_venta": Decimal("2.7"),
            },
            {
                "nombre": "American Express",
                "tipo": "emisor_tarjeta",
                "comision_compra": Decimal("3.0"),
                "comision_venta": Decimal("3.5"),
            },
            # Proveedores de billetera
            {
                "nombre": "Personal Pay",
                "tipo": "proveedor_billetera",
                "comision_compra": Decimal("1.0"),
                "comision_venta": Decimal("1.2"),
            },
            {
                "nombre": "Tigo Money",
                "tipo": "proveedor_billetera",
                "comision_compra": Decimal("0.8"),
                "comision_venta": Decimal("1.0"),
            },
            {
                "nombre": "Billetera Claro",
                "tipo": "proveedor_billetera",
                "comision_compra": Decimal("0.9"),
                "comision_venta": Decimal("1.1"),
            },
        ]

        for entidad_data in entidades_data:
            entidad, created = EntidadFinanciera.objects.get_or_create(
                nombre=entidad_data["nombre"],
                defaults={
                    "tipo": entidad_data["tipo"],
                    "comision_compra": entidad_data["comision_compra"],
                    "comision_venta": entidad_data["comision_venta"],
                    "activo": True,
                },
            )
            if created:
                self.stdout.write(f"  Created entidad: {entidad.nombre}")

    def create_medios_financieros(self):
        """Create sample financial means for each client."""
        self.stdout.write("Creating medios financieros...")

        clientes = list(Cliente.objects.all())

        for i, cliente in enumerate(clientes):
            self.stdout.write(f"  Creating medios for cliente: {cliente.nombre}")

            # Create a credit card for each client
            tarjeta = TarjetaCredito.objects.create(
                cliente=cliente,
                numero_tarjeta=f"424242424242{4240 + i:04d}",
                nombre_titular=cliente.nombre,
                fecha_expiracion=date.today() + timedelta(days=365 * 2),
                cvv="123",
                entidad=None,  # No entity required
                habilitado_para_pago=True,
                habilitado_para_cobro=False,
                alias=f"Tarjeta Principal {cliente.nombre}",
            )
            self.stdout.write(f"    Created tarjeta: {tarjeta.alias}")

            # Create a bank account for each client
            # Determine payment/collection capabilities based on client index
            if i == 0:  # First client: only for payments
                pago, cobro = True, False
            elif i == 1:  # Second client: only for collections
                pago, cobro = False, True
            else:  # Others: both
                pago, cobro = True, True

            cuenta = CuentaBancaria.objects.create(
                cliente=cliente,
                numero_cuenta=f"12345678{i:02d}",
                entidad=None,  # No entity required
                titular_cuenta=cliente.nombre,
                documento_titular=cliente.ruc.replace("-", ""),
                habilitado_para_pago=pago,
                habilitado_para_cobro=cobro,
                alias=f"Cuenta Principal {cliente.nombre}",
            )
            self.stdout.write(f"    Created cuenta: {cuenta.alias}")

            # Create an electronic wallet for each client
            # Determine payment/collection capabilities
            if i == 2:  # Third client: only for payments
                pago, cobro = True, False
            elif i == 3:  # Fourth client: only for collections
                pago, cobro = False, True
            else:  # Others: both
                pago, cobro = True, True

            billetera = BilleteraElectronica.objects.create(
                cliente=cliente,
                entidad=None,  # No entity required
                identificador=cliente.email,
                numero_telefono=cliente.telefono,
                email_asociado=cliente.email,
                habilitado_para_pago=pago,
                habilitado_para_cobro=cobro,
                alias=f"Billetera {cliente.nombre}",
            )
            self.stdout.write(f"    Created billetera: {billetera.alias}")

        self.stdout.write("Medios financieros created successfully!")
