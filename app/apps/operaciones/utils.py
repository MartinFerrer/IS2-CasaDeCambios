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
        "AED": "ae",
        "AFN": "af",
        "ALL": "al",
        "AMD": "am",
        "AOA": "ao",
        "ARS": "ar",
        "AUD": "au",
        "AWG": "aw",
        "AZN": "az",
        "BAM": "ba",
        "BBD": "bb",
        "BDT": "bd",
        "BGN": "bg",
        "BHD": "bh",
        "BIF": "bi",
        "BMD": "bm",
        "BND": "bn",
        "BOB": "bo",
        "BRL": "br",
        "BSD": "bs",
        "BTN": "bt",
        "BWP": "bw",
        "BYN": "by",
        "BZD": "bz",
        "CAD": "ca",
        "CDF": "cd",
        "CHF": "ch",
        "CLP": "cl",
        "CNY": "cn",
        "COP": "co",
        "CRC": "cr",
        "CUP": "cu",
        "CVE": "cv",
        "CZK": "cz",
        "DJF": "dj",
        "DKK": "dk",
        "DOP": "do",
        "DZD": "dz",
        "EGP": "eg",
        "ERN": "er",
        "ETB": "et",
        "EUR": "eu",
        "FJD": "fj",
        "FKP": "fk",
        "GBP": "gb",
        "GEL": "ge",
        "GHS": "gh",
        "GIP": "gi",
        "GMD": "gm",
        "GNF": "gn",
        "GTQ": "gt",
        "GYD": "gy",
        "HKD": "hk",
        "HNL": "hn",
        "HRK": "hr",
        "HTG": "ht",
        "HUF": "hu",
        "IDR": "id",
        "ILS": "il",
        "INR": "in",
        "IQD": "iq",
        "IRR": "ir",
        "ISK": "is",
        "JMD": "jm",
        "JOD": "jo",
        "JPY": "jp",
        "KES": "ke",
        "KGS": "kg",
        "KHR": "kh",
        "KMF": "km",
        "KRW": "kr",
        "KWD": "kw",
        "KYD": "ky",
        "KZT": "kz",
        "LAK": "la",
        "LBP": "lb",
        "LKR": "lk",
        "LRD": "lr",
        "LSL": "ls",
        "LYD": "ly",
        "MAD": "ma",
        "MDL": "md",
        "MGA": "mg",
        "MKD": "mk",
        "MMK": "mm",
        "MNT": "mn",
        "MOP": "mo",
        "MRU": "mr",
        "MUR": "mu",
        "MVR": "mv",
        "MWK": "mw",
        "MXN": "mx",
        "MYR": "my",
        "MZN": "mz",
        "NAD": "na",
        "NGN": "ng",
        "NIO": "ni",
        "NOK": "no",
        "NPR": "np",
        "NZD": "nz",
        "OMR": "om",
        "PAB": "pa",
        "PEN": "pe",
        "PGK": "pg",
        "PHP": "ph",
        "PKR": "pk",
        "PLN": "pl",
        "PYG": "py",
        "QAR": "qa",
        "RON": "ro",
        "RSD": "rs",
        "RUB": "ru",
        "RWF": "rw",
        "SAR": "sa",
        "SBD": "sb",
        "SCR": "sc",
        "SDG": "sd",
        "SEK": "se",
        "SGD": "sg",
        "SHP": "sh",
        "SLE": "sl",
        "SRD": "sr",
        "SSP": "ss",
        "STN": "st",
        "SVC": "sv",
        "SYP": "sy",
        "SZL": "sz",
        "THB": "th",
        "TJS": "tj",
        "TMT": "tm",
        "TND": "tn",
        "TOP": "to",
        "TRY": "tr",
        "TTD": "tt",
        "TWD": "tw",
        "TZS": "tz",
        "UAH": "ua",
        "UGX": "ug",
        "USD": "us",
        "UYU": "uy",
        "UZS": "uz",
        "VES": "ve",
        "VND": "vn",
        "VUV": "vu",
        "WST": "ws",
        "XAF": "cm",
        "XCD": "ag",
        "XOF": "sn",
        "XPF": "pf",
        "YER": "ye",
        "ZAR": "za",
        "ZMW": "zm",
        "ZWL": "zw",
    }

    try:
        # 1. Intenta con el mapeo manual primero
        country_code = manual_mapping.get(currency_code.upper())
        if country_code:
            return f"https://flagcdn.com/w160/{country_code}.png"

        # 2. Si no hay mapeo manual, usa pycountry
        currency = pycountry.currencies.get(alpha_3=currency_code)
        if currency and hasattr(currency, "countries"):
            countries = getattr(currency, "countries", None)
            if countries:
                country = pycountry.countries.get(alpha_2=countries[0])
                country_code = country.alpha_2.lower()
                return f"https://flagcdn.com/w160/{country_code}.png"
        return "https://flagcdn.com/w160/un.png"

    except (AttributeError, KeyError):
        return "https://flagcdn.com/w160/un.png"
