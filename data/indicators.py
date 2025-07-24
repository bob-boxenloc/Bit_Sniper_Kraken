import pandas as pd
import logging
import numpy as np

def calculate_rsi_wilder(closes: list, length: int = 40) -> float:
    """
    Calcule le RSI selon la méthode Wilder (lissage exponentiel discret).
    
    Args:
        closes: Liste des prix de clôture (du plus ancien au plus récent)
        length: Période du RSI (défaut: 40 pour la nouvelle stratégie)
    
    Returns:
        RSI Wilder pour la dernière période
    """
    if len(closes) < length + 1:
        return None
    
    # Calculer les deltas
    deltas = []
    for i in range(1, len(closes)):
        deltas.append(closes[i] - closes[i-1])
    
    # Séparer gains et pertes
    gains = [max(delta, 0) for delta in deltas]
    losses = [max(-delta, 0) for delta in deltas]
    
    # Première moyenne (initialisation) - SMA sur les 'length' premières périodes
    avg_gain = sum(gains[:length]) / length
    avg_loss = sum(losses[:length]) / length
    
    # Lissage récursif de Wilder pour les périodes suivantes
    for i in range(length, len(deltas)):
        avg_gain = (avg_gain * (length - 1) + gains[i]) / length
        avg_loss = (avg_loss * (length - 1) + losses[i]) / length
    
    # Calcul du RSI
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_atr(highs: list, lows: list, closes: list, period: int = 28) -> float:
    """
    Calcule l'Average True Range (ATR) selon la méthode Wilder.
    
    Args:
        highs: Liste des prix hauts
        lows: Liste des prix bas
        closes: Liste des prix de clôture
        period: Période de l'ATR (défaut: 28)
    
    Returns:
        ATR Wilder pour la dernière période
    """
    if len(highs) < period + 1:
        return None
    
    # Calculer les True Ranges
    true_ranges = []
    for i in range(1, len(highs)):
        high_low = highs[i] - lows[i]
        high_close_prev = abs(highs[i] - closes[i-1])
        low_close_prev = abs(lows[i] - closes[i-1])
        true_range = max(high_low, high_close_prev, low_close_prev)
        true_ranges.append(true_range)
    
    # Première moyenne (initialisation)
    atr = sum(true_ranges[:period]) / period
    
    # Lissage récursif de Wilder pour les périodes suivantes
    for i in range(period, len(true_ranges)):
        atr = (atr * (period - 1) + true_ranges[i]) / period
    
    return atr

def calculate_volatility_index(highs: list, lows: list, closes: list, 
                              atr_period: int = 28, atr_multiplier: int = 19) -> float:
    """
    Calcule un Volatility Index selon la méthode Wilder.
    
    Args:
        highs: Liste des prix hauts
        lows: Liste des prix bas
        closes: Liste des prix de clôture
        atr_period: Période de l'ATR (défaut: 28)
        atr_multiplier: Multiplicateur ATR (défaut: 19 pour VI1)
    
    Returns:
        Volatility Index pour la dernière période
    """
    if len(closes) < atr_period + 1:
        return None
    
    # Calculer l'ATR
    atr = calculate_atr(highs, lows, closes, atr_period)
    if atr is None:
        return None
    
    # Calculer le Volatility Index
    current_close = closes[-1]
    volatility_index = current_close + (atr * atr_multiplier)
    
    return volatility_index

def compute_rsi_40(closes, period=40):
    """
    Calcule le RSI(40) selon la méthode Wilder.
    
    :param closes: liste ou Series de prix de clôture
    :param period: période du RSI (par défaut 40)
    :return: RSI Wilder pour la dernière période
    """
    logger = logging.getLogger(__name__)
    
    # Convertir en liste si c'est une Series
    if isinstance(closes, pd.Series):
        closes = closes.tolist()
    
    # Log des données d'entrée pour debug
    logger.debug(f"Calcul RSI Wilder({period}) - {len(closes)} prix de clôture")
    
    # Utiliser la méthode Wilder
    rsi_wilder = calculate_rsi_wilder(closes, period)
    
    if rsi_wilder is None:
        logger.warning(f"Impossible de calculer RSI Wilder - données insuffisantes")
        return None
    
    logger.debug(f"RSI Wilder({period}): {rsi_wilder}")
    
    return rsi_wilder

def compute_volatility_indexes(highs, lows, closes):
    """
    Calcule les 3 Volatility Indexes selon la nouvelle stratégie.
    
    :param highs: liste des prix hauts
    :param lows: liste des prix bas
    :param closes: liste des prix de clôture
    :return: dict avec les 3 VI (VI1, VI2, VI3)
    """
    logger = logging.getLogger(__name__)
    
    # Convertir en listes si ce sont des Series
    if isinstance(highs, pd.Series):
        highs = highs.tolist()
    if isinstance(lows, pd.Series):
        lows = lows.tolist()
    if isinstance(closes, pd.Series):
        closes = closes.tolist()
    
    # Calculer les 3 Volatility Indexes
    vi1 = calculate_volatility_index(highs, lows, closes, atr_period=28, atr_multiplier=19)
    vi2 = calculate_volatility_index(highs, lows, closes, atr_period=28, atr_multiplier=10)
    vi3 = calculate_volatility_index(highs, lows, closes, atr_period=28, atr_multiplier=6)
    
    result = {
        'VI1': vi1,
        'VI2': vi2,
        'VI3': vi3
    }
    
    logger.debug(f"Volatility Indexes calculés: {result}")
    
    return result

def has_sufficient_history_for_indicators(candles, rsi_period=40, atr_period=28):
    """
    Vérifie qu'on a assez d'historique pour calculer les indicateurs de manière fiable.
    :param candles: liste des bougies
    :param rsi_period: période du RSI (par défaut 40)
    :param atr_period: période de l'ATR (par défaut 28)
    :return: (bool, str) - (suffisant, message d'erreur)
    """
    # Total nécessaire : max(rsi_period, atr_period) + 1 pour avoir une valeur valide
    total_needed = max(rsi_period, atr_period) + 1
    
    if len(candles) < total_needed:
        return False, f"Pas assez d'historique. Nécessaire: {total_needed}, Disponible: {len(candles)}"
    
    # Vérifier que les indicateurs sont calculables
    closes = [float(c['close']) for c in candles]
    highs = [float(c['high']) for c in candles]
    lows = [float(c['low']) for c in candles]
    
    rsi = compute_rsi_40(closes, rsi_period)
    volatility_indexes = compute_volatility_indexes(highs, lows, closes)
    
    # Vérifier que tous les indicateurs sont calculables
    if rsi is None or any(v is None for v in volatility_indexes.values()):
        return False, f"Indicateurs pas encore calculables avec {len(closes)} bougies"
    
    return True, f"Historique suffisant pour le trading (RSI({rsi_period}), VI)"

def get_indicators_with_validation(candles, rsi_period=40):
    """
    Calcule tous les indicateurs avec validation de l'historique.
    :param candles: liste des bougies
    :param rsi_period: période du RSI (par défaut 40)
    :return: (bool, dict, message) - (succès, indicateurs, message)
    """
    # Vérifier si on a assez de données
    is_valid, message = has_sufficient_history_for_indicators(candles, rsi_period)
    if not is_valid:
        return False, None, message
    
    # Calculer les indicateurs
    closes = [float(c['close']) for c in candles]
    highs = [float(c['high']) for c in candles]
    lows = [float(c['low']) for c in candles]
    
    rsi = compute_rsi_40(closes, rsi_period)
    volatility_indexes = compute_volatility_indexes(highs, lows, closes)
    
    indicators = {
        'RSI': rsi,
        **volatility_indexes
    }
    
    return True, indicators, f"Indicateurs calculés avec succès"

# Test du module
if __name__ == "__main__":
    # Données fictives pour test
    closes = [100, 102, 101, 105, 107, 110, 108, 109, 111, 115, 117, 120, 119, 121, 123, 125]
    highs = [c + 2 for c in closes]
    lows = [c - 2 for c in closes]
    
    # Test RSI
    rsi = compute_rsi_40(closes, period=40)
    print("RSI(40) Wilder :")
    print(rsi)
    
    # Test Volatility Indexes
    vi = compute_volatility_indexes(highs, lows, closes)
    print("\nVolatility Indexes :")
    for name, value in vi.items():
        print(f"{name}: {value}")
    
    # Test de validation
    candles = [{'close': c, 'high': h, 'low': l} for c, h, l in zip(closes, highs, lows)]
    is_valid, message = has_sufficient_history_for_indicators(candles, 40)
    print(f"\nValidation: {is_valid} - {message}") 