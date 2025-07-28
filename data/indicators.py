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
    
    :param highs: liste des prix hauts (du plus ancien au plus récent)
    :param lows: liste des prix bas (du plus ancien au plus récent)
    :param closes: liste des prix de clôture (du plus ancien au plus récent)
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
    
    # Vérifier qu'on a assez de données (au moins 28 + 1 = 29 bougies)
    if len(closes) < 29:
        logger.warning(f"Pas assez de données pour calculer les VI. Nécessaire: 29, Disponible: {len(closes)}")
        return {'VI1': None, 'VI2': None, 'VI3': None}
    
    # Calculer les True Ranges (à partir de la 2ème bougie)
    true_ranges = []
    for i in range(1, len(highs)):
        high_low = highs[i] - lows[i]
        high_close_prev = abs(highs[i] - closes[i-1])
        low_close_prev = abs(lows[i] - closes[i-1])
        true_range = max(high_low, high_close_prev, low_close_prev)
        true_ranges.append(true_range)
    
    # Vérifier qu'on a assez de True Ranges
    if len(true_ranges) < 28:
        logger.warning(f"Pas assez de True Ranges pour calculer l'ATR. Nécessaire: 28, Disponible: {len(true_ranges)}")
        return {'VI1': None, 'VI2': None, 'VI3': None}
    
    # Calculer l'ATR (RMA des True Ranges sur 28 périodes)
    atr_rma = rma(true_ranges, 28)
    if atr_rma is None:
        logger.warning("Impossible de calculer l'ATR RMA")
        return {'VI1': None, 'VI2': None, 'VI3': None}
    
    # Prendre les dernières valeurs (les plus récentes)
    atr = atr_rma[-1]
    close = closes[-1]  # Dernier close
    
    # Calculer les Volatility Indexes
    # VI = ATR × multiplicateur
    vi1_value = atr * 19
    vi2_value = atr * 10
    vi3_value = atr * 6
    
    # Calculer les bandes
    vi1_upper = close + vi1_value
    vi1_lower = close - vi1_value
    vi2_upper = close + vi2_value
    vi2_lower = close - vi2_value
    vi3_upper = close + vi3_value
    vi3_lower = close - vi3_value
    
    # Pour l'instant, on retourne les bandes inférieures (on ajustera plus tard selon la logique)
    vi1 = vi1_lower
    vi2 = vi2_lower
    vi3 = vi3_lower
    
    result = {
        'VI1': vi1,
        'VI2': vi2,
        'VI3': vi3
    }
    
    logger.debug(f"Volatility Indexes calculés: {result}")
    logger.debug(f"Close: {close}, ATR (RMA TR 28): {atr}")
    logger.debug(f"Données utilisées: {len(closes)} closes, {len(true_ranges)} True Ranges")
    
    return result

def calculate_complete_rma_history(values, period):
    """
    Calcule l'historique complet du RMA pour toutes les valeurs.
    Cette fonction est utilisée au démarrage pour initialiser correctement les indicateurs.
    
    :param values: liste des valeurs (du plus ancien au plus récent)
    :param period: période du RMA
    :return: liste des valeurs RMA calculées
    """
    if len(values) < period:
        return None
    
    # Initialisation : SMA sur les 'period' premières valeurs
    rmas = [sum(values[:period]) / period]
    
    # Lissage Wilder pour toutes les valeurs suivantes
    for v in values[period:]:
        rmas.append((rmas[-1] * (period - 1) + v) / period)
    
    return rmas

def calculate_complete_volatility_indexes_history(highs, lows, closes):
    """
    Calcule l'historique complet des Volatility Indexes.
    Cette fonction est utilisée au démarrage pour initialiser correctement les indicateurs.
    
    :param highs: liste des prix hauts (du plus ancien au plus récent)
    :param lows: liste des prix bas (du plus ancien au plus récent)
    :param closes: liste des prix de clôture (du plus ancien au plus récent)
    :return: dict avec l'historique complet des VI
    """
    logger = logging.getLogger(__name__)
    
    # Convertir en listes si ce sont des Series
    if isinstance(highs, pd.Series):
        highs = highs.tolist()
    if isinstance(lows, pd.Series):
        lows = lows.tolist()
    if isinstance(closes, pd.Series):
        closes = closes.tolist()
    
    # Vérifier qu'on a assez de données (au moins 28 + 1 = 29 bougies)
    if len(closes) < 29:
        logger.warning(f"Pas assez de données pour calculer l'historique des VI. Nécessaire: 29, Disponible: {len(closes)}")
        return None
    
    # Calculer les True Ranges (à partir de la 2ème bougie)
    true_ranges = []
    for i in range(1, len(highs)):
        high_low = highs[i] - lows[i]
        high_close_prev = abs(highs[i] - closes[i-1])
        low_close_prev = abs(lows[i] - closes[i-1])
        true_range = max(high_low, high_close_prev, low_close_prev)
        true_ranges.append(true_range)
    
    # Vérifier qu'on a assez de True Ranges
    if len(true_ranges) < 28:
        logger.warning(f"Pas assez de True Ranges pour calculer l'historique ATR. Nécessaire: 28, Disponible: {len(true_ranges)}")
        return None
    
    # Calculer l'historique complet de l'ATR (RMA des True Ranges sur 28 périodes)
    atr_rma_history = calculate_complete_rma_history(true_ranges, 28)
    if atr_rma_history is None:
        logger.warning("Impossible de calculer l'historique de l'ATR RMA")
        return None
    
    # Calculer l'historique complet des Volatility Indexes
    # VI = ATR × multiplicateur
    # Puis on calcule les bandes : upper = close + VI, lower = close - VI
    vi1_history = []
    vi2_history = []
    vi3_history = []
    
    # On commence à partir de l'index 27 (28ème bougie) car on a besoin de 28 périodes pour le RMA
    # L'ATR a 959 valeurs (True Range commence à la 2ème bougie)
    # Les closes ont 960 valeurs
    # Donc on aligne : close[i] correspond à atr[i-1]
    for i in range(27, len(closes)):
        close = closes[i]
        atr = atr_rma_history[i - 1]  # ATR correspondant à la même période
        
        # Calculer le VI
        vi1_value = atr * 19
        vi2_value = atr * 10
        vi3_value = atr * 6
        
        # Calculer les bandes
        vi1_upper = close + vi1_value
        vi1_lower = close - vi1_value
        vi2_upper = close + vi2_value
        vi2_lower = close - vi2_value
        vi3_upper = close + vi3_value
        vi3_lower = close - vi3_value
        
        # Pour l'instant, on stocke les bandes inférieures (on ajustera plus tard selon la logique)
        vi1_history.append(vi1_lower)
        vi2_history.append(vi2_lower)
        vi3_history.append(vi3_lower)
    
    result = {
        'VI1_history': vi1_history,
        'VI2_history': vi2_history,
        'VI3_history': vi3_history,
        'atr_history': atr_rma_history,
        'true_ranges': true_ranges
    }
    
    logger.info(f"Historique complet des VI calculé: {len(vi1_history)} valeurs")
    logger.debug(f"Première valeur VI1: {vi1_history[0] if vi1_history else 'N/A'}")
    logger.debug(f"Dernière valeur VI1: {vi1_history[-1] if vi1_history else 'N/A'}")
    
    # Debug: Afficher les dernières valeurs pour vérification
    if vi1_history:
        print(f"🔧 DEBUG VI CALCUL - Dernière bougie:")
        print(f"   Close: {closes[-1]:.2f}")
        print(f"   ATR: {atr_rma_history[-1]:.2f}")
        print(f"   VI1: {vi1_history[-1]:.2f}")
        print(f"   VI2: {vi2_history[-1]:.2f}")
        print(f"   VI3: {vi3_history[-1]:.2f}")
    
    return result

def calculate_complete_rsi_history(closes, period=40):
    """
    Calcule l'historique complet du RSI avec la méthode Wilder Smoothing.
    Cette fonction est utilisée au démarrage pour initialiser correctement les indicateurs.
    
    :param closes: liste des prix de clôture (du plus ancien au plus récent)
    :param period: période du RSI (défaut: 40)
    :return: liste des valeurs RSI calculées
    """
    if len(closes) < period + 1:
        return None
    
    # Calculer les deltas
    deltas = []
    for i in range(1, len(closes)):
        deltas.append(closes[i] - closes[i-1])
    
    # Séparer gains et pertes
    gains = [max(delta, 0) for delta in deltas]
    losses = [max(-delta, 0) for delta in deltas]
    
    # Première moyenne (initialisation) - SMA sur les 'period' premières périodes
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Calculer le premier RSI
    if avg_loss == 0:
        first_rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        first_rsi = 100 - (100 / (1 + rs))
    
    rsi_history = [first_rsi]
    
    # Lissage récursif de Wilder pour les périodes suivantes
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        rsi_history.append(rsi)
    
    return rsi_history

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
    # Pour les VI, on a besoin d'au moins vi_period + 1 bougies (28 + 1 = 29)
    # Pour le RSI, on a besoin d'au moins rsi_period + 1 bougies (40 + 1 = 41)
    # On prend le maximum des deux
    total_needed = max(rsi_period + 1, vi_period + 1)
    
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