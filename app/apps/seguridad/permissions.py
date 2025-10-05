"""Constantes de permisos para el sistema de casa de cambios.

Este módulo define las constantes de permisos personalizados que se utilizan
en el sistema, además de los permisos CRUD generados automáticamente por Django.
"""

# Permisos CRUD automáticos de Django (para referencia)
# Formato: <acción>_<modelo>
# Acciones: add, change, delete, view

# ============================================================================
# PERMISOS DE USUARIOS
# ============================================================================
PERM_ADD_USUARIO = "add_usuario"
PERM_CHANGE_USUARIO = "change_usuario"
PERM_DELETE_USUARIO = "delete_usuario"
PERM_VIEW_USUARIO = "view_usuario"

# ============================================================================
# PERMISOS DE CLIENTES
# ============================================================================
PERM_ADD_CLIENTE = "add_cliente"
PERM_CHANGE_CLIENTE = "change_cliente"
PERM_DELETE_CLIENTE = "delete_cliente"
PERM_VIEW_CLIENTE = "view_cliente"

# ============================================================================
# PERMISOS DE TIPOS DE CLIENTE
# ============================================================================
PERM_ADD_TIPOCLIENTE = "add_tipocliente"
PERM_CHANGE_TIPOCLIENTE = "change_tipocliente"
PERM_DELETE_TIPOCLIENTE = "delete_tipocliente"
PERM_VIEW_TIPOCLIENTE = "view_tipocliente"

# ============================================================================
# PERMISOS DE TRANSACCIONES
# ============================================================================
PERM_ADD_TRANSACCION = "add_transaccion"
PERM_CHANGE_TRANSACCION = "change_transaccion"
PERM_DELETE_TRANSACCION = "delete_transaccion"
PERM_VIEW_TRANSACCION = "view_transaccion"

# ============================================================================
# PERMISOS DE OPERACIONES
# ============================================================================
PERM_ADD_OPERACION = "add_operacion"
PERM_CHANGE_OPERACION = "change_operacion"
PERM_DELETE_OPERACION = "delete_operacion"
PERM_VIEW_OPERACION = "view_operacion"

# ============================================================================
# PERMISOS DE ENTIDADES FINANCIERAS
# ============================================================================
PERM_ADD_ENTIDADFINANCIERA = "add_entidadfinanciera"
PERM_CHANGE_ENTIDADFINANCIERA = "change_entidadfinanciera"
PERM_DELETE_ENTIDADFINANCIERA = "delete_entidadfinanciera"
PERM_VIEW_ENTIDADFINANCIERA = "view_entidadfinanciera"

# ============================================================================
# PERMISOS DE LÍMITES DE TRANSACCIONES
# ============================================================================
PERM_ADD_LIMITETRANSACCIONES = "add_limitetransacciones"
PERM_CHANGE_LIMITETRANSACCIONES = "change_limitetransacciones"
PERM_DELETE_LIMITETRANSACCIONES = "delete_limitetransacciones"
PERM_VIEW_LIMITETRANSACCIONES = "view_limitetransacciones"

# ============================================================================
# PERMISOS DE SISTEMA / ADMIN
# ============================================================================
# Objetos administrativos creados por Django y relacionados con auditing/sesiones
PERM_ADD_LOGENTRY = "add_logentry"
PERM_CHANGE_LOGENTRY = "change_logentry"
PERM_DELETE_LOGENTRY = "delete_logentry"
PERM_VIEW_LOGENTRY = "view_logentry"

PERM_ADD_GROUP = "add_group"
PERM_CHANGE_GROUP = "change_group"
PERM_DELETE_GROUP = "delete_group"
PERM_VIEW_GROUP = "view_group"

PERM_ADD_PERMISSION = "add_permission"
PERM_CHANGE_PERMISSION = "change_permission"
PERM_DELETE_PERMISSION = "delete_permission"
PERM_VIEW_PERMISSION = "view_permission"

PERM_ADD_CONTENTTYPE = "add_contenttype"
PERM_CHANGE_CONTENTTYPE = "change_contenttype"
PERM_DELETE_CONTENTTYPE = "delete_contenttype"
PERM_VIEW_CONTENTTYPE = "view_contenttype"

PERM_ADD_SESSION = "add_session"
PERM_CHANGE_SESSION = "change_session"
PERM_DELETE_SESSION = "delete_session"
PERM_VIEW_SESSION = "view_session"

# ============================================================================
# PERMISOS DE OPERACIONES / DIVISAS Y TASAS
# ============================================================================
PERM_ADD_DIVISA = "add_divisa"
PERM_CHANGE_DIVISA = "change_divisa"
PERM_DELETE_DIVISA = "delete_divisa"
PERM_VIEW_DIVISA = "view_divisa"

PERM_ADD_TASACAMBIO = "add_tasacambio"
PERM_CHANGE_TASACAMBIO = "change_tasacambio"
PERM_DELETE_TASACAMBIO = "delete_tasacambio"
PERM_VIEW_TASACAMBIO = "view_tasacambio"

PERM_ADD_TASACAMBIOHISTORIAL = "add_tasacambiohistorial"
PERM_CHANGE_TASACAMBIOHISTORIAL = "change_tasacambiohistorial"
PERM_DELETE_TASACAMBIOHISTORIAL = "delete_tasacambiohistorial"
PERM_VIEW_TASACAMBIOHISTORIAL = "view_tasacambiohistorial"

# ============================================================================
# PERMISOS DE MEDIOS FINANCIEROS
# ============================================================================
PERM_ADD_BILLETERAELECTRONICA = "add_billeteraelectronica"
PERM_CHANGE_BILLETERAELECTRONICA = "change_billeteraelectronica"
PERM_DELETE_BILLETERAELECTRONICA = "delete_billeteraelectronica"
PERM_VIEW_BILLETERAELECTRONICA = "view_billeteraelectronica"

PERM_ADD_CUENTABANCARIA = "add_cuentabancaria"
PERM_CHANGE_CUENTABANCARIA = "change_cuentabancaria"
PERM_DELETE_CUENTABANCARIA = "delete_cuentabancaria"
PERM_VIEW_CUENTABANCARIA = "view_cuentabancaria"

PERM_ADD_TARJETACREDITO = "add_tarjetacredito"
PERM_CHANGE_TARJETACREDITO = "change_tarjetacredito"
PERM_DELETE_TARJETACREDITO = "delete_tarjetacredito"
PERM_VIEW_TARJETACREDITO = "view_tarjetacredito"

# ============================================================================
# PERMISOS ADMINISTRATIVOS
# ============================================================================
# Permisos relacionados con configuración del sistema
PERM_CHANGE_COMISIONES = "change_comisiones"  # Modificar comisiones
PERM_CHANGE_LIMITES = "change_limites"  # Modificar límites de transacciones
PERM_VIEW_REPORTES = "view_reportes"  # Ver reportes
PERM_GENERATE_REPORTES = "generate_reportes"  # Generar reportes
# Permisos para asociación de cliente
PERM_ASOCIAR_CLIENTE = "asociar_cliente"
PERM_DESASOCIAR_CLIENTE = "desasociar_cliente"
# Permisos específicos para gestión de roles
PERM_VIEW_ROL = "view_rol"
PERM_ASIGNAR_PERMISO_ROL = "asignar_permiso_rol"
PERM_DESASIGNAR_PERMISO_ROL = "desasignar_permiso_rol"


def get_permission_display_name(codename: str) -> str:
    """Obtiene el nombre amigable de un permiso basado en su codename.

    Args:
        codename: El codename del permiso.

    Returns:
        El nombre amigable del permiso.

    """
    permission_names = {
        # Usuarios
        PERM_ADD_USUARIO: "Crear usuarios",
        PERM_CHANGE_USUARIO: "Modificar usuarios",
        PERM_DELETE_USUARIO: "Eliminar usuarios",
        PERM_VIEW_USUARIO: "Ver usuarios",
        # Clientes
        PERM_ADD_CLIENTE: "Crear clientes",
        PERM_CHANGE_CLIENTE: "Modificar clientes",
        PERM_DELETE_CLIENTE: "Eliminar clientes",
        PERM_VIEW_CLIENTE: "Ver clientes",
        # Tipos de cliente
        PERM_ADD_TIPOCLIENTE: "Crear tipos de cliente",
        PERM_CHANGE_TIPOCLIENTE: "Modificar tipos de cliente",
        PERM_DELETE_TIPOCLIENTE: "Eliminar tipos de cliente",
        PERM_VIEW_TIPOCLIENTE: "Ver tipos de cliente",
        # Transacciones
        PERM_ADD_TRANSACCION: "Crear transacciones",
        PERM_CHANGE_TRANSACCION: "Modificar transacciones",
        PERM_DELETE_TRANSACCION: "Eliminar transacciones",
        PERM_VIEW_TRANSACCION: "Ver transacciones",
        # Operaciones
        PERM_ADD_OPERACION: "Crear operaciones",
        PERM_CHANGE_OPERACION: "Modificar operaciones",
        PERM_DELETE_OPERACION: "Eliminar operaciones",
        PERM_VIEW_OPERACION: "Ver operaciones",
        # Entidades financieras
        PERM_ADD_ENTIDADFINANCIERA: "Crear entidades financieras",
        PERM_CHANGE_ENTIDADFINANCIERA: "Modificar entidades financieras",
        PERM_DELETE_ENTIDADFINANCIERA: "Eliminar entidades financieras",
        PERM_VIEW_ENTIDADFINANCIERA: "Ver entidades financieras",
        # Límites
        PERM_ADD_LIMITETRANSACCIONES: "Crear límites de transacciones",
        PERM_CHANGE_LIMITETRANSACCIONES: "Modificar límites de transacciones",
        PERM_DELETE_LIMITETRANSACCIONES: "Eliminar límites de transacciones",
        PERM_VIEW_LIMITETRANSACCIONES: "Ver límites de transacciones",
        # Administrativos
        PERM_CHANGE_COMISIONES: "Modificar comisiones",
        PERM_VIEW_REPORTES: "Ver reportes",
        PERM_GENERATE_REPORTES: "Generar reportes",
        # Sistema / admin
        PERM_ADD_LOGENTRY: "Crear entradas de log",
        PERM_CHANGE_LOGENTRY: "Modificar entradas de log",
        PERM_DELETE_LOGENTRY: "Eliminar entradas de log",
        PERM_VIEW_LOGENTRY: "Ver entradas de log",
        PERM_ADD_GROUP: "Crear grupos",
        PERM_CHANGE_GROUP: "Modificar grupos",
        PERM_DELETE_GROUP: "Eliminar grupos",
        PERM_VIEW_GROUP: "Ver grupos",
        PERM_ADD_PERMISSION: "Crear permisos",
        PERM_CHANGE_PERMISSION: "Modificar permisos",
        PERM_DELETE_PERMISSION: "Eliminar permisos",
        PERM_VIEW_PERMISSION: "Ver permisos",
        PERM_ADD_CONTENTTYPE: "Crear content types",
        PERM_CHANGE_CONTENTTYPE: "Modificar content types",
        PERM_DELETE_CONTENTTYPE: "Eliminar content types",
        PERM_VIEW_CONTENTTYPE: "Ver content types",
        PERM_ADD_SESSION: "Crear sesiones",
        PERM_CHANGE_SESSION: "Modificar sesiones",
        PERM_DELETE_SESSION: "Eliminar sesiones",
        PERM_VIEW_SESSION: "Ver sesiones",
        # Divisas y tasas
        PERM_ADD_DIVISA: "Crear divisas",
        PERM_CHANGE_DIVISA: "Modificar divisas",
        PERM_DELETE_DIVISA: "Eliminar divisas",
        PERM_VIEW_DIVISA: "Ver divisas",
        PERM_ADD_TASACAMBIO: "Crear tasa de cambio",
        PERM_CHANGE_TASACAMBIO: "Modificar tasa de cambio",
        PERM_DELETE_TASACAMBIO: "Eliminar tasa de cambio",
        PERM_VIEW_TASACAMBIO: "Ver tasa de cambio",
        PERM_ADD_TASACAMBIOHISTORIAL: "Crear historial de tasa de cambio",
        PERM_CHANGE_TASACAMBIOHISTORIAL: "Modificar historial de tasa de cambio",
        PERM_DELETE_TASACAMBIOHISTORIAL: "Eliminar historial de tasa de cambio",
        PERM_VIEW_TASACAMBIOHISTORIAL: "Ver historial de tasa de cambio",
        # Medios financieros
        PERM_ADD_BILLETERAELECTRONICA: "Crear billetera electrónica",
        PERM_CHANGE_BILLETERAELECTRONICA: "Modificar billetera electrónica",
        PERM_DELETE_BILLETERAELECTRONICA: "Eliminar billetera electrónica",
        PERM_VIEW_BILLETERAELECTRONICA: "Ver billetera electrónica",
        PERM_ADD_CUENTABANCARIA: "Crear cuenta bancaria",
        PERM_CHANGE_CUENTABANCARIA: "Modificar cuenta bancaria",
        PERM_DELETE_CUENTABANCARIA: "Eliminar cuenta bancaria",
        PERM_VIEW_CUENTABANCARIA: "Ver cuenta bancaria",
        PERM_ADD_TARJETACREDITO: "Crear tarjeta de crédito",
        PERM_CHANGE_TARJETACREDITO: "Modificar tarjeta de crédito",
        PERM_DELETE_TARJETACREDITO: "Eliminar tarjeta de crédito",
        PERM_VIEW_TARJETACREDITO: "Ver tarjeta de crédito",
        # Asociación de clientes
        PERM_ASOCIAR_CLIENTE: "Asociar cliente a usuario",
        PERM_DESASOCIAR_CLIENTE: "Desasociar cliente de usuario",
        # Roles / gestión de permisos sobre roles
        PERM_VIEW_ROL: "Ver roles",
        PERM_ASIGNAR_PERMISO_ROL: "Asignar permiso a rol",
        PERM_DESASIGNAR_PERMISO_ROL: "Desasignar permiso de rol",
    }
    return permission_names.get(codename, codename)
