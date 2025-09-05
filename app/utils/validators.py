"""
Utilidades para validación de documentos paraguayos.
"""


def calcular_digito_verificador_ruc(ruc_sin_dv: str) -> int:
    """
    Calcula el dígito verificador del RUC.
    
    Args:
        ruc_sin_dv: RUC sin el dígito verificador

    Returns:
        int: Dígito verificador calculado (0-9)
    """
    # Limpiar el RUC (remover espacios, guiones, etc.)
    ruc_limpio = ''.join(c for c in ruc_sin_dv if c.isdigit())
    
    # Algoritmo de cálculo del dígito verificador
    k = 2
    total = 0
    
    # Recorrer los dígitos de derecha a izquierda
    for i in range(len(ruc_limpio) - 1, -1, -1):
        if k > 11:  # base máxima según el algoritmo
            k = 2
        
        digito = int(ruc_limpio[i])
        total += digito * k
        k += 1
    
    resto = total % 11
    dv = 0 if resto <= 1 else 11 - resto
    
    return dv

def validar_ruc_completo(ruc_completo: str) -> bool:
    """
    Valida un RUC completo.
    
    Args:
        ruc_completo: RUC completo en formato XXXXXXXX-X
        
    Returns:
        bool: True si el RUC es válido, False en caso contrario
    """
    try:
        # Limpiar el RUC
        ruc_limpio = limpiar_ruc(ruc_completo)
        
        # Separar RUC base y dígito verificador
        ruc_base = ruc_limpio[:-1]
        dv_proporcionado = int(ruc_limpio[-1])
        
        # Calcular el dígito verificador correcto
        dv_calculado = calcular_digito_verificador_ruc(ruc_base)
        
        return dv_proporcionado == dv_calculado
        
    except (ValueError, IndexError):
        return False

def limpiar_ruc(ruc: str) -> str:
    """
    Limpia un RUC removiendo caracteres no numéricos.

    Args:
        ruc: RUC en formato XXXXXXXX-X

    Returns:
        str: RUC solo con dígitos
    """
    return ''.join(c for c in ruc if c.isdigit())
