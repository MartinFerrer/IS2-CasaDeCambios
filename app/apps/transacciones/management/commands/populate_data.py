"""Management command para poblar la base de datos con datos de muestra del sistema Casa de Cambios.

DOCUMENTACION PARA QA - CONJUNTO DE DATOS CARGADOS
==================================================

Este script carga un conjunto completo de datos de prueba para el sistema Casa de Cambios.
Los datos son configurables yestan organizados en secciones claramente definidas.

DATOS CARGADOS POR DEFECTO:
---------------------------

1. DIVISAS (7 divisas):
   NOTA: PYG NO se carga aqui, se crea con migracion customizada
   - USD (Dolar Estadounidense) - Tasa base: 8000, Comision venta: 80, Comision compra: 65
   - EUR (Euro) - Tasa base: 8500, Comision venta: 85, Comision compra: 70
   - BRL (Real Brasileno) - Tasa base: 1500, Comision venta: 15, Comision compra: 12
   - ARS (Peso Argentino) - Tasa base: 9, Comision venta: 0.5, Comision compra: 0.3
   - UYU (Peso Uruguayo) - Tasa base: 190, Comision venta: 5, Comision compra: 3
   - CLP (Peso Chileno) - Tasa base: 8, Comision venta: 0.5, Comision compra: 0.3
   - BOB (Boliviano) - Tasa base: 1100, Comision venta: 20, Comision compra: 15

2. TIPOS DE CLIENTE (3 tipos fijos - NO se crean aqui):
   NOTA: Los tipos de cliente se crean mediante fixtures o migraciones
   - VIP
   - Corporativo
   - Minorista

3. USUARIOS ADMINISTRADORES (2 usuarios):
   - admin@test.com (Superusuario + Rol: Administrador) - Contraseña: 123
   - analista@test.com (Staff + Rol: Analista Cambiario) - Contraseña: 123

4. USUARIOS DEL SISTEMA (10 por defecto, 25 en modo --full):
   NOTA: Los usuarios NO tienen tipo de cliente asignado inicialmente
   - Usuarios con emails unicos generados automaticamente
   - 75% activos, 25% inactivos
   - 25% con permisos de staff
   - Contrasena por defecto: "123"
   - Roles asignados automaticamente:
     * "Usuario Asociado a Cliente": usuarios asociados a uno o mas clientes
     * "Usuario Registrado": usuarios sin clientes asociados

5. CLIENTES (15 por defecto, 50 en modo --full):
   - Empresas con RUCs validos de la lista predefinida
   - Asignacion aleatoria entre los 3 tipos de cliente (VIP, Corporativo, Minorista)
   - Cada cliente tiene 1-3 usuarios asignados
   - Datos de contacto completos (email, telefono, direccion)

6. MEDIOS DE PAGO (asignados a cada cliente):
   - Al menos 1 cuenta bancaria (habilitada para pago)
   - Al menos 1 tarjeta de credito (habilitada para pago)
   - Al menos 1 billetera electronica (habilitada para cobro)
   - Utilizan las Entidades Financieras existentes en la BD

7. ENTIDADES FINANCIERAS:
   NOTA: NO se crean aqui, se obtienen de otra forma

8. TASAS DE CAMBIO HISTORICAS (90 dias por defecto):
   - Actualizaciones diarias con variaciones realistas (-2% a +2%)
   - PYG es siempre la divisa ORIGEN, las demas son DESTINO
   - Cada tasa incluye: precio_base, comision_compra, comision_venta (valores separados, no calculados)

9. LIMITES DE TRANSACCIONES (configuracion fija):
   - Limite diario: 100,000,000 guaranies
   - Limite mensual: 800,000,000 guaranies

OPCIONES DE EJECUCION:
---------------------

Basico (datos minimos para desarrollo):
    python dev.py populate-data

Completo (datos extensos para testing):
    python dev.py populate-data-full

Limpiar y recargar:
    python dev.py populate-data-clear

Historial personalizado:
    python manage.py populate_data --historical-days 180

MODIFICACION DE DATOS PARA QA:
-----------------------------

Para modificar los conjuntos de datos, editar las siguientes secciones en este archivo:

1. DIVISAS_DATA - Para agregar/quitar divisas (NO incluir PYG)
2. NOMBRES_USUARIOS/NOMBRES_EMPRESAS - Para personalizar nombres
3. TASAS_CONFIG - Para ajustar tasas de cambio, comisiones de compra y venta
4. LIMITES_DATA - Para configurar limites de transacciones

VALIDACIONES Y RESTRICCIONES:
----------------------------

- Los RUCs se usan de una lista predefinida de RUCs validos
- Las tasas de cambio siempre incluyen PYG como divisa base
- Los limites mensuales siempre son mayores a los diarios
- Los emails son unicos en todo el sistema
"""

import random
from datetime import timedelta
from decimal import Decimal

from apps.operaciones.models import Divisa, TasaCambio
from apps.transacciones.models import (
    BilleteraElectronica,
    CuentaBancaria,
    EntidadFinanciera,
    LimiteTransacciones,
    TarjetaCredito,
)
from apps.usuarios.models import Cliente, TipoCliente
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

User = get_user_model()

# =============================================================================
# CONFIGURACION DE DATOS - MODIFICAR AQUI PARA PERSONALIZAR EL CONJUNTO DE DATOS
# =============================================================================

# NOTA: PYG NO se incluye aqui, se crea con migracion customizada
DIVISAS_DATA = [
    {"codigo": "USD", "nombre": "Dolar Estadounidense", "simbolo": "$"},
    {"codigo": "EUR", "nombre": "Euro", "simbolo": "€"},
    {"codigo": "BRL", "nombre": "Real Brasileno", "simbolo": "R$"},
    {"codigo": "ARS", "nombre": "Peso Argentino", "simbolo": "AR$"},
    {"codigo": "UYU", "nombre": "Peso Uruguayo", "simbolo": "UY$"},
    {"codigo": "CLP", "nombre": "Peso Chileno", "simbolo": "CL$"},
    {"codigo": "BOB", "nombre": "Boliviano", "simbolo": "Bs"},
]

# NOTA: Los tipos de cliente NO se crean aqui. Los 3 tipos fijos son: VIP, Corporativo, Minorista
# Se obtienen mediante fixtures o migraciones
TIPOS_CLIENTE_FIJOS = ["VIP", "Corporativo", "Minorista"]

NOMBRES_USUARIOS = [
    "María García",
    "Carlos López",
    "Ana Martínez",
    "Diego Fernández",
    "Laura González",
    "Miguel Torres",
    "Sofía Rodríguez",
    "Pablo Silva",
    "Valentina Benítez",
    "Andrés Cabrera",
    "Camila Vera",
    "Mateo Ruiz",
    "Isabella Morales",
    "Sebastián Núñez",
    "Francesca Delgado",
    "Nicolás Herrera",
    "Catalina Vargas",
    "Emiliano Castro",
    "Esperanza Jiménez",
    "Maximiliano Ortega",
    "Alejandra Peña",
    "Ricardo Medina",
    "Daniela Aguilar",
    "Fernando Ramos",
    "Gabriela Mendoza",
    "Arturo Vega",
    "Renata Campos",
    "Joaquín Soto",
]

NOMBRES_EMPRESAS = [
    "Tech Solutions S.A.",
    "Global Trade Corp",
    "Import Export Ltda",
    "Digital Services SRL",
    "Consulting Group",
    "Financial Partners",
    "Innovation Hub S.A.",
    "Business Network",
    "Strategic Alliance",
    "Market Leaders Corp",
    "Growth Partners",
    "Success Ventures",
    "Elite Business",
    "Prime Consulting",
    "Advanced Solutions",
    "Professional Services",
    "Quality Partners",
    "Excellence Corp",
    "Dynamic Group",
    "Future Tech",
    "Smart Business",
    "Capital Partners",
    "Investment Group",
    "Commerce Solutions",
    "Trade Network",
    "Economic Partners",
    "Development Corp",
    "Progress Solutions",
    "Prosperity Group",
    "Wealth Management",
    "Asset Partners",
]

# NOTA: Las entidades financieras NO se crean aqui, se obtienen de otra forma

# Configuracion de tasas de cambio con valores directos (NO calculados)
# Formato: codigo_divisa: {precio_base, comision_venta, comision_compra}
TASAS_CONFIG = {
    "USD": {"precio_base": Decimal("8000"), "comision_venta": Decimal("80"), "comision_compra": Decimal("65")},
    "EUR": {"precio_base": Decimal("8500"), "comision_venta": Decimal("85"), "comision_compra": Decimal("70")},
    "BRL": {"precio_base": Decimal("1500"), "comision_venta": Decimal("15"), "comision_compra": Decimal("12")},
    "ARS": {"precio_base": Decimal("9"), "comision_venta": Decimal("0.5"), "comision_compra": Decimal("0.3")},
    "UYU": {"precio_base": Decimal("190"), "comision_venta": Decimal("5"), "comision_compra": Decimal("3")},
    "CLP": {"precio_base": Decimal("8"), "comision_venta": Decimal("0.5"), "comision_compra": Decimal("0.3")},
    "BOB": {"precio_base": Decimal("1100"), "comision_venta": Decimal("20"), "comision_compra": Decimal("15")},
}

# Limites fijos de transacciones
LIMITES_DATA = {
    "limite_diario": Decimal("100000000"),  # 100M guaranies
    "limite_mensual": Decimal("800000000"),  # 800M guaranies
}

DOMINIOS_EMAIL = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "empresa.com.py"]

# Lista de RUCs validos
RUCS_VALIDOS = [
    "1000850-0",
    "1001620-1",
    "1002060-8",
    "1003120-0",
    "1003580-0",
    "1004130-3",
    "1007080-0",
    "1007960-2",
    "1008940-3",
    "1009790-2",
    "1010480-1",
    "1010940-4",
    "1011870-5",
    "1012140-4",
    "1012210-9",
    "1012290-7",
    "1012600-7",
    "1016950-4",
    "1020270-6",
    "1021030-0",
    "1005710-2",
    "1020340-0",
    "1023510-8",
    "1048690-9",
    "1066050-0",
    "1075780-5",
    "1094990-9",
    "1131470-2",
    "1138580-4",
    "1153640-3",
    "1174510-0",
    "1179480-1",
    "1207360-1",
    "1209910-4",
    "1268520-8",
    "1286490-0",
    "1288140-6",
    "1297030-1",
    "1309050-0",
    "1322930-3",
    "1003270-3",
    "1006090-1",
    "1007540-2",
    "1007830-4",
    "1011630-3",
    "1013850-1",
    "1013860-9",
    "1014070-0",
    "1016720-0",
    "1017450-8",
    "1018040-0",
    "1018490-2",
    "1019600-5",
    "1020970-0",
    "1022230-8",
    "1022690-7",
    "1026650-0",
    "1027850-8",
    "1028240-8",
    "1026670-4",
    "1365330-0",
    "1433580-8",
    "1540120-0",
    "1644490-6",
    "1659360-0",
    "1683080-6",
    "1910520-7",
    "2041840-0",
    "2270430-2",
    "2358640-0",
    "2389790-2",
    "2638520-1",
    "3010930-2",
    "3023060-8",
    "3212880-0",
    "3220660-7",
    "3341700-8",
    "3342160-9",
    "3350350-8",
    "2180550-4",
    "2561390-1",
    "3374640-0",
    "3443180-2",
    "3546790-8",
    "3978330-8",
    "4009870-2",
    "4336960-0",
    "4484810-2",
    "4655590-0",
    "4753050-2",
    "4783570-2",
    "4842600-8",
    "4876080-3",
    "4905210-1",
    "4963070-9",
    "4967200-2",
    "4973490-3",
    "5018340-0",
]

# =============================================================================
# CLASE DEL COMANDO
# =============================================================================


class Command(BaseCommand):
    """Django management command para cargar datos de muestra del sistema."""

    help = "Carga datos de muestra completos y realistas en la base de datos Casa de Cambios"

    def __init__(self):
        """Initialize command with data tracking lists."""
        super().__init__()
        self.divisas_creadas = []
        self.usuarios_creados = []
        self.clientes_creados = []
        self.entidades_creadas = []
        self.tipos_cliente_creados = []

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Borra todos los datos antes de cargar nuevos",
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help="Carga conjunto completo y extenso de datos (más usuarios y clientes)",
        )
        parser.add_argument(
            "--historical-days",
            type=int,
            default=90,
            help="Número de días de historial de tasas de cambio (default: 90)",
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        try:
            with transaction.atomic():
                self.stdout.write(self.style.HTTP_INFO("=" * 60))
                self.stdout.write(self.style.HTTP_INFO("SISTEMA CASA DE CAMBIOS - CARGA DE DATOS DE MUESTRA"))
                self.stdout.write(self.style.HTTP_INFO("=" * 60))

                if options["clear"]:
                    self.stdout.write("🗑️  Borrando datos existentes...")
                    self.clear_data()

                self.stdout.write("📊 Cargando datos de muestra...")

                # Datos básicos del sistema
                self.crear_divisas()
                self.crear_tipos_cliente()

                # Usuarios administradores
                self.crear_usuario_admin()
                self.crear_usuario_analista()

                # Usuarios y clientes
                cantidad_usuarios = 25 if options.get("full", False) else 10
                cantidad_clientes = 50 if options.get("full", False) else 15
                self.crear_usuarios(cantidad=cantidad_usuarios)
                self.crear_clientes(cantidad=cantidad_clientes)

                # Asignar roles a usuarios segun asociacion con clientes
                self.asignar_roles_usuarios()

                # Entidades financieras y medios de pago
                self.crear_entidades_financieras()
                self.crear_medios_financieros()

                # Configuración del sistema

                self.crear_limites_transacciones()  # Datos históricos
                historical_days = options.get("historical_days", 90)
                self.crear_tasas_cambio_historicas(dias_historial=historical_days)

                if options["full"]:
                    self.stdout.write("📈 Cargando conjunto completo de datos...")
                    self.crear_datos_adicionales()

                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(self.style.SUCCESS("✅ DATOS DE MUESTRA CARGADOS EXITOSAMENTE"))
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.mostrar_resumen()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error al cargar datos: {e}"))
            raise

    def clear_data(self):
        """Borra todos los datos de muestra existentes."""
        models_to_clear = [
            TasaCambio,
            TarjetaCredito,
            CuentaBancaria,
            BilleteraElectronica,
            Cliente,
            User,
            TipoCliente,
            EntidadFinanciera,
            Divisa,
            LimiteTransacciones,
        ]

        total_eliminados = 0
        for model in models_to_clear:
            count = model.objects.count()
            if count > 0:
                model.objects.all().delete()
                total_eliminados += count
                self.stdout.write(f"  - Eliminados {count} registros de {model.__name__}")

        self.stdout.write(f"  📋 Total eliminados: {total_eliminados} registros")

    def crear_divisas(self):
        """Crea divisas principales del sistema (excepto PYG que se crea con migracion)."""
        self.stdout.write("Creando divisas...")

        for divisa_data in DIVISAS_DATA:
            divisa, created = Divisa.objects.get_or_create(
                codigo=divisa_data["codigo"],
                defaults={"nombre": divisa_data["nombre"], "simbolo": divisa_data["simbolo"], "estado": "activa"},
            )
            if created:
                self.divisas_creadas.append(divisa)
                self.stdout.write(f"  Creada: {divisa.codigo} - {divisa.nombre}")
            else:
                self.divisas_creadas.append(divisa)
                self.stdout.write(f"  Ya existe: {divisa.codigo} - {divisa.nombre}")

        self.stdout.write(f"  Total divisas creadas/encontradas: {len(self.divisas_creadas)}")

    def crear_tipos_cliente(self):
        """Obtiene los tipos de cliente que ya existen (NO los crea)."""
        self.stdout.write("Obteniendo tipos de cliente existentes...")

        for nombre_tipo in TIPOS_CLIENTE_FIJOS:
            tipo = TipoCliente.objects.filter(nombre=nombre_tipo).first()
            if tipo:
                self.tipos_cliente_creados.append(tipo)
                self.stdout.write(f"  Encontrado: {tipo.nombre}")
            else:
                self.stdout.write(self.style.WARNING(f"  ADVERTENCIA: Tipo '{nombre_tipo}' no existe en la BD"))

        self.stdout.write(f"  Total tipos de cliente disponibles: {len(self.tipos_cliente_creados)}")

    def crear_usuario_admin(self):
        """Crea usuario administrador con todos los permisos."""
        from django.contrib.auth.models import Group

        self.stdout.write("Creando usuario administrador...")

        admin, created = User.objects.get_or_create(
            email="admin@test.com",
            defaults={
                "nombre": "admin",
                "activo": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        if created:
            admin.set_password("123")
            admin.save()
            self.stdout.write("  Creado: admin@test.com (Superusuario)")
        else:
            self.stdout.write("  Ya existe: admin@test.com")

        # Asignar el rol 'Administrador'
        try:
            grupo_admin = Group.objects.get(name="Administrador")
            if grupo_admin not in admin.groups.all():
                admin.groups.add(grupo_admin)
                self.stdout.write("  Rol 'Administrador' asignado al usuario admin")
            else:
                self.stdout.write("  Usuario admin ya tiene el rol 'Administrador'")
        except Group.DoesNotExist:
            self.stdout.write(self.style.WARNING("  ADVERTENCIA: Grupo 'Administrador' no existe aun"))

    def crear_usuario_analista(self):
        """Crea usuario analista cambiario."""
        from django.contrib.auth.models import Group

        self.stdout.write("Creando usuario analista cambiario...")

        analista, created = User.objects.get_or_create(
            email="analista@test.com",
            defaults={
                "nombre": "analista",
                "activo": True,
                "is_staff": True,
                "is_superuser": False,
            },
        )

        if created:
            analista.set_password("123")
            analista.save()
            self.stdout.write("  Creado: analista@test.com (Staff)")
        else:
            self.stdout.write("  Ya existe: analista@test.com")

        # Asignar el rol 'Analista Cambiario'
        try:
            grupo_analista = Group.objects.get(name="Analista Cambiario")
            if grupo_analista not in analista.groups.all():
                analista.groups.add(grupo_analista)
                self.stdout.write("  Rol 'Analista Cambiario' asignado al usuario analista")
            else:
                self.stdout.write("  Usuario analista ya tiene el rol 'Analista Cambiario'")
        except Group.DoesNotExist:
            self.stdout.write(self.style.WARNING("  ADVERTENCIA: Grupo 'Analista Cambiario' no existe aun"))

    def crear_usuarios(self, cantidad=10):
        """Crea usuarios del sistema con datos variados."""
        self.stdout.write(f"Creando {cantidad} usuarios...")

        nombres_disponibles = NOMBRES_USUARIOS.copy()

        for _ in range(min(cantidad, len(nombres_disponibles))):
            nombre = random.choice(nombres_disponibles)
            nombres_disponibles.remove(nombre)  # Evitar duplicados

            email = f"{nombre.lower().replace(' ', '.')}{random.randint(1, 999)}@{random.choice(DOMINIOS_EMAIL)}"

            usuario, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "nombre": nombre,
                    "activo": random.choice([True, True, True, False]),  # 75% activos
                    "is_staff": random.choice([True, False, False, False]),  # 25% staff
                },
            )

            if created:
                usuario.set_password("123")  # Contrasena por defecto
                usuario.save()
                self.usuarios_creados.append(usuario)
                estado = "Activo" if usuario.activo else "Inactivo"
                staff = " (Staff)" if usuario.is_staff else ""
                self.stdout.write(f"  Creado: {usuario.nombre} - {estado}{staff}")

        self.stdout.write(f"  Total usuarios: {len(self.usuarios_creados)}")

    def crear_clientes(self, cantidad=15):
        """Crea clientes con datos realistas."""
        from django.core.exceptions import ValidationError

        self.stdout.write(f"🏢 Creando {cantidad} clientes...")

        nombres_disponibles = NOMBRES_EMPRESAS.copy()
        rucs_disponibles = RUCS_VALIDOS.copy()

        for i in range(min(cantidad, len(nombres_disponibles), len(rucs_disponibles))):
            # Usar RUC válido de la lista
            ruc_completo = random.choice(rucs_disponibles)
            rucs_disponibles.remove(ruc_completo)  # Evitar duplicados

            nombre = random.choice(nombres_disponibles)
            nombres_disponibles.remove(nombre)  # Evitar duplicados

            # Generar email unico usando indice
            email_domain = nombre.lower().replace(" ", "").replace(".", "")[:15]
            email = f"contacto{i + 1}@{email_domain}.com.py"

            try:
                cliente, created = Cliente.objects.get_or_create(
                    ruc=ruc_completo,
                    defaults={
                        "nombre": nombre,
                        "email": email,
                        "telefono": f"0{random.randint(900, 999)}{random.randint(100000, 999999)}",
                        "direccion": f"Av. Principal {random.randint(100, 9999)}, Asunción",
                        "tipo_cliente": random.choice(self.tipos_cliente_creados)
                        if self.tipos_cliente_creados
                        else None,
                    },
                )

                if created:
                    # Asignar usuarios aleatorios al cliente
                    if self.usuarios_creados:
                        usuarios_asignados = random.sample(
                            self.usuarios_creados, random.randint(1, min(3, len(self.usuarios_creados)))
                        )
                        cliente.usuarios.set(usuarios_asignados)

                    self.clientes_creados.append(cliente)
                    tipo_cliente = cliente.tipo_cliente.nombre if cliente.tipo_cliente else "Sin tipo"
                    self.stdout.write(f"  ✓ {cliente.nombre} - {tipo_cliente}")
                else:
                    self.stdout.write(f"  Ya existe: {cliente.nombre}")
            except ValidationError:
                # Ignorar clientes duplicados (por email u otro campo unico)
                self.stdout.write(f"  Ignorado: {nombre} - email duplicado")
                continue

        self.stdout.write(f"  📊 Total clientes: {len(self.clientes_creados)}")

    def asignar_roles_usuarios(self):
        """Asigna roles a usuarios segun si estan asociados a clientes o no."""
        from django.contrib.auth.models import Group

        self.stdout.write("Asignando roles a usuarios...")

        try:
            grupo_asociado = Group.objects.get(name="Usuario Asociado a Cliente")
            grupo_registrado = Group.objects.get(name="Usuario Registrado")
        except Group.DoesNotExist as e:
            self.stdout.write(self.style.WARNING(f"  ADVERTENCIA: {e}"))
            return

        usuarios_asociados = 0
        usuarios_registrados = 0

        for usuario in self.usuarios_creados:
            # Verificar si el usuario esta asociado a algun cliente
            tiene_clientes = Cliente.objects.filter(usuarios=usuario).exists()

            if tiene_clientes:
                if grupo_asociado not in usuario.groups.all():
                    usuario.groups.add(grupo_asociado)
                    usuarios_asociados += 1
            else:
                if grupo_registrado not in usuario.groups.all():
                    usuario.groups.add(grupo_registrado)
                    usuarios_registrados += 1

        self.stdout.write(f"  Usuarios con rol 'Usuario Asociado a Cliente': {usuarios_asociados}")
        self.stdout.write(f"  Usuarios con rol 'Usuario Registrado': {usuarios_registrados}")

    def crear_entidades_financieras(self):
        """Las entidades financieras NO se crean aqui, se obtienen de otra forma."""
        self.stdout.write("NOTA: Entidades financieras NO se crean en este script")
        self.stdout.write("  Se obtienen de otra forma segun requerimientos del sistema")

        # Obtener las entidades existentes para referencia
        self.entidades_creadas = list(EntidadFinanciera.objects.all())
        if self.entidades_creadas:
            self.stdout.write(f"  Entidades disponibles en BD: {len(self.entidades_creadas)}")
        else:
            self.stdout.write(self.style.WARNING("  ADVERTENCIA: No hay entidades financieras en la BD"))

    def crear_medios_financieros(self):
        """Crea medios de pago para cada cliente."""
        from datetime import date

        self.stdout.write("Creando medios de pago para clientes...")

        if not self.entidades_creadas:
            self.stdout.write(self.style.WARNING("  No hay entidades financieras disponibles"))
            return

        # Separar entidades por tipo
        bancos = [e for e in self.entidades_creadas if e.tipo == "banco"]
        emisores_tarjeta = [e for e in self.entidades_creadas if e.tipo == "emisor_tarjeta"]
        proveedores_billetera = [e for e in self.entidades_creadas if e.tipo == "proveedor_billetera"]

        medios_creados = {"cuentas": 0, "tarjetas": 0, "billeteras": 0}

        for cliente in self.clientes_creados:
            # Crear al menos una cuenta bancaria (para pago o cobro)
            if bancos:
                entidad_banco = random.choice(bancos)
                numero_cuenta = f"{random.randint(100000, 999999)}{random.randint(10, 99)}"
                cuenta, created = CuentaBancaria.objects.get_or_create(
                    cliente=cliente,
                    entidad=entidad_banco,
                    numero_cuenta=numero_cuenta,
                    defaults={
                        "titular_cuenta": cliente.nombre,
                        "documento_titular": cliente.ruc,
                        "habilitado_para_pago": True,
                        "habilitado_para_cobro": random.choice([True, False]),
                    },
                )
                if created:
                    medios_creados["cuentas"] += 1

            # Crear al menos una tarjeta de credito (para pago)
            if emisores_tarjeta:
                entidad_emisor = random.choice(emisores_tarjeta)
                numero_tarjeta = (
                    f"{random.randint(1000, 9999)}"
                    f"{random.randint(1000, 9999)}"
                    f"{random.randint(1000, 9999)}"
                    f"{random.randint(1000, 9999)}"
                )
                tarjeta, created = TarjetaCredito.objects.get_or_create(
                    cliente=cliente,
                    entidad=entidad_emisor,
                    numero_tarjeta=numero_tarjeta,
                    defaults={
                        "nombre_titular": cliente.nombre,
                        "fecha_expiracion": date(2026 + random.randint(0, 3), random.randint(1, 12), 1),
                        "cvv": f"{random.randint(100, 999)}",
                    },
                )
                if created:
                    medios_creados["tarjetas"] += 1

            # Crear al menos una billetera electronica (para cobro)
            if proveedores_billetera:
                entidad_billetera = random.choice(proveedores_billetera)
                numero_telefono = f"0{random.randint(900, 999)}{random.randint(100000, 999999)}"
                billetera, created = BilleteraElectronica.objects.get_or_create(
                    cliente=cliente,
                    entidad=entidad_billetera,
                    numero_telefono=numero_telefono,
                    defaults={
                        "identificador": numero_telefono,
                        "email_asociado": cliente.email,
                        "habilitado_para_pago": random.choice([True, False]),
                        "habilitado_para_cobro": True,
                    },
                )
                if created:
                    medios_creados["billeteras"] += 1

        total = sum(medios_creados.values())
        self.stdout.write(f"  Cuentas bancarias: {medios_creados['cuentas']}")
        self.stdout.write(f"  Tarjetas de credito: {medios_creados['tarjetas']}")
        self.stdout.write(f"  Billeteras electronicas: {medios_creados['billeteras']}")
        self.stdout.write(f"  Total medios de pago: {total}")

    def crear_limites_transacciones(self):
        """Crea limites de transacciones fijos."""
        self.stdout.write("Creando limites de transacciones...")

        limite = LimiteTransacciones.objects.create(
            limite_diario=LIMITES_DATA["limite_diario"], limite_mensual=LIMITES_DATA["limite_mensual"]
        )

        self.stdout.write(f"  Limite diario: {LIMITES_DATA['limite_diario']:,} guaranies")
        self.stdout.write(f"  Limite mensual: {LIMITES_DATA['limite_mensual']:,} guaranies")

    def crear_tasas_cambio_historicas(self, dias_historial=90):
        """Crea tasas de cambio con valores directos (NO calculados) y su historial."""
        from apps.operaciones.models import TasaCambioHistorial

        self.stdout.write(f"Creando tasas actuales y {dias_historial} dias de historial...")

        # Obtener PYG (divisa base)
        try:
            pyg = Divisa.objects.get(codigo="PYG")
        except Divisa.DoesNotExist:
            self.stdout.write(self.style.ERROR("  ERROR: Divisa PYG no existe en la BD"))
            self.stdout.write(self.style.WARNING("  Ejecuta las migraciones para crear PYG"))
            return

        # Primero crear las tasas de cambio actuales (unicas) con valores directos
        # PYG es siempre la divisa ORIGEN, las demas son DESTINO
        tasas_actuales = {}
        for divisa in self.divisas_creadas:
            if divisa.codigo in TASAS_CONFIG:
                config = TASAS_CONFIG[divisa.codigo]
                precio_base = config["precio_base"]
                comision_compra = config["comision_compra"]
                comision_venta = config["comision_venta"]

                # Crear o actualizar tasa actual (PYG -> divisa)
                tasa, created = TasaCambio.objects.get_or_create(
                    divisa_origen=pyg,
                    divisa_destino=divisa,
                    defaults={
                        "precio_base": precio_base,
                        "comision_compra": comision_compra,
                        "comision_venta": comision_venta,
                        "activo": True,
                    },
                )

                # Actualizar la tasa si ya existia (get_or_create no actualiza campos en defaults)
                if not created:
                    tasa.precio_base = precio_base
                    tasa.comision_compra = comision_compra
                    tasa.comision_venta = comision_venta
                    tasa.activo = True
                    tasa.save()

                tasas_actuales[divisa.codigo] = tasa

                if created:
                    self.stdout.write(
                        f"  Creada: PYG/{divisa.codigo} - "
                        f"Precio: {precio_base}, "
                        f"C.Venta: {comision_venta}, "
                        f"C.Compra: {comision_compra}"
                    )
                else:
                    self.stdout.write(
                        f"  Actualizada: PYG/{divisa.codigo} - "
                        f"Precio: {precio_base}, "
                        f"C.Venta: {comision_venta}, "
                        f"C.Compra: {comision_compra}"
                    )

        # Ahora crear el historial con variaciones realistas
        fecha_inicio = timezone.now() - timedelta(days=dias_historial)
        total_historial = 0

        for dias in range(dias_historial + 1):
            fecha_actual = fecha_inicio + timedelta(days=dias)

            # Crear historial para cada divisa
            for divisa in self.divisas_creadas:
                if divisa.codigo in TASAS_CONFIG and divisa.codigo in tasas_actuales:
                    config = TASAS_CONFIG[divisa.codigo]

                    # Calcular variacion diaria (-2% a +2%)
                    variacion = random.uniform(-0.02, 0.02)
                    precio_base = (config["precio_base"] * Decimal(str(1 + variacion))).quantize(Decimal("0.001"))
                    comision_compra = (config["comision_compra"] * Decimal(str(1 + variacion * 0.5))).quantize(
                        Decimal("0.001")
                    )
                    comision_venta = (config["comision_venta"] * Decimal(str(1 + variacion * 0.5))).quantize(
                        Decimal("0.001")
                    )

                    # Crear entrada en el historial (PYG -> divisa)
                    historial = TasaCambioHistorial.objects.create(
                        tasa_cambio_original=tasas_actuales[divisa.codigo],
                        divisa_origen=pyg,
                        divisa_destino=divisa,
                        precio_base=precio_base,
                        comision_compra=comision_compra,
                        comision_venta=comision_venta,
                        activo=True,
                        motivo=f"Fluctuacion de mercado - {fecha_actual.date()}",
                    )

                    # Actualizar la fecha del historial manualmente
                    historial.fecha_registro = fecha_actual
                    historial.save(update_fields=["fecha_registro"])

                    total_historial += 1

        self.stdout.write(f"  Total tasas actuales: {len(tasas_actuales)}")
        self.stdout.write(f"  Total historial creado: {total_historial}")

    def crear_datos_adicionales(self):
        """NO crea datos adicionales. Los tipos y entidades se manejan por otras vias."""
        self.stdout.write("NOTA: Datos adicionales NO se crean en este script")
        self.stdout.write("  Tipos de cliente: Se usan los 3 fijos (VIP, Corporativo, Minorista)")
        self.stdout.write("  Entidades financieras: Se obtienen de otra forma")

    def mostrar_resumen(self):
        """Muestra un resumen de los datos cargados."""
        self.stdout.write("RESUMEN DE DATOS CARGADOS:")
        self.stdout.write(f"  - Divisas: {Divisa.objects.count()}")
        self.stdout.write(f"  - Tipos de Cliente: {TipoCliente.objects.count()}")
        self.stdout.write(f"  - Usuarios: {User.objects.count()}")
        self.stdout.write(f"  - Clientes: {Cliente.objects.count()}")
        self.stdout.write(f"  - Entidades Financieras: {EntidadFinanciera.objects.count()}")
        medios_count = (
            TarjetaCredito.objects.count() + CuentaBancaria.objects.count() + BilleteraElectronica.objects.count()
        )
        self.stdout.write(f"  - Medios Financieros: {medios_count}")
        self.stdout.write(f"  - Tasas de Cambio: {TasaCambio.objects.count()}")
        self.stdout.write(f"  - Limites de Transacciones: {LimiteTransacciones.objects.count()}")
        self.stdout.write("")
        self.stdout.write("Sistema listo para pruebas y desarrollo!")
