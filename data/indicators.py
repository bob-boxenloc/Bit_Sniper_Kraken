import pandas as pd
import logging
import numpy as np

def calculate_rsi_wilder(closes: list, length: int = 40) -> float:
    """
    Calcule le RSI selon la méthode Wilder Smoothing (comme TradingView par défaut).
    
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

def rma(values, period):
    """
    Calcule la moyenne mobile de Wilder (RMA - Rolling Moving Average).
    
    Args:
        values: Liste de valeurs
        period: Période pour la moyenne
    
    Returns:
        Liste des valeurs RMA
    """
    if len(values) < period:
        return None
    
    # Initialisation : SMA sur les 'period' premières valeurs
    rmas = [sum(values[:period]) / period]
    
    # Lissage Wilder pour les valeurs suivantes
    for v in values[period:]:
        rmas.append((rmas[-1] * (period - 1) + v) / period)
    
    return rmas

def calculate_volatility_indexes(highs, lows, closes):
    """
    Calcule les 3 Volatility Indexes selon la vraie formule TradingView.
    
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
    
    # Calculer les True Ranges
    true_ranges = []
    for i in range(1, len(highs)):
        high_low = highs[i] - lows[i]
        high_close_prev = abs(highs[i] - closes[i-1])
        low_close_prev = abs(lows[i] - closes[i-1])
        true_range = max(high_low, high_close_prev, low_close_prev)
        true_ranges.append(true_range)
    
    # Calculer la ligne centrale (RMA des clôtures sur 28 périodes)
    basis_rma = rma(closes, 28)
    if basis_rma is None:
        return {'VI1': None, 'VI2': None, 'VI3': None}
    
    # Calculer l'ATR (RMA des True Ranges sur 28 périodes)
    atr_rma = rma(true_ranges, 28)
    if atr_rma is None:
        return {'VI1': None, 'VI2': None, 'VI3': None}
    
    # Prendre les dernières valeurs
    basis = basis_rma[-1]
    atr = atr_rma[-1]
    
    # Calculer les 3 Volatility Indexes
    vi1 = basis + (atr * 19)
    vi2 = basis + (atr * 10)
    vi3 = basis + (atr * 6)
    
    result = {
        'VI1': vi1,
        'VI2': vi2,
        'VI3': vi3
    }
    
    logger.debug(f"Volatility Indexes calculés: {result}")
    logger.debug(f"Basis (RMA close 28): {basis}, ATR (RMA TR 28): {atr}")
    
    return result

def compute_rsi_40(closes, period=40):
    """
    Calcule le RSI(40) avec la méthode Wilder Smoothing.
    :param closes: liste des prix de clôture
    :param period: période du RSI (défaut: 40)
    :return: RSI Wilder pour la dernière période
    """
    return calculate_rsi_wilder(closes, period)

def has_sufficient_history_for_indicators(candles, rsi_period=40, vi_period=28):
    """
    Vérifie qu'on a assez d'historique pour calculer les indicateurs de manière fiable.
    :param candles: liste des bougies
    :param rsi_period: période du RSI (par défaut 40)
    :param vi_period: période pour les VI (par défaut 28)
    :return: (bool, str) - (suffisant, message d'erreur)
    """
    # Total nécessaire : max(rsi_period, vi_period) + 1 pour avoir une valeur valide
    total_needed = max(rsi_period, vi_period) + 1
    
    if len(candles) < total_needed:
        return False, f"Pas assez d'historique. Nécessaire: {total_needed}, Disponible: {len(candles)}"
    
    # Vérifier que les indicateurs sont calculables
    closes = [float(c['close']) for c in candles]
    highs = [float(c['high']) for c in candles]
    lows = [float(c['low']) for c in candles]
    
    rsi = compute_rsi_40(closes, rsi_period)
    volatility_indexes = calculate_volatility_indexes(highs, lows, closes)
    
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
    
    # RSI actuel (dernière bougie)
    rsi = compute_rsi_40(closes, rsi_period)
    
    # Volatility Indexes actuels
    volatility_indexes = calculate_volatility_indexes(highs, lows, closes)
    
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
    vi = calculate_volatility_indexes(highs, lows, closes)
    print("\nVolatility Indexes :")
    for name, value in vi.items():
        print(f"{name}: {value}")
    
    # Test de validation
    candles = [{'close': c, 'high': h, 'low': l} for c, h, l in zip(closes, highs, lows)]
    is_valid, message = has_sufficient_history_for_indicators(candles, 40)
    print(f"\nValidation: {is_valid} - {message}") 