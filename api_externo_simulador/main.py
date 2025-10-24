#!/usr/bin/env python3
"""
API Externo Simulador - Servicio Bancario

Este servicio simula APIs externas para la Casa de Cambios.
Actualmente incluye simulación bancaria, pero puede expandirse para otros servicios.
Proporciona endpoints REST para procesar pagos con criterios de éxito/fallo.
"""

import os
import random
import time
from datetime import datetime
from typing import Any, Dict

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Permitir CORS para llamadas desde el frontend

# Configuración del simulador (usando variables de entorno)
CONFIG = {
    "puerto": int(os.getenv("PUERTO", 5001)),
    "host": os.getenv("HOST", "0.0.0.0"),
    "tiempo_procesamiento_min": int(os.getenv("TIEMPO_PROCESAMIENTO_MIN", 2)),
    "tiempo_procesamiento_max": int(os.getenv("TIEMPO_PROCESAMIENTO_MAX", 5)),
    "probabilidad_exito": float(os.getenv("PROBABILIDAD_EXITO", 0.7)),
}

# Códigos de error bancarios simulados
ERRORES_BANCARIOS = [
    {"codigo": "ERR-001", "mensaje": "Fondos insuficientes en la cuenta"},
    {"codigo": "ERR-002", "mensaje": "Tarjeta bloqueada o vencida"},
    {"codigo": "ERR-003", "mensaje": "Error de conexión con el banco emisor"},
    {"codigo": "ERR-004", "mensaje": "Transacción rechazada por políticas de seguridad"},
    {"codigo": "ERR-005", "mensaje": "Límite diario de transacciones excedido"},
    {"codigo": "ERR-006", "mensaje": "Datos de tarjeta inválidos"},
    {"codigo": "ERR-007", "mensaje": "Transacción duplicada"},
    {"codigo": "ERR-008", "mensaje": "Monto de transacción excede límites permitidos"},
    {"codigo": "ERR-009", "mensaje": "Servicio bancario temporalmente no disponible"},
    {"codigo": "ERR-010", "mensaje": "Error de autenticación con el banco"},
]

# Simulación de cuentas/tarjetas que siempre fallan
CUENTAS_QUE_FALLAN = [
    "1111111111111111",
    "4000000000000002",
    "5555555555554444",
]

# Cuentas que siempre tienen éxito
CUENTAS_EXITOSAS = [
    "4000000000000077",  
    "5555555555555557",  
    "3782822463100059",  
]


def determinar_resultado_transaccion(datos_transaccion: Dict[str, Any]) -> Dict[str, Any]:
    """Determina si una transacción es exitosa o falla."""
    transaccion_id = datos_transaccion.get("transaccion_id")
    numero_cuenta = datos_transaccion.get("numero_cuenta", "")
    medio_pago = datos_transaccion.get("medio_pago", "efectivo")
    medio_cobro = datos_transaccion.get("medio_cobro", "efectivo")
    
    print("ANÁLISIS DEL MEDIO DE PAGO:")
    print(f"   Medio pago: {medio_pago}")
    print(f"   Medio cobro: {medio_cobro}")
    
    # Determinar el tipo de identificador basado en el medio de pago
    identificador_tipo = "N/A"
    if numero_cuenta:
        # Determinar el tipo basado en el medio de pago
        if medio_pago.startswith("tarjeta_"):
            identificador_tipo = "Número de tarjeta"
        elif medio_pago.startswith("cuenta_"):
            identificador_tipo = "Número de cuenta"
        elif medio_pago.startswith("billetera_"):
            identificador_tipo = "Identificador de billetera"
        else:
            identificador_tipo = "Número de cuenta/tarjeta"
    
    print(f"   {identificador_tipo}: {numero_cuenta}")
    
    # Verificar si hay números de cuenta/tarjeta específicos para QA
    if numero_cuenta in CUENTAS_QUE_FALLAN:
        error = random.choice(ERRORES_BANCARIOS)
        print("   Resultado: FALLO (cuenta en lista de fallos de QA)")
        return {
            "exito": False,
            "codigo_error": error["codigo"],
            "mensaje_error": error["mensaje"],
            "transaccion_id": transaccion_id,
        }
    
    if numero_cuenta in CUENTAS_EXITOSAS:
        print("   Resultado: ÉXITO (cuenta en lista de éxitos de QA)")
        return {
            "exito": True,
            "transaccion_id": transaccion_id,
        }

    # Resultado aleatorio basado en probabilidad ajustada
    exito = random.random() < CONFIG["probabilidad_exito"]
    
    if exito:
        print("   Resultado: ÉXITO")
        return {
            "exito": True,
            "transaccion_id": transaccion_id,
        }
    else:
        error = random.choice(ERRORES_BANCARIOS)
        print(f"   Resultado: FALLO ({error['codigo']})")
        return {
            "exito": False,
            "codigo_error": error["codigo"],
            "mensaje_error": error["mensaje"],
            "transaccion_id": transaccion_id,
        }

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de health check."""
    return jsonify({
        "status": "healthy",
        "service": "API Externo Simulador - Banco",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })


@app.route("/api/procesar-transaccion", methods=["POST"])
def procesar_transaccion():
    """
    Procesa una transacción bancaria.
    
    Expected JSON:
    {
        "transaccion_id": "string",
        "monto": float,
        "divisa": "string",
        "medio_pago": "string",
        "numero_cuenta": "string (opcional)",
        "datos_adicionales": {}
    }
    
    Returns:
    {
        "exito": bool,
        "codigo_error": "string" | null,
        "mensaje_error": "string" | null,
        "transaccion_id": "string"
    }
    """
    try:
        datos = request.get_json()
        
        # ===== LOGS DE DEBUG DETALLADOS =====
        print("=" * 80)
        print(f"[{datetime.now()}] NUEVA TRANSACCIÓN RECIBIDA")
        print("=" * 80)
        
        if not datos:
            print("ERROR: No se enviaron datos en el request")
            return jsonResponse({"error": "No se enviaron datos"}, 400)
        
        # Log completo de todos los datos recibidos
        print("DATOS COMPLETOS RECIBIDOS:")
        for key, value in datos.items():
            print(f"   {key}: {value} (tipo: {type(value).__name__})")
        
        print("\nINFORMACIÓN DE PAGO:")
        print(f"   Monto: {datos.get('monto', 'N/A')} {datos.get('divisa', 'N/A')}")
        
        # Información detallada de medios de pago y cobro
        medio_pago = datos.get('medio_pago', 'N/A')
        medio_cobro = datos.get('medio_cobro', 'N/A')
        numero_cuenta = datos.get('numero_cuenta', 'N/A')
        datos_adicionales = datos.get('datos_adicionales', {})
        
        print(f"   Medio de pago: {medio_pago}")
        print(f"   Medio de cobro: {medio_cobro}")
        
        # Determinar el tipo de identificador dinámicamente
        if numero_cuenta != 'N/A':
            if medio_pago.startswith("tarjeta_"):
                print(f"   Número de tarjeta: {numero_cuenta}")
            elif medio_pago.startswith("cuenta_"):
                print(f"   Número de cuenta bancaria: {numero_cuenta}")
            elif medio_pago.startswith("billetera_"):
                print(f"   Identificador de billetera: {numero_cuenta}")
            else:
                print(f"   Número de cuenta/tarjeta: {numero_cuenta}")
        else:
            print(f"   Identificador financiero: {numero_cuenta}")
        
        # Información adicional de la transacción
        print(f"   Monto origen: {datos_adicionales.get('monto_origen', 'N/A')} {datos_adicionales.get('divisa_origen', 'N/A')}")
        print(f"   Tasa aplicada: {datos_adicionales.get('tasa_aplicada', 'N/A')}")
        print(f"   Fecha transacción: {datos_adicionales.get('fecha_transaccion', 'N/A')}")
        print(f"   Estado: {datos_adicionales.get('estado_transaccion', 'N/A')}")
        
        print("\nINFORMACIÓN DEL CLIENTE:")
        datos_adicionales = datos.get('datos_adicionales', {})
        print(f"   Cliente ID: {datos_adicionales.get('cliente_id', 'N/A')}")
        print(f"   Tipo operación: {datos_adicionales.get('tipo_operacion', 'N/A')}")
        
        print("\nINFORMACIÓN TÉCNICA:")
        print(f"   ID Transacción: {datos.get('transaccion_id', 'N/A')}")
        print(f"   IP Cliente: {request.remote_addr}")
        print(f"   Timestamp: {datetime.now().isoformat()}")
        
        # Headers de la request para debugging
        print("\nHEADERS HTTP RELEVANTES:")
        headers_importantes = ['User-Agent', 'Referer', 'Origin', 'Content-Type']
        for header in headers_importantes:
            if header in request.headers:
                print(f"   {header}: {request.headers[header]}")
        
        print("=" * 80)
        
        # Validaciones básicas
        if not datos.get("transaccion_id"):
            print("VALIDACIÓN FALLIDA: transaccion_id es requerido")
            return jsonResponse({"error": "transaccion_id es requerido"}, 400)
        
        if not datos.get("monto") or float(datos.get("monto", 0)) <= 0:
            print("VALIDACIÓN FALLIDA: monto debe ser mayor a 0")
            return jsonResponse({"error": "monto debe ser mayor a 0"}, 400)
        
        print("VALIDACIONES BÁSICAS PASADAS")
        
        # Simular tiempo de procesamiento bancario
        tiempo_procesamiento = random.uniform(
            CONFIG["tiempo_procesamiento_min"],
            CONFIG["tiempo_procesamiento_max"]
        )
        print(f"Simulando procesamiento bancario por {tiempo_procesamiento:.2f} segundos...")
        time.sleep(tiempo_procesamiento)
        
        # Procesar la transacción
        resultado = determinar_resultado_transaccion(datos)
        
        # Log del resultado
        print("\nRESULTADO DE LA TRANSACCIÓN:")
        print(f"   Estado: {'ÉXITO' if resultado['exito'] else 'FALLO'}")
        if not resultado['exito']:
            print(f"   Código de error: {resultado.get('codigo_error')}")
            print(f"   Mensaje: {resultado.get('mensaje_error')}")
        
        print("=" * 80)
        print()
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"   ERROR CRÍTICO procesando transacción: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        print(f"   Detalles: {str(e)}")
        return jsonResponse({
            "error": "Error interno del banco",
            "detalle": str(e)
        }, 500)


@app.route("/api/procesar-transferencia", methods=["POST"])
def procesar_transferencia():
    """
    Procesa una transferencia al medio de cobro del cliente (para ventas).
    
    Expected JSON:
    {
        "transaccion_id": "string",
        "monto": float,
        "divisa": "string",
        "medio_cobro": "string",
        "identificador_cobro": "string",
        "cliente_nombre": "string",
        "datos_adicionales": {}
    }
    
    Returns:
    {
        "exito": bool,
        "codigo_transferencia": "string",
        "mensaje": "string",
        "transaccion_id": "string",
        "tiempo_procesamiento": float
    }
    """
    try:
        datos = request.get_json()
        
        print("=" * 80)
        print(f"[{datetime.now()}] NUEVA TRANSFERENCIA RECIBIDA")
        print("=" * 80)
        
        if not datos:
            print("ERROR: No se enviaron datos en el request")
            return jsonResponse({"error": "No se enviaron datos"}, 400)
        
        # Log completo de todos los datos recibidos
        print("DATOS COMPLETOS DE TRANSFERENCIA:")
        for key, value in datos.items():
            print(f"   {key}: {value} (tipo: {type(value).__name__})")
        
        transaccion_id = datos.get("transaccion_id")
        monto = datos.get("monto")
        divisa = datos.get("divisa", "PYG")
        medio_cobro = datos.get("medio_cobro", "efectivo")
        identificador_cobro = datos.get("identificador_cobro", "")
        cliente_nombre = datos.get("cliente_nombre", "Cliente")
        
        print("\nINFORMACIÓN DE TRANSFERENCIA:")
        print(f"   Monto a transferir: {monto} {divisa}")
        print(f"   Cliente: {cliente_nombre}")
        print(f"   Medio de cobro: {medio_cobro}")
        print(f"   Identificador: {identificador_cobro}")
        
        # Validaciones básicas
        if not transaccion_id:
            print("VALIDACIÓN FALLIDA: transaccion_id es requerido")
            return jsonResponse({"error": "transaccion_id es requerido"}, 400)
        
        if not monto or float(monto) <= 0:
            print("VALIDACIÓN FALLIDA: monto debe ser mayor a 0")
            return jsonResponse({"error": "monto debe ser mayor a 0"}, 400)
        
        print("VALIDACIONES DE TRANSFERENCIA PASADAS")
        
        # Simular tiempo de procesamiento 
        tiempo_procesamiento = random.uniform(1.0, 3.0)
        print(f"Simulando transferencia por {tiempo_procesamiento:.2f} segundos...")
        time.sleep(tiempo_procesamiento)
        
        # Generar código de transferencia único
        codigo_transferencia = f"{random.randint(100000, 999999)}"
        print(f"   Código de transferencia generado: {codigo_transferencia}")
        resultado = {
            "exito": True,
            "codigo_transferencia": codigo_transferencia,
            "mensaje": f"Transferencia exitosa a {medio_cobro} por {monto} {divisa}",
            "transaccion_id": transaccion_id,
            "tiempo_procesamiento": round(tiempo_procesamiento, 2)
        }
        
        print("\nRESULTADO DE LA TRANSFERENCIA:")
        print("   Estado: ÉXITO")
        print(f"   Código transferencia: {codigo_transferencia}")
        print(f"   Tiempo procesamiento: {tiempo_procesamiento:.2f}s")
        
        print("=" * 80)
        print()
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"   ERROR CRÍTICO procesando transferencia: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        print(f"   Detalles: {str(e)}")
        return jsonResponse({
            "error": "Error interno del simulador",
            "detalle": str(e)
        }, 500)


@app.route("/api/configuracion", methods=["GET"])
def obtener_configuracion():
    """Obtiene la configuración actual del simulador."""
    return jsonify(CONFIG)


@app.route("/api/configuracion", methods=["POST"])
def actualizar_configuracion():
    """
    Actualiza la configuración del simulador.
    
    Expected JSON:
    {
        "probabilidad_exito": float (0.0 - 1.0),
        "tiempo_procesamiento_min": int,
        "tiempo_procesamiento_max": int
    }
    """
    try:
        nuevos_datos = request.get_json()
        
        if "probabilidad_exito" in nuevos_datos:
            prob = float(nuevos_datos["probabilidad_exito"])
            if 0.0 <= prob <= 1.0:
                CONFIG["probabilidad_exito"] = prob
        
        if "tiempo_procesamiento_min" in nuevos_datos:
            CONFIG["tiempo_procesamiento_min"] = int(nuevos_datos["tiempo_procesamiento_min"])
        
        if "tiempo_procesamiento_max" in nuevos_datos:
            CONFIG["tiempo_procesamiento_max"] = int(nuevos_datos["tiempo_procesamiento_max"])
        
        return jsonify({
            "mensaje": "Configuración actualizada",
            "configuracion": CONFIG
        })
        
    except Exception as e:
        return jsonResponse({"error": f"Error actualizando configuración: {e}"}, 400)


@app.route("/api/cuentas-prueba", methods=["GET"])
def obtener_cuentas_prueba():
    """Devuelve las cuentas de prueba para QA."""
    return jsonify({
        "cuentas_exitosas": CUENTAS_EXITOSAS,
        "cuentas_que_fallan": CUENTAS_QUE_FALLAN,
        "descripcion": {
            "cuentas_exitosas": "Números de cuenta/tarjeta que siempre tienen éxito",
            "cuentas_que_fallan": "Números de cuenta/tarjeta que siempre fallan"
        }
    })


def jsonResponse(data, status_code=200):
    """Helper para crear respuestas JSON con el status code correcto."""
    response = jsonify(data)
    response.status_code = status_code
    return response


if __name__ == "__main__":
    print("=" * 60)
    print(" API EXTERNO SIMULADOR - INICIANDO")
    print(" Servicio Bancario Simulado")
    print("=" * 60)
    print(f"Host: {CONFIG['host']}")
    print(f"Puerto: {CONFIG['puerto']}")
    print(f"Probabilidad de éxito: {CONFIG['probabilidad_exito']*100}%")
    print(f"Tiempo de procesamiento: {CONFIG['tiempo_procesamiento_min']}-{CONFIG['tiempo_procesamiento_max']}s")
    print("\nEndpoints disponibles:")
    print("  GET  /health")
    print("  POST /api/procesar-transaccion")
    print("  POST /api/procesar-transferencia")
    print("  GET  /api/configuracion")
    print("  POST /api/configuracion")
    print("  GET  /api/cuentas-prueba")
    print("\nCuentas de prueba para QA:")
    print("  Siempre exitosas:", CUENTAS_EXITOSAS)
    print("  Siempre fallan:", CUENTAS_QUE_FALLAN)
    print("=" * 60)
    
    app.run(
        host=CONFIG["host"],
        port=CONFIG["puerto"],
        debug=os.getenv("FLASK_ENV") == "development"
    )