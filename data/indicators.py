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
    Calcule les Volatility Indexes en temps réel avec la méthode Wilder Smoothing.
    Cette fonction est utilisée pour les calculs en temps réel.
    
    :param highs: liste des prix hauts (du plus ancien au plus récent)
    :param lows: liste des prix bas (du plus ancien au plus récent)
    :param closes: liste des prix de clôture (du plus ancien au plus récent)
    :return: dictionnaire avec les VI calculés
    """
    logger = logging.getLogger(__name__)
    
    if len(closes) < 28:
        logger.warning(f"Pas assez de données pour calculer les VI. Nécessaire: 28, Disponible: {len(closes)}")
        return {'VI1': None, 'VI2': None, 'VI3': None}
    
    # Calculer les True Ranges
    true_ranges = []
    for i in range(1, len(closes)):
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
    
    # Calculer la ligne centrale (RMA des closes sur 28 périodes)
    center_line_rma = rma(closes, 28)
    if center_line_rma is None:
        logger.warning("Impossible de calculer la ligne centrale RMA")
        return {'VI1': None, 'VI2': None, 'VI3': None}
    
    # Prendre les dernières valeurs (les plus récentes)
    atr = atr_rma[-1]
    center_line = center_line_rma[-1]
    close = closes[-1]  # Dernier close
    
    # Calculer les Volatility Indexes basés sur la ligne centrale
    # VI = ATR × multiplicateur
    vi1_value = atr * 19
    vi2_value = atr * 10
    vi3_value = atr * 6
    
    # Calculer les bandes
    vi1_upper = center_line + vi1_value
    vi1_lower = center_line - vi1_value
    vi2_upper = center_line + vi2_value
    vi2_lower = center_line - vi2_value
    vi3_upper = center_line + vi3_value
    vi3_lower = center_line - vi3_value
    
    # Logique de sélection dynamique des bandes
    # Chaque VI a sa propre logique indépendante basée sur sa propre RMA
    # Si VI > RMA(VI) → utiliser bande supérieure (résistance)
    # Si VI < RMA(VI) → utiliser bande inférieure (support)
    
    # Calculer les RMA de chaque VI individuellement
    # On doit d'abord calculer l'historique complet de chaque VI pour avoir sa RMA
    
    # Calculer l'historique complet des VI (sans sélection de bande) jusqu'à l'index i
    vi1_raw_history = []
    vi2_raw_history = []
    vi3_raw_history = []
    
    # Utiliser les données jusqu'à l'index i pour calculer l'historique
    for j in range(27, len(closes)):
        if j >= len(closes) or (j - 1) >= len(atr_rma) or (j - 27) >= len(center_line_rma):
            break
            
        close_j = closes[j]
        atr_j = atr_rma[j - 1]
        center_line_j = center_line_rma[j - 27]
        
        # Calculer les VI basés sur la ligne centrale
        vi1_value_j = atr_j * 19
        vi2_value_j = atr_j * 10
        vi3_value_j = atr_j * 6
        
        # Calculer les bandes
        vi1_upper_j = center_line_j + vi1_value_j
        vi2_upper_j = center_line_j + vi2_value_j
        vi3_upper_j = center_line_j + vi3_value_j
        
        # Stocker les bandes supérieures comme valeurs "brutes" pour calculer RMA
        vi1_raw_history.append(vi1_upper_j)
        vi2_raw_history.append(vi2_upper_j)
        vi3_raw_history.append(vi3_upper_j)
    
    # Calculer RMA de chaque VI
    if len(vi1_raw_history) >= 28:
        vi1_rma = rma(vi1_raw_history, 28)
        vi2_rma = rma(vi2_raw_history, 28)
        vi3_rma = rma(vi3_raw_history, 28)
        
        if vi1_rma is not None and vi2_rma is not None and vi3_rma is not None:
            # Comparer chaque VI avec sa propre RMA
            current_vi1 = vi1_upper  # Valeur actuelle
            current_vi2 = vi2_upper
            current_vi3 = vi3_upper
            
            if current_vi1 > vi1_rma[-1]:
                vi1 = vi1_upper  # VI1 > RMA(VI1) → résistance
            else:
                vi1 = vi1_lower  # VI1 < RMA(VI1) → support
                
            if current_vi2 > vi2_rma[-1]:
                vi2 = vi2_upper  # VI2 > RMA(VI2) → résistance
            else:
                vi2 = vi2_lower  # VI2 < RMA(VI2) → support
                
            if current_vi3 > vi3_rma[-1]:
                vi3 = vi3_upper  # VI3 > RMA(VI3) → résistance
            else:
                vi3 = vi3_lower  # VI3 < RMA(VI3) → support
        else:
            # Fallback : utiliser la bande supérieure
            vi1 = vi1_upper
            vi2 = vi2_upper
            vi3 = vi3_upper
    else:
        # Fallback : utiliser la bande supérieure
        vi1 = vi1_upper
        vi2 = vi2_upper
        vi3 = vi3_upper
    
    result = {
        'VI1': vi1,
        'VI2': vi2,
        'VI3': vi3,
        'VI1_upper': vi1_upper,
        'VI1_lower': vi1_lower,
        'VI2_upper': vi2_upper,
        'VI2_lower': vi2_lower,
        'VI3_upper': vi3_upper,
        'VI3_lower': vi3_lower,
        'center_line': center_line
    }
    
    logger.debug(f"Volatility Indexes calculés: {result}")
    logger.debug(f"Close: {close}, Ligne centrale: {center_line}, ATR (RMA TR 28): {atr}")
    logger.debug(f"VI1 - Upper: {vi1_upper:.2f}, Lower: {vi1_lower:.2f}, Selected: {vi1:.2f}")
    logger.debug(f"VI2 - Upper: {vi2_upper:.2f}, Lower: {vi2_lower:.2f}, Selected: {vi2:.2f}")
    logger.debug(f"VI3 - Upper: {vi3_upper:.2f}, Lower: {vi3_lower:.2f}, Selected: {vi3:.2f}")
    logger.debug(f"Logique: Close > VI_upper ? VI1:{close > vi1_upper}, VI2:{close > vi2_upper}, VI3:{close > vi3_upper}")
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
    Calcule l'historique complet des Volatility Indexes avec la méthode Wilder Smoothing.
    Cette fonction est utilisée au démarrage pour initialiser correctement les indicateurs.
    
    :param highs: liste des prix hauts (du plus ancien au plus récent)
    :param lows: liste des prix bas (du plus ancien au plus récent)
    :param closes: liste des prix de clôture (du plus ancien au plus récent)
    :return: dictionnaire avec les historiques des VI et données associées
    """
    logger = logging.getLogger(__name__)
    
    if len(closes) < 28:
        logger.warning(f"Pas assez de données pour calculer l'historique des VI. Nécessaire: 28, Disponible: {len(closes)}")
        return None
    
    # Calculer les True Ranges
    true_ranges = []
    for i in range(1, len(closes)):
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
    
    # Calculer l'historique complet de la ligne centrale (RMA des closes sur 28 périodes)
    center_line_history = calculate_complete_rma_history(closes, 28)
    if center_line_history is None:
        logger.warning("Impossible de calculer l'historique de la ligne centrale RMA")
        return None
    
    # Calculer l'historique complet des Volatility Indexes
    # Ligne centrale = RMA(close, 28)
    # VI_upper = ligne_centrale + (ATR × multiplicateur)
    # VI_lower = ligne_centrale - (ATR × multiplicateur)
    vi1_upper_history = []
    vi1_lower_history = []
    vi2_upper_history = []
    vi2_lower_history = []
    vi3_upper_history = []
    vi3_lower_history = []
    
    # Historique des bandes sélectionnées (pour la logique dynamique)
    vi1_selected_history = []
    vi2_selected_history = []
    vi3_selected_history = []
    
    # On commence à partir de l'index 27 (28ème bougie) car on a besoin de 28 périodes pour le RMA
    # L'ATR a 959 valeurs (True Range commence à la 2ème bougie)
    # La ligne centrale a 933 valeurs (RMA commence à la 28ème bougie)
    # Les closes ont 960 valeurs
    # Donc on aligne : close[i] correspond à atr[i-1] et center_line[i-27]
    for i in range(27, len(closes)):
        # Vérifier qu'on ne dépasse pas les indices
        if i >= len(closes) or (i - 1) >= len(atr_rma_history) or (i - 27) >= len(center_line_history):
            break
            
        close = closes[i]
        atr = atr_rma_history[i - 1]  # ATR correspondant à la même période
        center_line = center_line_history[i - 27]  # Ligne centrale correspondante
        
        # Calculer les VI basés sur la ligne centrale
        vi1_value = atr * 19
        vi2_value = atr * 10
        vi3_value = atr * 6
        
        # Calculer les bandes
        vi1_upper = center_line + vi1_value
        vi1_lower = center_line - vi1_value
        vi2_upper = center_line + vi2_value
        vi2_lower = center_line - vi2_value
        vi3_upper = center_line + vi3_value
        vi3_lower = center_line - vi3_value
        
        # Stocker les bandes
        vi1_upper_history.append(vi1_upper)
        vi1_lower_history.append(vi1_lower)
        vi2_upper_history.append(vi2_upper)
        vi2_lower_history.append(vi2_lower)
        vi3_upper_history.append(vi3_upper)
        vi3_lower_history.append(vi3_lower)
        
        # Logique de sélection dynamique des bandes
        # Chaque VI a sa propre logique indépendante basée sur sa propre RMA
        # Si VI > RMA(VI) → utiliser bande supérieure (résistance)
        # Si VI < RMA(VI) → utiliser bande inférieure (support)
        
        # Calculer les RMA de chaque VI individuellement
        # On doit d'abord calculer l'historique complet de chaque VI pour avoir sa RMA
        
        # Calculer l'historique complet des VI (sans sélection de bande) jusqu'à l'index i
        vi1_raw_history = []
        vi2_raw_history = []
        vi3_raw_history = []
        
        # Utiliser les données jusqu'à l'index i pour calculer l'historique
        for j in range(27, i + 1):
            if j >= len(closes) or (j - 1) >= len(atr_rma_history) or (j - 27) >= len(center_line_history):
                break
                
            close_j = closes[j]
            atr_j = atr_rma_history[j - 1]
            center_line_j = center_line_history[j - 27]
            
            # Calculer les VI basés sur la ligne centrale
            vi1_value_j = atr_j * 19
            vi2_value_j = atr_j * 10
            vi3_value_j = atr_j * 6
            
            # Calculer les bandes
            vi1_upper_j = center_line_j + vi1_value_j
            vi2_upper_j = center_line_j + vi2_value_j
            vi3_upper_j = center_line_j + vi3_value_j
            
            # Stocker les bandes supérieures comme valeurs "brutes" pour calculer RMA
            vi1_raw_history.append(vi1_upper_j)
            vi2_raw_history.append(vi2_upper_j)
            vi3_raw_history.append(vi3_upper_j)
        
        # Calculer RMA de chaque VI
        if len(vi1_raw_history) >= 28:
            vi1_rma = rma(vi1_raw_history, 28)
            vi2_rma = rma(vi2_raw_history, 28)
            vi3_rma = rma(vi3_raw_history, 28)
            
            if vi1_rma is not None and vi2_rma is not None and vi3_rma is not None:
                # Comparer chaque VI avec sa propre RMA
                current_vi1 = vi1_upper  # Valeur actuelle
                current_vi2 = vi2_upper
                current_vi3 = vi3_upper
                
                if current_vi1 > vi1_rma[-1]:
                    vi1_selected_history.append(vi1_upper)  # VI1 > RMA(VI1) → résistance
                else:
                    vi1_selected_history.append(vi1_lower)  # VI1 < RMA(VI1) → support
                    
                if current_vi2 > vi2_rma[-1]:
                    vi2_selected_history.append(vi2_upper)  # VI2 > RMA(VI2) → résistance
                else:
                    vi2_selected_history.append(vi2_lower)  # VI2 < RMA(VI2) → support
                    
                if current_vi3 > vi3_rma[-1]:
                    vi3_selected_history.append(vi3_upper)  # VI3 > RMA(VI3) → résistance
                else:
                    vi3_selected_history.append(vi3_lower)  # VI3 < RMA(VI3) → support
            else:
                # Fallback : utiliser la bande supérieure
                vi1_selected_history.append(vi1_upper)
                vi2_selected_history.append(vi2_upper)
                vi3_selected_history.append(vi3_upper)
        else:
            # Fallback : utiliser la bande supérieure
            vi1_selected_history.append(vi1_upper)
            vi2_selected_history.append(vi2_upper)
            vi3_selected_history.append(vi3_upper)
    
    result = {
        'VI1_upper_history': vi1_upper_history,
        'VI1_lower_history': vi1_lower_history,
        'VI1_selected_history': vi1_selected_history,
        'VI2_upper_history': vi2_upper_history,
        'VI2_lower_history': vi2_lower_history,
        'VI2_selected_history': vi2_selected_history,
        'VI3_upper_history': vi3_upper_history,
        'VI3_lower_history': vi3_lower_history,
        'VI3_selected_history': vi3_selected_history,
        'center_line_history': center_line_history,
        'atr_history': atr_rma_history,
        'true_ranges': true_ranges
    }
    
    logger.info(f"Historique complet des VI calculé: {len(vi1_selected_history)} valeurs")
    logger.debug(f"Première valeur VI1: {vi1_selected_history[0] if vi1_selected_history else 'N/A'}")
    logger.debug(f"Dernière valeur VI1: {vi1_selected_history[-1] if vi1_selected_history else 'N/A'}")
    
    # Debug: Afficher les dernières valeurs pour vérification
    if vi1_selected_history:
        print(f"🔧 DEBUG VI CALCUL - Dernière bougie:")
        print(f"   Close: {closes[-1]:.2f}")
        print(f"   Ligne centrale: {center_line_history[-1]:.2f}")
        print(f"   ATR: {atr_rma_history[-1]:.2f}")
        print(f"   VI1 (sélectionné): {vi1_selected_history[-1]:.2f}")
        print(f"   VI1 (upper): {vi1_upper_history[-1]:.2f}")
        print(f"   VI1 (lower): {vi1_lower_history[-1]:.2f}")
        print(f"   VI2 (sélectionné): {vi2_selected_history[-1]:.2f}")
        print(f"   VI2 (upper): {vi2_upper_history[-1]:.2f}")
        print(f"   VI2 (lower): {vi2_lower_history[-1]:.2f}")
        print(f"   VI3 (sélectionné): {vi3_selected_history[-1]:.2f}")
        print(f"   VI3 (upper): {vi3_upper_history[-1]:.2f}")
        print(f"   VI3 (lower): {vi3_lower_history[-1]:.2f}")
        print(f"   Logique: Close > VI_upper ? VI1:{closes[-1] > vi1_upper_history[-1]}, VI2:{closes[-1] > vi2_upper_history[-1]}, VI3:{closes[-1] > vi3_upper_history[-1]}")
    
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