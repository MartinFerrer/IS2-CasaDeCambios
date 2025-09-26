"""Comando de gestión de Django para poblar datos de ejemplo para pruebas.

Este comando crea datos de ejemplo para:
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
    """Comando de gestión para poblar datos de ejemplo."""

    help = "Poblar la base de datos con datos de ejemplo para pruebas"

    def add_arguments(self, parser):
        """Agregar argumentos de línea de comandos."""
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Limpiar datos existentes antes de poblar",
        )

    def handle(self, *args, **options):
        """Manejar el comando de gestión."""
        if options["clear"]:
            self.stdout.write("Limpiando datos existentes...")
            self.clear_data()

        try:
            with transaction.atomic():
                self.create_divisas()
                self.create_tasas_cambio()
                self.create_usuarios()
                self.create_clientes()
                self.create_medios_financieros()

            self.stdout.write(self.style.SUCCESS("Se ha poblado la base de datos con datos de ejemplo"))
        except Exception as e:
            raise CommandError(f"Error populando datos: {e}")

    def clear_data(self):
        """Limpiar datos."""
        TarjetaCredito.objects.all().delete()
        CuentaBancaria.objects.all().delete()
        BilleteraElectronica.objects.all().delete()
        TasaCambio.objects.all().delete()
        Cliente.objects.all().delete()
        Usuario.objects.filter(email__contains="test").delete()

    def create_divisas(self):
        """Crear divisas."""
        self.stdout.write("Creando divisas...")

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
                self.stdout.write(f"  Creada divisa: {divisa.codigo}")

    def create_tasas_cambio(self):
        """Crear tasas de cambio de ejemplo."""
        self.stdout.write("Creando tasas de cambio...")

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
                self.stdout.write(f"  Creada tasa: {tasa.divisa_origen.codigo} -> {tasa.divisa_destino.codigo}")

    def create_tipos_cliente(self):
        """Crear tipos de cliente de ejemplo."""
        self.stdout.write("Creando tipos de cliente...")

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
                self.stdout.write(f"  Creado tipo cliente: {tipo.nombre}")

    def create_usuarios(self):
        """Crear usuarios de ejemplo."""
        self.stdout.write("Creando usuarios...")

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
                self.stdout.write(f"  Creado usuario: {usuario.email}")

    def create_clientes(self):
        """Crear clientes de ejemplo."""
        self.stdout.write("Creando clientes...")

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
                # Asociar con usuarios
                cliente.usuarios.set(usuarios[:2])  # Asociar con los primeros 2 usuarios
                self.stdout.write(f"  Creado cliente: {cliente.nombre}")

    def create_entidades_financieras(self):
        """Crear entidades financieras de ejemplo."""
        self.stdout.write("Creando entidades financieras...")

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
                self.stdout.write(f"  Creada entidad: {entidad.nombre}")

    def create_medios_financieros(self):
        """Crear medios financieros de ejemplo para cada cliente."""
        self.stdout.write("Creando medios financieros...")

        clientes = list(Cliente.objects.all())
        bancos = list(EntidadFinanciera.objects.filter(tipo="banco", activo=True))
        emisores = list(EntidadFinanciera.objects.filter(tipo="emisor_tarjeta", activo=True))
        proveedores_billetera = list(EntidadFinanciera.objects.filter(tipo="proveedor_billetera", activo=True))

        for i, cliente in enumerate(clientes):
            self.stdout.write(f"  Creando medios para cliente: {cliente.nombre}")

            # Crear una tarjeta de crédito para cada cliente
            emisor = emisores[i % len(emisores)] if emisores else None
            tarjeta = TarjetaCredito.objects.create(
                cliente=cliente,
                numero_tarjeta=f"424242424242{4240 + i:04d}",
                nombre_titular=cliente.nombre,
                fecha_expiracion=date.today() + timedelta(days=365 * 2),
                cvv="123",
                entidad=emisor,
                habilitado_para_pago=True,
                habilitado_para_cobro=False,
                alias=f"Tarjeta {emisor.nombre if emisor else 'Principal'} {cliente.nombre}",
            )
            self.stdout.write(f"    Creada tarjeta: {tarjeta.alias}")

            # Crear una cuenta bancaria para cada cliente
            # Determinar capacidades de pago/cobro basadas en el índice del cliente
            if i == 0:  # Primer cliente: solo para pagos
                pago, cobro = True, False
            elif i == 1:  # Segundo cliente: solo para cobros
                pago, cobro = False, True
            else:  # Otros: ambos
                pago, cobro = True, True

            banco = bancos[i % len(bancos)] if bancos else None
            cuenta = CuentaBancaria.objects.create(
                cliente=cliente,
                numero_cuenta=f"12345678{i:02d}",
                entidad=banco,
                titular_cuenta=cliente.nombre,
                documento_titular=cliente.ruc.replace("-", ""),
                habilitado_para_pago=pago,
                habilitado_para_cobro=cobro,
                alias=f"Cuenta {banco.nombre if banco else 'Principal'} {cliente.nombre}",
            )
            self.stdout.write(f"    Creada cuenta: {cuenta.alias}")

            # Crear una billetera electrónica para cada cliente
            # Determinar capacidades de pago/cobro
            if i == 2:  # Tercer cliente: solo para pagos
                pago, cobro = True, False
            elif i == 3:  # Cuarto cliente: solo para cobros
                pago, cobro = False, True
            else:  # Otros: ambos
                pago, cobro = True, True

            proveedor = proveedores_billetera[i % len(proveedores_billetera)] if proveedores_billetera else None
            billetera = BilleteraElectronica.objects.create(
                cliente=cliente,
                entidad=proveedor,
                identificador=cliente.email,
                numero_telefono=cliente.telefono,
                email_asociado=cliente.email,
                habilitado_para_pago=pago,
                habilitado_para_cobro=cobro,
                alias=f"Billetera {proveedor.nombre if proveedor else 'Principal'} {cliente.nombre}",
            )
            self.stdout.write(f"    Creada billetera: {billetera.alias}")

        self.stdout.write("¡Medios financieros creados exitosamente!")
