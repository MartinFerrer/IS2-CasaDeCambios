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

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.operaciones.models import Divisa, TasaCambio
from apps.stock.models import StockDivisaTauser
from apps.tauser.models import Tauser
from apps.transacciones.models import BilleteraElectronica, CuentaBancaria, EntidadFinanciera, TarjetaCredito
from apps.usuarios.models import Cliente, TipoCliente

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
                self.create_tipos_cliente()
                self.create_usuarios()
                self.create_clientes()
                self.create_tausers()
                self.create_medios_financieros()
                self.create_stock_divisas()

            self.stdout.write(self.style.SUCCESS("Se ha poblado la base de datos con datos de ejemplo"))
        except Exception as e:
            raise CommandError(f"Error populando datos: {e}")

    def clear_data(self):
        """Limpiar datos."""
        StockDivisaTauser.objects.all().delete()
        Tauser.objects.all().delete()
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

        # Crear o obtener grupos necesarios
        admin_group, _ = Group.objects.get_or_create(name="Administrador")
        analyst_group, _ = Group.objects.get_or_create(name="Analista Cambiario")

        usuarios_data = [
            {"email": "admin@test.com", "nombre": "Administrador Test", "is_staff": True, "groups": ["Administrador"]},
            {"email": "operador1@test.com", "nombre": "Operador Test 1", "is_staff": False, "groups": []},
            {"email": "operador2@test.com", "nombre": "Operador Test 2", "is_staff": False, "groups": []},
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

                # Asignar grupos al usuario
                for group_name in usuario_data.get("groups", []):
                    group = Group.objects.get(name=group_name)
                    usuario.groups.add(group)
                    self.stdout.write(f"    Asignado grupo '{group_name}' al usuario {usuario.email}")
            else:
                # Si el usuario ya existe, asegurar que tenga los grupos correctos
                for group_name in usuario_data.get("groups", []):
                    group = Group.objects.get(name=group_name)
                    if not usuario.groups.filter(name=group_name).exists():
                        usuario.groups.add(group)
                        self.stdout.write(f"    Asignado grupo '{group_name}' al usuario existente {usuario.email}")

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

    def create_tausers(self):
        """Crear tausers de ejemplo."""
        self.stdout.write("Creando tausers...")

        tausers_data = [
            {
                "nombre": "Casa Central",
                "ubicacion": "Av. Mariscal López 1234, Asunción - Centro"
            },
            {
                "nombre": "Sucursal Shopping del Sol",
                "ubicacion": "Shopping del Sol, Local 205, Asunción"
            },
            {
                "nombre": "Sucursal Villa Morra",
                "ubicacion": "Av. Aviadores del Chaco 2050, Asunción - Villa Morra"
            },
            {
                "nombre": "Sucursal Ciudad del Este",
                "ubicacion": "Av. San Blas 1456, Ciudad del Este, Alto Paraná"
            },
            {
                "nombre": "Sucursal Encarnación",
                "ubicacion": "Calle 14 de Mayo 789, Encarnación, Itapúa"
            }
        ]

        for tauser_data in tausers_data:
            tauser, created = Tauser.objects.get_or_create(
                nombre=tauser_data["nombre"],
                defaults={
                    "ubicacion": tauser_data["ubicacion"]
                }
            )
            if created:
                self.stdout.write(f"  Creado tauser: {tauser.nombre}")

    def create_stock_divisas(self):
        """Crear stock de divisas para cada tauser."""
        self.stdout.write("Creando stock de divisas...")

        tausers = list(Tauser.objects.all())
        divisas = list(Divisa.objects.all())

        # Denominaciones comunes para cada divisa
        denominaciones_por_divisa = {
            "PYG": [2000, 5000, 10000, 20000, 50000, 100000],
            "USD": [1, 5, 10, 20, 50, 100],
            "EUR": [5, 10, 20, 50, 100, 200],
            "BRL": [2, 5, 10, 20, 50, 100, 200],
            "ARS": [100, 200, 500, 1000, 2000]
        }

        # Stock inicial base por denominación (varía por tauser)
        stock_base = {
            "PYG": {2000: 400, 5000: 300, 10000: 200, 20000: 150, 50000: 100, 100000: 50},
            "USD": {1: 200, 5: 150, 10: 100, 20: 80, 50: 50, 100: 30},
            "EUR": {5: 100, 10: 80, 20: 60, 50: 40, 100: 25, 200: 15},
            "BRL": {2: 150, 5: 120, 10: 90, 20: 70, 50: 45, 100: 25, 200: 15},
            "ARS": {100: 200, 200: 150, 500: 100, 1000: 80, 2000: 40}
        }

        for tauser in tausers:
            self.stdout.write(f"  Creando stock para tauser: {tauser.nombre}")

            for divisa in divisas:
                denominaciones = denominaciones_por_divisa.get(divisa.codigo, [])
                stock_divisa = stock_base.get(divisa.codigo, {})

                for denominacion in denominaciones:
                    # Variar el stock base según el tauser
                    # Casa Central tiene más stock, sucursales menores tienen menos
                    multiplier = 1.0
                    if "Casa Central" in tauser.nombre:
                        multiplier = 1.5
                    elif "Ciudad del Este" in tauser.nombre or "Encarnación" in tauser.nombre:
                        multiplier = 0.7
                    else:
                        multiplier = 1.0

                    stock_cantidad = int(stock_divisa.get(denominacion, 50) * multiplier)
                    stock_reservado = min(stock_cantidad // 10, 20)  # 10% reservado, máximo 20

                    stock, created = StockDivisaTauser.objects.get_or_create(
                        tauser=tauser,
                        divisa=divisa,
                        denominacion=denominacion,
                        defaults={
                            "stock": stock_cantidad,
                            "stock_reservado": stock_reservado
                        }
                    )

                    if created:
                        self.stdout.write(
                            f"    {divisa.codigo} {denominacion}: {stock_cantidad} unidades "
                            f"(reservado: {stock_reservado})"
                        )

        self.stdout.write("¡Stock de divisas creado exitosamente!")
