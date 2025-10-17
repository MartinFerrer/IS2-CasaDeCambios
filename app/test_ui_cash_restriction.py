#!/usr/bin/env python3
"""Test script para verificar que la restricción de efectivo funciona en la UI.
Este script prueba que el endpoint api_medios_pago_cliente no devuelve efectivo
para operaciones de compra.
"""

import os
import sys

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "global_exchange_django.settings")
sys.path.append("/home/iant/GlobalExchange/IS2-CasaDeCambios/app")

django.setup()

from apps.usuarios.models import Cliente
from django.contrib.auth import get_user_model
from django.test import Client


def test_cash_restriction_in_api():
    """Test que verifica que efectivo no esté disponible para compra"""
    # Crear cliente de prueba
    User = get_user_model()
    user = User.objects.create_user(username="test_user", password="test_pass")
    cliente = Cliente.objects.create(nombre="Test Cliente", ruc="12345678-9")
    cliente.usuarios.add(user)

    client = Client()
    client.login(username="test_user", password="test_pass")

    # Test para operación de compra
    response = client.get(f"/transacciones/api/medios-pago-cliente/{cliente.id}/?tipo=compra")
    data = response.json()

    print("=== Test: Operación de COMPRA ===")
    print(f"Status Code: {response.status_code}")
    print(f"Medios de pago disponibles: {len(data.get('medios_pago', []))}")

    # Verificar que no hay efectivo en los medios de pago
    medios_pago_ids = [medio["id"] for medio in data.get("medios_pago", [])]
    print(f"IDs de medios de pago: {medios_pago_ids}")

    if "efectivo" in medios_pago_ids:
        print("❌ ERROR: Efectivo está disponible para compra (no debería estar)")
        return False
    else:
        print("✅ CORRECTO: Efectivo NO está disponible para compra")

    # Test para operación de venta
    response_venta = client.get(f"/transacciones/api/medios-pago-cliente/{cliente.id}/?tipo=venta")
    data_venta = response_venta.json()

    print("\n=== Test: Operación de VENTA ===")
    print(f"Status Code: {response_venta.status_code}")
    print(f"Medios de pago disponibles: {len(data_venta.get('medios_pago', []))}")

    medios_pago_venta_ids = [medio["id"] for medio in data_venta.get("medios_pago", [])]
    print(f"IDs de medios de pago: {medios_pago_venta_ids}")

    if "efectivo" in medios_pago_venta_ids:
        print("✅ CORRECTO: Efectivo SÍ está disponible para venta")
        return True
    else:
        print("❌ ERROR: Efectivo NO está disponible para venta (debería estar)")
        return False


if __name__ == "__main__":
    try:
        success = test_cash_restriction_in_api()
        if success:
            print("\n🎉 Todos los tests pasaron correctamente!")
        else:
            print("\n❌ Algunos tests fallaron")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error durante la ejecución del test: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
