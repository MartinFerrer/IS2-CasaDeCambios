"""Módulo para la integración con el servicio de Facturación Electrónica de la SET (SIFEN).

Integración con el API de Factura Segura para generar documentos electrónicos (DE) en Paraguay.

Este módulo implementa:
- Autenticación con token precargado (sin login dinámico)
- Gestión automática de rangos de numeración de documentos
- Cálculo y generación de documentos electrónicos (DE) con retry automático
- Descarga de archivos KuDE (PDF) y XML firmado
- Manejo de errores NUMDOC_ENVIADO_A_SIFEN y NUMDOC_SOL_APROBACION
- Logging completo de operaciones

Basado en el script funcional test_factura_segura.py
"""

import logging
from typing import Dict, List, Optional, Tuple

import requests
from django.http import HttpResponse
from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================================
# GESTOR DE NUMERACIÓN DE DOCUMENTOS
# ============================================================================


class GestorNumeracion:
    """Gestor de rangos de numeración de documentos electrónicos.

    Maneja múltiples rangos configurables y controla qué números ya fueron utilizados
    para evitar duplicados y manejar errores NUMDOC_* de SIFEN.
    """

    def __init__(self, rangos: List[Tuple[int, int]]):
        """Inicializar gestor con rangos de numeración.

        Args:
            rangos: Lista de tuplas (inicio, fin) con rangos válidos
                   Ejemplo: [(102, 150), (201, 300)]

        """
        self.rangos = rangos
        self.numeros_usados = set()
        self.ultimo_numero = None
        logger.info(f"GestorNumeracion inicializado con rangos: {rangos}")

    def obtener_siguiente_numero(self) -> Optional[str]:
        """Obtener el siguiente número de documento disponible.

        Returns:
            str: Número de documento formateado (ej: "0000102") o None si no hay más números

        """
        # Si ya usamos un número, intentar el siguiente
        inicio = self.ultimo_numero + 1 if self.ultimo_numero else None

        # Iterar sobre todos los rangos
        for rango_inicio, rango_fin in self.rangos:
            # Determinar desde donde empezar en este rango
            if inicio is None or inicio < rango_inicio:
                numero_actual = rango_inicio
            elif inicio <= rango_fin:
                numero_actual = inicio
            else:
                continue  # Este rango ya fue agotado

            # Buscar un número disponible en este rango
            while numero_actual <= rango_fin:
                if numero_actual not in self.numeros_usados:
                    self.ultimo_numero = numero_actual
                    self.numeros_usados.add(numero_actual)
                    numero_formateado = f"{numero_actual:07d}"
                    logger.info(f"Número asignado: {numero_formateado}")
                    return numero_formateado
                numero_actual += 1

        # No hay más números disponibles
        logger.error("No hay más números de documento disponibles en los rangos configurados")
        return None

    def marcar_numero_usado(self, numero: int):
        """Marcar un número como usado (para cuando SIFEN reporta que ya existe).

        Args:
            numero: Número de documento que ya fue usado

        """
        self.numeros_usados.add(numero)
        logger.warning(f"Número {numero} marcado como usado (ya existía en SIFEN)")

    def reiniciar(self):
        """Reiniciar el gestor (útil para testing)."""
        self.numeros_usados.clear()
        self.ultimo_numero = None
        logger.info("GestorNumeracion reiniciado")


# ============================================================================
# CLIENTE FACTURA SEGURA
# ============================================================================


def debug_print(message):
    """Print debug messages that will appear in Docker console."""
    print(f"[FACTURA-SEGURA-DEBUG] {message}")
    logger.info(message)


class FacturaSeguraError(Exception):
    """Excepción personalizada para errores del servicio Factura Segura."""

    pass


class FacturaSeguraClient:
    """Cliente para integración con el API de Factura Segura."""

    def __init__(self):
        """Inicializar el cliente con configuración desde Django settings.

        Usa el token precargado directamente como lo hace test_factura_segura.py.
        No intenta hacer login ya que el API tiene problemas con la autenticación dinámica.
        """
        from django.conf import settings

        # URLs desde settings
        self.login_url = settings.FACTURACION_LOGIN_URL
        self.base_url = settings.FACTURACION_API_URL

        # Credenciales desde settings
        self.email = settings.FACTURACION_EMAIL
        self.password = settings.FACTURACION_PASSWORD

        # Token precargado (como test_factura_segura.py)
        try:
            preloaded_token = settings.FACTURACION_PRELOADED_TOKEN
        except AttributeError:
            preloaded_token = ""

        self.auth_token = preloaded_token
        self.session = requests.Session()

        # Configurar headers con el token precargado
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authentication-Token": self.auth_token,
            }
        )

        # Logs detallados de configuración
        debug_print("=" * 60)
        debug_print("INICIALIZANDO CLIENTE FACTURA SEGURA")
        debug_print("=" * 60)
        debug_print(f"API_URL: {self.base_url}")
        debug_print(f"EMAIL: {self.email}")
        debug_print(f"TOKEN (parcial): {self.auth_token[:40]}..." if self.auth_token else "TOKEN: <NO CONFIGURADO>")
        debug_print("=" * 60)

        logger.info(f"Inicializando cliente Factura Segura con URL: {self.base_url}")
        logger.info(f"Email configurado: {self.email}")
        logger.info("Usando token precargado (sin login dinámico)")

        # Verificar que tenemos token
        if not self.auth_token:
            raise FacturaSeguraError("No se encontró FACTURACION_PRELOADED_TOKEN en la configuración")

    def test_connectivity(self) -> Dict:
        """Prueba la conectividad con el API de Factura Segura.

        Returns:
            Dict: Resultado de la prueba de conectividad

        """
        logger.info("=== PROBANDO CONECTIVIDAD ===")

        try:
            url = self.base_url
            # Probar con una operación simple para verificar conectividad
            test_payload = {
                "operation": "get_estado_sifen",
                "params": {"CDC": "01234567890123456789012345678901234567890123", "dRucEm": "80000001"},
            }

            print(f"[FACTURACION] Probando conectividad con: {url}")
            print(f"[FACTURACION] Headers: {dict(self.session.headers)}")
            print(f"[FACTURACION] Payload de prueba: {test_payload}")
            logger.info(f"Probando conectividad con: {url}")
            logger.info(f"Headers: {dict(self.session.headers)}")
            logger.info(f"Payload de prueba: {test_payload}")

            response = self.session.post(url, json=test_payload, timeout=30)

            print(f"[FACTURACION] Status: {response.status_code}")
            print(f"[FACTURACION] Content: {response.text[:500]}")
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Content: {response.text[:500]}")

            if response.status_code == 200:
                # Parsear respuesta JSON
                try:
                    result = response.json()
                    return {"success": True, "url": url, "status": response.status_code, "api_response": result}
                except Exception as e:
                    logger.warning(f"Error parseando JSON: {e}")

            # Cualquier respuesta del servidor indica que el endpoint existe
            if response.status_code in [200, 400, 401, 403, 500]:
                return {"success": True, "url": url, "status": response.status_code, "response": response.text[:500]}

        except Exception as e:
            logger.error(f"Error de conectividad: {e}")

        return {"success": False, "message": "No se pudo establecer conectividad con Factura Segura"}

    def calcular_de(self, datos_transaccion: Dict) -> Dict:
        """Calcula el documento electrónico (DE) enviando datos resumidos.

        Args:
            datos_transaccion: Datos de la transacción para calcular el DE

        Returns:
            Dict: Respuesta del servicio con el JSON_DE completo

        Raises:
            FacturaSeguraError: Si falla el cálculo del DE

        """
        try:
            # Usar estructura oficial de Factura Segura API
            url = self.base_url
            payload = {"operation": "calcular_de", "params": {"DE": datos_transaccion}}

            debug_print("=== CALCULANDO DE ===")
            debug_print(f"URL: {url}")
            debug_print(f"Headers: {dict(self.session.headers)}")
            debug_print(f"Payload completo: {payload}")

            response = self.session.post(url, json=payload, timeout=60)

            logger.info(f"Respuesta - Status: {response.status_code}")
            logger.info(f"Respuesta - Headers: {dict(response.headers)}")
            logger.info(f"Respuesta - Content: {response.text[:2000]}...")

            if response.status_code == 200:
                resultado = response.json()

                # Verificar estructura de respuesta según documentación
                if resultado.get("code") == 0:
                    # Operación exitosa
                    de_calculado = resultado.get("results", [{}])[0].get("DE", {})
                    operation_id = resultado.get("operation_info", {}).get("id")
                    logger.info(f"DE calculado exitosamente. Operation ID: {operation_id}")
                    return de_calculado
                else:
                    # Error en la operación
                    code = resultado.get("code")
                    description = resultado.get("description")
                    error_msg = f"Error en calcular_de - Code: {code}, Description: {description}"
                    logger.error(error_msg)
                    raise FacturaSeguraError(error_msg)
            else:
                error_msg = f"Error HTTP calculando DE: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise FacturaSeguraError(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión calculando DE: {e!s}"
            logger.error(error_msg)
            raise FacturaSeguraError(error_msg) from e

    def generar_de(self, json_de_completo: Dict) -> Dict:
        """Genera el documento electrónico (DE) final con los datos completos.

        Args:
            json_de_completo: JSON completo del DE obtenido de calcular_de

        Returns:
            Dict: Respuesta del servicio con el DE generado

        Raises:
            FacturaSeguraError: Si falla la generación del DE

        """
        try:
            # Usar estructura oficial de Factura Segura API
            url = self.base_url
            payload = {"operation": "generar_de", "params": {"DE": json_de_completo}}

            logger.info("=== GENERANDO DE ===")
            logger.info(f"URL: {url}")
            logger.info(f"Headers: {dict(self.session.headers)}")
            logger.info(f"Payload completo: {payload}")

            response = self.session.post(url, json=payload, timeout=60)

            logger.info(f"Respuesta - Status: {response.status_code}")
            logger.info(f"Respuesta - Headers: {dict(response.headers)}")
            logger.info(f"Respuesta - Content: {response.text[:2000]}...")

            if response.status_code == 200:
                resultado = response.json()

                # Verificar estructura de respuesta según documentación
                if resultado.get("code") == 0:
                    # Operación exitosa - obtener CDC del resultado
                    cdc = resultado.get("results", [{}])[0].get("CDC")
                    operation_id = resultado.get("operation_info", {}).get("id")
                    logger.info(f"DE generado exitosamente. CDC: {cdc}, Operation ID: {operation_id}")
                    return {"cdc": cdc, "operation_id": operation_id}
                else:
                    # Error en la operación
                    code = resultado.get("code")
                    description = resultado.get("description")
                    error_msg = f"Error en generar_de - Code: {code}, Description: {description}"
                    logger.error(error_msg)
                    raise FacturaSeguraError(error_msg)
            else:
                error_msg = f"Error HTTP generando DE: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise FacturaSeguraError(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión generando DE: {e!s}"
            logger.error(error_msg)
            raise FacturaSeguraError(error_msg) from e

    def descargar_kude_pdf(self, cdc: str, ruc_emisor: str = "2595733") -> Tuple[bytes, str]:
        """Descarga el archivo KuDE en formato PDF usando HTTP GET como test_factura_segura.py.

        Args:
            cdc: Código de Control del Documento Electrónico
            ruc_emisor: RUC del emisor (sin DV)

        Returns:
            Tuple[bytes, str]: Contenido del PDF y nombre del archivo

        Raises:
            FacturaSeguraError: Si falla la descarga

        """
        try:
            # Construir URL GET siguiendo patrón de test_factura_segura.py
            url = f"{self.base_url}/dwn_kude/{ruc_emisor}/{cdc}"

            debug_print("=== DESCARGANDO KUDE PDF ===")
            debug_print(f"URL: {url}")
            debug_print(f"Headers: {dict(self.session.headers)}")

            # Usar GET en lugar de POST
            response = self.session.get(url, timeout=60)

            debug_print(f"Respuesta - Status: {response.status_code}")
            debug_print(f"Respuesta - Content Length: {len(response.content)} bytes")

            if response.status_code == 200:
                # El contenido viene como bytes directos del PDF
                pdf_content = response.content
                filename = f"kude_{cdc}.pdf"

                debug_print(f"✓ KuDE PDF descargado exitosamente: {filename}")
                debug_print(f"Tamaño: {len(pdf_content)} bytes")
                return pdf_content, filename
            else:
                error_msg = f"Error descargando KuDE PDF: Status {response.status_code}"
                debug_print(f"✗ {error_msg}")
                try:
                    error_json = response.json()
                    debug_print(f"Error JSON: {error_json}")
                except Exception:
                    debug_print(f"Response: {response.text[:500]}")
                raise FacturaSeguraError(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión descargando KuDE PDF: {e!s}"
            logger.error(error_msg)
            raise FacturaSeguraError(error_msg) from e

    def descargar_xml_firmado(self, cdc: str, ruc_emisor: str = "2595733") -> Tuple[bytes, str]:
        """Descarga el archivo XML firmado usando HTTP GET como test_factura_segura.py.

        Args:
            cdc: Código de Control del Documento Electrónico
            ruc_emisor: RUC del emisor (sin DV)

        Returns:
            Tuple[bytes, str]: Contenido del XML y nombre del archivo

        Raises:
            FacturaSeguraError: Si falla la descarga

        """
        try:
            # Construir URL GET siguiendo patrón de test_factura_segura.py
            url = f"{self.base_url}/dwn_xml/{ruc_emisor}/{cdc}"

            debug_print("=== DESCARGANDO XML FIRMADO ===")
            debug_print(f"URL: {url}")
            debug_print(f"Headers: {dict(self.session.headers)}")

            # Usar GET en lugar de POST
            response = self.session.get(url, timeout=60)

            debug_print(f"Respuesta - Status: {response.status_code}")
            debug_print(f"Respuesta - Content Length: {len(response.content)} bytes")

            if response.status_code == 200:
                # El contenido viene como bytes directos del XML
                xml_content = response.content
                filename = f"de_{cdc}.xml"

                debug_print(f"✓ XML firmado descargado exitosamente: {filename}")
                debug_print(f"Tamaño: {len(xml_content)} bytes")
                return xml_content, filename
            else:
                error_msg = f"Error descargando XML firmado: Status {response.status_code}"
                debug_print(f"✗ {error_msg}")
                try:
                    error_json = response.json()
                    debug_print(f"Error JSON: {error_json}")
                except Exception:
                    debug_print(f"Response: {response.text[:500]}")
                raise FacturaSeguraError(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión descargando XML firmado: {e!s}"
            logger.error(error_msg)
            raise FacturaSeguraError(error_msg) from e


def _construir_de_payload(transaccion, num_doc: str) -> Dict:
    """Construir el payload DE con datos reales del cliente y transacción.

    Args:
        transaccion: Instancia del modelo Transaccion
        num_doc: Número de documento formateado (ej: "0000102")

    Returns:
        Dict: Estructura DE completa con datos del cliente

    """
    from django.conf import settings

    # Obtener configuración desde settings
    emisor = getattr(settings, "FACTURACION_EMISOR", {})
    timbrado = getattr(settings, "FACTURACION_TIMBRADO", {})

    # Fecha y hora actual en formato ISO
    now_iso = timezone.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Calcular monto en PYG (el monto pagado por el servicio)
    if transaccion.tipo_operacion == "compra":
        # Cliente compra divisa extranjera, paga en PYG
        monto_pyg = int(transaccion.monto_final) if transaccion.monto_final else 100
    else:
        # Cliente vende divisa extranjera, recibe PYG
        monto_pyg = int(transaccion.monto_destino) if transaccion.monto_destino else 100

    # Obtener datos del cliente
    cliente = transaccion.cliente
    try:
        # Intentar obtener primer usuario del cliente
        usuario = cliente.usuarios.first()
        email_cliente = usuario.email if usuario else "cliente@example.com"
        nombre_cliente = f"{usuario.first_name} {usuario.last_name}".strip() if usuario else "Cliente"
        if not nombre_cliente or nombre_cliente == "":
            nombre_cliente = "Cliente"
    except Exception:
        email_cliente = "cliente@example.com"
        nombre_cliente = "Cliente"

    # Datos del receptor (usar emisor como default para testing)
    ruc_receptor = emisor.get("ruc", "2595733")
    dv_receptor = emisor.get("dv", "3")

    # Construir descripción detallada del servicio
    divisa_origen = transaccion.divisa_origen.codigo if transaccion.divisa_origen else "USD"
    divisa_destino = transaccion.divisa_destino.codigo if transaccion.divisa_destino else "PYG"

    if transaccion.tipo_operacion == "compra":
        descripcion = f"Cambio de divisas: {divisa_destino} → {divisa_origen}"
        tipo_cambio_desc = f"Compra {divisa_origen}"
    else:
        descripcion = f"Cambio de divisas: {divisa_origen} → {divisa_destino}"
        tipo_cambio_desc = f"Venta {divisa_origen}"

    # Construir DE según estructura de test_factura_segura.py con datos reales
    de = {
        "iTipEmi": "1",
        "iTiDE": "1",
        "dNumTim": timbrado.get("numero", "80002247"),
        "dFeIniT": timbrado.get("fecha_inicio", "2023-12-27"),
        "dEst": timbrado.get("establecimiento", "001"),
        "dPunExp": timbrado.get("punto_expedicion", "003"),
        "dNumDoc": num_doc,
        "dFeEmiDE": now_iso,
        "iTipTra": "1",
        "iTImp": "1",
        "cMoneOpe": "PYG",
        "dCondTiCam": "1",
        "dTiCam": "1",
        "dRucEm": emisor.get("ruc", "2595733"),
        "dDVEmi": emisor.get("dv", "3"),
        "iTipCont": "2",
        "dNomEmi": emisor.get("razon_social", "Casa de Cambios Global Exchange"),
        "dDirEmi": emisor.get("direccion", "Av. Mariscal López 1234"),
        "dNumCas": emisor.get("numero_casa", "1234"),
        "cDepEmi": emisor.get("codigo_departamento", "11"),
        "dDesDepEmi": emisor.get("nombre_departamento", "CENTRAL"),
        "cCiuEmi": emisor.get("codigo_ciudad", "1"),
        "dDesCiuEmi": emisor.get("nombre_ciudad", "ASUNCION (DISTRITO)"),
        "dTelEmi": emisor.get("telefono", "(021)123456"),
        "dEmailE": emisor.get("email", "grupo4.is2.ge@gmail.com"),
        "gActEco": [
            {
                "cActEco": "46699",
                "dDesActEco": "Otras actividades de servicios financieros n.c.p.",
            }
        ],
        "iNatRec": "1",
        "iTiOpe": "1",
        "cPaisRec": "PRY",
        "iTiContRec": "1",
        "dRucRec": ruc_receptor,
        "dDVRec": dv_receptor,
        "iTipIDRec": "0",
        "dNumIDRec": "0",
        "dNomRec": nombre_cliente,
        "dEmailRec": email_cliente,
        "iIndPres": "1",
        "iCondOpe": "1",
        "gPaConEIni": [
            {
                "iTiPago": "1",
                "dMonTiPag": str(monto_pyg),
                "cMoneTiPag": "PYG",
                "dTiCamTiPag": "1",
            }
        ],
        "iCondCred": "1",
        "dPlazoCre": "0",
        "gCamItem": [
            {
                "dCodInt": "SVC001",
                "dDesProSer": descripcion,
                "cUniMed": "77",
                "dCantProSer": "1",
                "dPUniProSer": str(monto_pyg),
                "dDescItem": "0",
                "dDescGloItem": "0",
                "dAntPreUniIt": "0",
                "dAntGloPreUniIt": "0",
                "iAfecIVA": "3",  # 3 = Exento
                "dPropIVA": "0",  # 0% porque es exento
                "dTasaIVA": "0",  # Sin IVA
            }
        ],
        "CDC": "0",
        "dCodSeg": "0",
        "dDVId": "0",
        "dSisFact": "1",
        "dInfAdic": f"ID: {transaccion.id_transaccion} | {tipo_cambio_desc} | Tasa: {transaccion.tipo_cambio}",
    }

    return de


def generar_factura_electronica(transaccion, max_intentos: int = 10) -> Tuple[bool, str]:
    """Genera factura electrónica con retry automático para errores de número de documento.

    Implementa la lógica completa de:
    1. Verificar si ya existe factura
    2. Obtener número de documento del gestor de numeración
    3. calcular_de con el número
    4. generar_de para obtener el CDC
    5. Si falla por NUMDOC_*, reintentar con siguiente número (máx 10 intentos)
    6. Guardar CDC en la transacción

    Args:
        transaccion: Instancia del modelo Transaccion completada
        max_intentos: Máximo número de reintentos (default: 10)

    Returns:
        Tuple[bool, str]: (éxito, mensaje_o_cdc)
            - (True, "CDC...") si se generó exitosamente
            - (False, "error...") si falló

    """
    from django.conf import settings

    try:
        # Verificar estado
        if transaccion.estado != "completada":
            msg = f"Transacción debe estar completada (estado actual: {transaccion.estado})"
            logger.warning(msg)
            return False, msg

        # Verificar si ya tiene factura
        if transaccion.cdc_factura:
            msg = f"Transacción ya tiene factura: {transaccion.cdc_factura}"
            logger.info(msg)
            return True, transaccion.cdc_factura

        # Obtener rangos de numeración desde settings
        rangos = getattr(settings, "FACTURACION_RANGOS_NUMERACION", [(102, 150)])
        gestor = GestorNumeracion(rangos)

        # Inicializar cliente
        try:
            cliente = FacturaSeguraClient()
        except FacturaSeguraError as e:
            msg = f"Error de autenticación: {e!s}"
            logger.error(msg)
            return False, msg

        logger.info(f"Iniciando generación de factura para transacción {transaccion.id_transaccion}")

        # Intentar hasta max_intentos veces
        for intento in range(1, max_intentos + 1):
            # Obtener siguiente número disponible
            num_doc = gestor.obtener_siguiente_numero()
            if not num_doc:
                msg = "No hay más números de documento disponibles en los rangos configurados"
                logger.error(msg)
                return False, msg

            logger.info(f"Intento {intento}/{max_intentos} con número de documento: {num_doc}")

            try:
                # Construir payload DE
                de_payload = _construir_de_payload(transaccion, num_doc)

                # Paso 1: calcular_de
                logger.debug("Llamando calcular_de...")
                de_calculado = cliente.calcular_de(de_payload)

                # Paso 2: generar_de
                logger.debug("Llamando generar_de...")
                resultado = cliente.generar_de(de_calculado)

                # Extraer CDC del resultado
                cdc = resultado.get("cdc")
                if not cdc:
                    # Intentar extraer de results[0]
                    results = resultado.get("results", [])
                    if results and len(results) > 0:
                        cdc = results[0].get("CDC")

                if cdc:
                    # ¡Éxito! Guardar en BD
                    transaccion.cdc_factura = cdc
                    transaccion.fecha_facturacion = timezone.now()
                    transaccion.save(update_fields=["cdc_factura", "fecha_facturacion"])

                    logger.info(f"✓ Factura generada exitosamente. CDC: {cdc}")
                    return True, cdc
                else:
                    msg = "No se recibió CDC en la respuesta"
                    logger.error(f"Respuesta sin CDC: {resultado}")
                    return False, msg

            except FacturaSeguraError as e:
                error_str = str(e).upper()

                # Detectar errores de numeración que requieren retry
                if "NUMDOC_ENVIADO_A_SIFEN" in error_str or "NUMDOC_SOL_APROBACION" in error_str:
                    logger.warning(f"Número {num_doc} ya usado en SIFEN. Reintentando con siguiente número...")
                    gestor.marcar_numero_usado(int(num_doc))
                    continue  # Reintentar con siguiente número

                # Otros errores no recuperables
                msg = f"Error no recuperable: {e!s}"
                logger.error(msg)
                return False, msg

            except Exception as e:
                msg = f"Error inesperado: {e!s}"
                logger.error(msg, exc_info=True)
                return False, msg

        # Agotados todos los intentos
        msg = f"Se agotaron los {max_intentos} intentos para generar la factura"
        logger.error(msg)
        return False, msg

    except Exception as e:
        msg = f"Error crítico en generación de factura: {e!s}"
        logger.error(msg, exc_info=True)
        return False, msg


# ============================================================================
# FUNCIONES SIMPLES DE DESCARGA (reciben CDC directamente)
# ============================================================================


def visualizar_kude_pdf(cdc: str, ruc_emisor: str = "2595733") -> HttpResponse:
    """Visualizar factura KuDE en PDF (inline en navegador).

    Args:
        cdc: Código de Control del documento electrónico
        ruc_emisor: RUC del emisor (sin DV)

    Returns:
        HttpResponse con PDF para visualizar

    """
    try:
        cliente = FacturaSeguraClient()
        pdf_content, filename = cliente.descargar_kude_pdf(cdc, ruc_emisor)

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'  # inline para visualizar
        response["Content-Length"] = len(pdf_content)

        return response
    except Exception as e:
        logger.error(f"Error visualizando KuDE PDF para CDC {cdc}: {e!s}")
        return HttpResponse(f"Error visualizando factura: {e!s}", status=500)


def descargar_kude_pdf(cdc: str, ruc_emisor: str = "2595733") -> HttpResponse:
    """Descargar factura KuDE en PDF.

    Args:
        cdc: Código de Control del documento electrónico
        ruc_emisor: RUC del emisor (sin DV)

    Returns:
        HttpResponse con PDF para descargar

    """
    try:
        cliente = FacturaSeguraClient()
        pdf_content, filename = cliente.descargar_kude_pdf(cdc, ruc_emisor)

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'  # attachment para descargar
        response["Content-Length"] = len(pdf_content)

        return response
    except Exception as e:
        logger.error(f"Error descargando KuDE PDF para CDC {cdc}: {e!s}")
        return HttpResponse(f"Error descargando factura: {e!s}", status=500)


def descargar_xml_firmado(cdc: str, ruc_emisor: str = "2595733") -> HttpResponse:
    """Descargar XML firmado del documento electrónico.

    Args:
        cdc: Código de Control del documento electrónico
        ruc_emisor: RUC del emisor (sin DV)

    Returns:
        HttpResponse con XML para descargar

    """
    try:
        cliente = FacturaSeguraClient()
        xml_content, filename = cliente.descargar_xml_firmado(cdc, ruc_emisor)

        response = HttpResponse(xml_content, content_type="application/xml")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = len(xml_content)

        return response
    except Exception as e:
        logger.error(f"Error descargando XML firmado para CDC {cdc}: {e!s}")
        return HttpResponse(f"Error descargando XML: {e!s}", status=500)


# ============================================================================
# VISTAS DE DJANGO (integran con models y authentication)
# ============================================================================


def descargar_kude_pdf_view(request, transaccion_id: str) -> HttpResponse:
    """Vista para descargar el PDF del KuDE de una transacción.

    Args:
        request: HttpRequest
        transaccion_id: ID de la transacción

    Returns:
        HttpResponse: Respuesta con el PDF para descarga

    """
    try:
        from django.conf import settings

        from .models import Transaccion

        # Obtener transacción
        transaccion = Transaccion.objects.get(id_transaccion=transaccion_id, cliente__usuarios=request.user)

        # Verificar que tenga CDC
        if not transaccion.cdc_factura:
            return HttpResponse("Esta transacción no tiene factura electrónica generada.", status=400)

        # Obtener RUC del emisor desde settings
        emisor = getattr(settings, "FACTURACION_EMISOR", {})
        ruc_emisor = emisor.get("ruc", "2595733")

        # Inicializar cliente y descargar
        cliente = FacturaSeguraClient()
        pdf_content, filename = cliente.descargar_kude_pdf(transaccion.cdc_factura, ruc_emisor)

        # Crear respuesta HTTP con el PDF
        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = len(pdf_content)

        logger.info(f"KuDE PDF descargado para transacción: {transaccion_id}")

        return response

    except Exception as e:
        logger.error(f"Error descargando KuDE PDF para transacción {transaccion_id}: {e!s}")
        return HttpResponse(f"Error descargando PDF: {e!s}", status=500)


def descargar_xml_firmado_view(request, transaccion_id: str) -> HttpResponse:
    """Vista para descargar el XML firmado de una transacción.

    Args:
        request: HttpRequest
        transaccion_id: ID de la transacción

    Returns:
        HttpResponse: Respuesta con el XML para descarga

    """
    try:
        from django.conf import settings

        from .models import Transaccion

        # Obtener transacción
        transaccion = Transaccion.objects.get(id_transaccion=transaccion_id, cliente__usuarios=request.user)

        # Verificar que tenga CDC
        if not transaccion.cdc_factura:
            return HttpResponse("Esta transacción no tiene factura electrónica generada.", status=400)

        # Obtener RUC del emisor desde settings
        emisor = getattr(settings, "FACTURACION_EMISOR", {})
        ruc_emisor = emisor.get("ruc", "2595733")

        # Inicializar cliente y descargar
        cliente = FacturaSeguraClient()
        xml_content, filename = cliente.descargar_xml_firmado(transaccion.cdc_factura, ruc_emisor)

        # Crear respuesta HTTP con el XML
        response = HttpResponse(xml_content, content_type="application/xml")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = len(xml_content)

        logger.info(f"XML firmado descargado para transacción: {transaccion_id}")

        return response

    except Exception as e:
        logger.error(f"Error descargando XML firmado para transacción {transaccion_id}: {e!s}")
        return HttpResponse(f"Error descargando XML: {e!s}", status=500)


def visualizar_kude_pdf_view(request, transaccion_id: str) -> HttpResponse:
    """Vista para visualizar el PDF del KuDE en el navegador.

    Args:
        request: HttpRequest
        transaccion_id: ID de la transacción

    Returns:
        HttpResponse: Respuesta con el PDF para visualización inline

    """
    try:
        from django.conf import settings

        from .models import Transaccion

        # Obtener transacción
        transaccion = Transaccion.objects.get(id_transaccion=transaccion_id, cliente__usuarios=request.user)

        # Verificar que tenga CDC
        if not transaccion.cdc_factura:
            return HttpResponse("Esta transacción no tiene factura electrónica generada.", status=400)

        # Obtener RUC del emisor desde settings
        emisor = getattr(settings, "FACTURACION_EMISOR", {})
        ruc_emisor = emisor.get("ruc", "2595733")

        # Inicializar cliente y descargar
        cliente = FacturaSeguraClient()
        pdf_content, filename = cliente.descargar_kude_pdf(transaccion.cdc_factura, ruc_emisor)

        # Crear respuesta HTTP para visualización inline
        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        response["Content-Length"] = len(pdf_content)

        logger.info(f"KuDE PDF visualizado para transacción: {transaccion_id}")

        return response

    except Exception as e:
        logger.error(f"Error visualizando KuDE PDF para transacción {transaccion_id}: {e!s}")
        return HttpResponse(f"Error visualizando PDF: {e!s}", status=500)


# Función utilitaria para integrar con el flujo existente
def procesar_facturacion_post_pago(transaccion) -> Tuple[bool, str]:
    """Función para llamar después de completar exitosamente una transacción.

    Esta función se ejecuta automáticamente cuando una transacción se completa (estado="completada")
    para todos los medios de pago: Stripe, tarjeta local, transferencia bancaria, efectivo/TAUSER.

    Args:
        transaccion: Instancia del modelo Transaccion que se acaba de completar

    Returns:
        Tuple[bool, str]: (éxito, mensaje_o_cdc)
            - (True, "CDC...") si se generó exitosamente
            - (False, "error...") si falló

    """
    try:
        # Solo procesar si la transacción está completada
        if transaccion.estado != "completada":
            msg = f"Transacción no está completada (estado: {transaccion.estado})"
            logger.warning(msg)
            return False, msg

        logger.info(f"Iniciando facturación automática para transacción: {transaccion.id_transaccion}")

        exito, resultado = generar_factura_electronica(transaccion)

        if exito:
            logger.info(
                f"Facturación automática exitosa. CDC: {resultado} para transacción: {transaccion.id_transaccion}"
            )
        else:
            logger.warning(f"Facturación automática falló: {resultado} para transacción: {transaccion.id_transaccion}")

        return exito, resultado

    except Exception as e:
        msg = f"Error en facturación automática: {e!s}"
        logger.error(f"{msg} para transacción {transaccion.id_transaccion}", exc_info=True)
        # No relanzar la excepción para no afectar el flujo principal de la transacción
        return False, msg
