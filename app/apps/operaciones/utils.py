"""Utilidades para la gestión de operaciones de divisas.

Este módulo proporciona funciones auxiliares para trabajar con divisas,
como: obtención de banderas basadas en códigos de moneda.
"""

import pycountry


def get_flag_url_from_currency(currency_code):
    """Obtiene la URL de la imagen de la bandera (PNG) para un código de divisa ISO 4217.

    Args:
        currency_code (str): El código de divisa de 3 letras (ej. 'USD', 'EUR').

    Retorna:
        str: La URL de la imagen de la bandera, o una URL a una bandera genérica si no se encuentra.

    """
    # Mapeo manual para divisas
    manual_mapping = {
        "EUR": "eu",  # Bandera de la Unión Europea
        "USD": "us",
        "BRL": "br",
        "ARS": "ar",
        "PYG": "py",
        "AOA": "ao",  # Kwanza Angolano
        "GBP": "gb",
        "ANG": "an",  # Países Bajos del Caribe (ANTIGUA Y BARBUDA)
        "AUD": "au",
    }

    try:
        # 1. Intenta con el mapeo manual primero
        country_code = manual_mapping.get(currency_code.upper())
        if country_code:
            return f"https://flagcdn.com/w160/{country_code}.png"

        # 2. Si no hay mapeo manual, usa pycountry
        currency = pycountry.currencies.get(alpha_3=currency_code)
        if currency.countries:
            country = pycountry.countries.get(alpha_2=currency.countries[0])
            country_code = country.alpha_2.lower()
            return f"https://flagcdn.com/w160/{country_code}.png"
        else:
            return "https://flagcdn.com/w160/un.png"

    except (AttributeError, KeyError):
        return "https://flagcdn.com/w160/un.png"
