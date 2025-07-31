import pandas as pd
import numpy as np
from core.logger import BitSniperLogger

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
    logger = BitSniperLogger()
    logger.logger.info("🔧 DEBUG: Fonction calculate_volatility_indexes appelée")
    
    if len(closes) < 28:
        logger.logger.warning(f"Pas assez de données pour calculer les VI. Nécessaire: 28, Disponible: {len(closes)}")
        return {'VI1': None, 'VI2': None, 'VI3': None}
    
    # Calculer les True Ranges (méthode classique)
    true_ranges = []
    logger.logger.info(f"🔧 DEBUG ATR - Calcul des True Ranges (méthode classique):")
    logger.logger.info(f"   Nombre de bougies: {len(closes)}")
    logger.logger.info(f"   Dernières 3 bougies:")
    for i in range(max(0, len(closes)-3), len(closes)):
        logger.logger.info(f"     Bougie {i}: High={highs[i]}, Low={lows[i]}, Close={closes[i]}")
    
    for i in range(1, len(closes)):
        high_low = highs[i] - lows[i]
        high_close_prev = abs(highs[i] - closes[i-1])
        low_close_prev = abs(lows[i] - closes[i-1])
        true_range = max(high_low, high_close_prev, low_close_prev)
        true_ranges.append(true_range)
        
        # Log des 3 derniers True Ranges
        if i >= len(closes) - 3:
            logger.logger.info(f"     True Range {i}: {true_range:.2f} (HL:{high_low:.2f}, HC:{high_close_prev:.2f}, LC:{low_close_prev:.2f})")
    
    logger.logger.info(f"   Nombre de True Ranges calculés: {len(true_ranges)}")
    logger.logger.info(f"   Derniers True Ranges: {true_ranges[-3:] if len(true_ranges) >= 3 else true_ranges}")
    
    # Vérifier qu'on a assez de True Ranges
    if len(true_ranges) < 28:
        logger.logger.warning(f"Pas assez de True Ranges pour calculer l'ATR. Nécessaire: 28, Disponible: {len(true_ranges)}")
        return {'VI1': None, 'VI2': None, 'VI3': None}
    
    # Calculer l'ATR (RMA des True Ranges sur 28 périodes)
    atr_rma = rma(true_ranges, 28)
    if atr_rma is None:
        logger.logger.warning("Impossible de calculer l'ATR RMA")
        return {'VI1': None, 'VI2': None, 'VI3': None}
    
    logger.logger.info(f"🔧 DEBUG ATR RMA:")
    logger.logger.info(f"   Nombre de valeurs ATR RMA: {len(atr_rma)}")
    logger.logger.info(f"   Dernières 3 valeurs ATR RMA: {atr_rma[-3:] if len(atr_rma) >= 3 else atr_rma}")
    
    # Calculer la ligne centrale (RMA des closes sur 28 périodes)
    center_line_rma = rma(closes, 28)
    if center_line_rma is None:
        logger.logger.warning("Impossible de calculer la ligne centrale RMA")
        return {'VI1': None, 'VI2': None, 'VI3': None}
    
    logger.logger.info(f"🔧 DEBUG Center Line RMA:")
    logger.logger.info(f"   Nombre de valeurs Center Line RMA: {len(center_line_rma)}")
    logger.logger.info(f"   Dernières 3 valeurs Center Line RMA: {center_line_rma[-3:] if len(center_line_rma) >= 3 else center_line_rma}")
    
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
    
    # Logique de sélection des bandes basée sur les croisements
    # Si close > VI_upper → utiliser VI_lower (le prix traverse la bande supérieure vers le haut)
    # Si close < VI_lower → utiliser VI_upper (le prix traverse la bande inférieure vers le bas)
    # Valeurs par défaut si aucun croisement détecté
    
    # Sélection pour VI1 (défaut: lower)
    vi1 = vi1_lower  # Par défaut, utiliser le support
    if close > vi1_upper:
        vi1 = vi1_lower  # Le prix traverse la bande supérieure vers le haut → utiliser le support
    elif close < vi1_lower:
        vi1 = vi1_upper  # Le prix traverse la bande inférieure vers le bas → utiliser la résistance
    
    # Sélection pour VI2 (défaut: upper)
    vi2 = vi2_upper  # Par défaut, utiliser la résistance
    if close > vi2_upper:
        vi2 = vi2_lower  # Le prix traverse la bande supérieure vers le haut → utiliser le support
    elif close < vi2_lower:
        vi2 = vi2_upper  # Le prix traverse la bande inférieure vers le bas → utiliser la résistance
    
    # Sélection pour VI3 (défaut: upper)
    vi3 = vi3_upper  # Par défaut, utiliser la résistance
    if close > vi3_upper:
        vi3 = vi3_lower  # Le prix traverse la bande supérieure vers le haut → utiliser le support
    elif close < vi3_lower:
        vi3 = vi3_upper  # Le prix traverse la bande inférieure vers le bas → utiliser la résistance
    
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
    
    logger.logger.info(f"🔧 VI CALCUL DÉTAILLÉ:")
    logger.logger.info(f"   Close: {close:.2f}")
    logger.logger.info(f"   Ligne centrale: {center_line:.2f}")
    logger.logger.info(f"   ATR (RMA TR 28): {atr:.2f}")
    logger.logger.info(f"   VI1 - Upper: {vi1_upper:.2f}, Lower: {vi1_lower:.2f}, Selected: {vi1:.2f}")
    logger.logger.info(f"   VI2 - Upper: {vi2_upper:.2f}, Lower: {vi2_lower:.2f}, Selected: {vi2:.2f}")
    logger.logger.info(f"   VI3 - Upper: {vi3_upper:.2f}, Lower: {vi3_lower:.2f}, Selected: {vi3:.2f}")
    logger.logger.info(f"   Logique: Close > VI_upper ? VI1:{close > vi1_upper}, VI2:{close > vi2_upper}, VI3:{close > vi3_upper}")
    logger.logger.info(f"   Sélection finale: VI1:{vi1:.2f}, VI2:{vi2:.2f}, VI3:{vi3:.2f}")
    
    return result

def calculate_volatility_indexes_real_logic(closes, highs, lows, vi1_crossing_time, vi2_crossing_time, vi3_crossing_time):
    """
    Calcule les Volatility Indexes selon la vraie logique découverte.
    
    Logique :
    - Quand il y a croisement (VI vs Close) : VI = VI_précédente ± (ATR × multiplicateur)
    - Quand pas de croisement : VI = VI_précédente ± (différence_ATR × multiplicateur)
    
    :param closes: Liste des prix de clôture
    :param highs: Liste des prix hauts
    :param lows: Liste des prix bas
    :param vi1_crossing_time: Timestamp du croisement VI1 (1753612200000)
    :param vi2_crossing_time: Timestamp du croisement VI2 (1754028900000)
    :param vi3_crossing_time: Timestamp du croisement VI3 (1754076600000)
    :return: Dictionnaire avec les VI calculés
    """
    if len(closes) < 28:
        print("❌ Pas assez de données pour calculer les VI avec la logique réelle.")
        return None
    
    # Convertir les timestamps en indices dans le buffer
    vi1_crossing_index = None
    vi2_crossing_index = None
    vi3_crossing_index = None
    
    # Trouver les indices correspondants aux timestamps de croisement
    for i, candle in enumerate(closes):
        if isinstance(candle, dict) and 'time' in candle:
            candle_time = candle['time']
            if candle_time == vi1_crossing_time:
                vi1_crossing_index = i
            elif candle_time == vi2_crossing_time:
                vi2_crossing_index = i
            elif candle_time == vi3_crossing_time:
                vi3_crossing_index = i
    
    if vi1_crossing_index is None or vi2_crossing_index is None or vi3_crossing_index is None:
        print("❌ Impossible de trouver les indices de croisement dans l'historique")
        return None
    
    # Calculer les ATR pour chaque période
    atr_28_history = calculate_atr_history(highs, lows, closes, period=28)
    atr_10_history = calculate_atr_history(highs, lows, closes, period=10)
    atr_6_history = calculate_atr_history(highs, lows, closes, period=6)
    
    # Initialiser les VI avec des valeurs de départ (à ajuster selon les croisements)
    vi1_history = []
    vi2_history = []
    vi3_history = []
    
    # États initiaux selon les croisements
    vi1_state = "BULLISH"  # VI1 < close au croisement
    vi2_state = "BULLISH"  # VI2 < close au croisement
    vi3_state = "BEARISH"  # VI3 > close au croisement
    
    # Valeurs initiales des VI (à ajuster selon les données réelles)
    vi1_current = closes[vi1_crossing_index]['close'] * 0.97  # VI1 légèrement sous le close
    vi2_current = closes[vi2_crossing_index]['close'] * 0.98  # VI2 légèrement sous le close
    vi3_current = closes[vi3_crossing_index]['close'] * 1.02  # VI3 légèrement au-dessus du close
    
    # Calculer l'historique complet des VI
    for i in range(len(closes)):
        if i < 28:  # Pas assez de données pour ATR
            vi1_history.append(vi1_current)
            vi2_history.append(vi2_current)
            vi3_history.append(vi3_current)
            continue
        
        current_close = closes[i]['close']
        
        # VI1 (ATR 28 périodes)
        if i < len(atr_28_history):
            atr_28_current = atr_28_history[i - 28]
            atr_28_previous = atr_28_history[i - 29] if i > 28 else atr_28_current
            
            # Détecter si VI1 croise le close
            vi1_crossing = (vi1_current > current_close and vi1_state == "BULLISH") or \
                          (vi1_current < current_close and vi1_state == "BEARISH")
            
            if vi1_crossing:
                # Croisement détecté - utiliser ATR entier
                if vi1_current > current_close:
                    vi1_current = vi1_current - (atr_28_current * 19)
                    vi1_state = "BEARISH"
                else:
                    vi1_current = vi1_current + (atr_28_current * 19)
                    vi1_state = "BULLISH"
            else:
                # Pas de croisement - utiliser différence d'ATR
                atr_diff = atr_28_current - atr_28_previous
                if vi1_state == "BEARISH":  # VI1 > close
                    if atr_28_current > atr_28_previous:
                        vi1_current += (atr_diff * 19)
                    else:
                        vi1_current -= (atr_diff * 19)
                else:  # vi1_state == "BULLISH" - VI1 < close
                    if atr_28_current > atr_28_previous:
                        vi1_current -= (atr_diff * 19)
                    else:
                        vi1_current += (atr_diff * 19)
        
        # VI2 (ATR 10 périodes)
        if i < len(atr_10_history):
            atr_10_current = atr_10_history[i - 10]
            atr_10_previous = atr_10_history[i - 11] if i > 10 else atr_10_current
            
            # Détecter si VI2 croise le close
            vi2_crossing = (vi2_current > current_close and vi2_state == "BULLISH") or \
                          (vi2_current < current_close and vi2_state == "BEARISH")
            
            if vi2_crossing:
                # Croisement détecté - utiliser ATR entier
                if vi2_current > current_close:
                    vi2_current = vi2_current - (atr_10_current * 10)
                    vi2_state = "BEARISH"
                else:
                    vi2_current = vi2_current + (atr_10_current * 10)
                    vi2_state = "BULLISH"
            else:
                # Pas de croisement - utiliser différence d'ATR
                atr_diff = atr_10_current - atr_10_previous
                if vi2_state == "BEARISH":  # VI2 > close
                    if atr_10_current > atr_10_previous:
                        vi2_current += (atr_diff * 10)
                    else:
                        vi2_current -= (atr_diff * 10)
                else:  # vi2_state == "BULLISH" - VI2 < close
                    if atr_10_current > atr_10_previous:
                        vi2_current -= (atr_diff * 10)
                    else:
                        vi2_current += (atr_diff * 10)
        
        # VI3 (ATR 6 périodes)
        if i < len(atr_6_history):
            atr_6_current = atr_6_history[i - 6]
            atr_6_previous = atr_6_history[i - 7] if i > 6 else atr_6_current
            
            # Détecter si VI3 croise le close
            vi3_crossing = (vi3_current > current_close and vi3_state == "BULLISH") or \
                          (vi3_current < current_close and vi3_state == "BEARISH")
            
            if vi3_crossing:
                # Croisement détecté - utiliser ATR entier
                if vi3_current > current_close:
                    vi3_current = vi3_current - (atr_6_current * 6)
                    vi3_state = "BEARISH"
                else:
                    vi3_current = vi3_current + (atr_6_current * 6)
                    vi3_state = "BULLISH"
            else:
                # Pas de croisement - utiliser différence d'ATR
                atr_diff = atr_6_current - atr_6_previous
                if vi3_state == "BEARISH":  # VI3 > close
                    if atr_6_current > atr_6_previous:
                        vi3_current += (atr_diff * 6)
                    else:
                        vi3_current -= (atr_diff * 6)
                else:  # vi3_state == "BULLISH" - VI3 < close
                    if atr_6_current > atr_6_previous:
                        vi3_current -= (atr_diff * 6)
                    else:
                        vi3_current += (atr_diff * 6)
        
        vi1_history.append(vi1_current)
        vi2_history.append(vi2_current)
        vi3_history.append(vi3_current)
    
    return {
        'vi1_history': vi1_history,
        'vi2_history': vi2_history,
        'vi3_history': vi3_history,
        'vi1_crossing_index': vi1_crossing_index,
        'vi2_crossing_index': vi2_crossing_index,
        'vi3_crossing_index': vi3_crossing_index
    }

def calculate_atr_history(highs, lows, closes, period=28):
    """
    Calcule l'historique complet de l'ATR pour une période donnée.
    
    :param highs: Liste des prix hauts
    :param lows: Liste des prix bas
    :param closes: Liste des prix de clôture
    :param period: Période pour l'ATR
    :return: Liste des valeurs ATR
    """
    if len(closes) < period:
        return []
    
    # Calculer les True Ranges
    true_ranges = []
    for i in range(len(closes)):
        if i == 0:
            true_ranges.append(highs[i] - lows[i])
        else:
            high_low = highs[i] - lows[i]
            high_close_prev = abs(highs[i] - closes[i-1])
            low_close_prev = abs(lows[i] - closes[i-1])
            true_ranges.append(max(high_low, high_close_prev, low_close_prev))
    
    # Calculer l'ATR avec la méthode de Wilder (RMA)
    atr_history = []
    atr_current = sum(true_ranges[:period]) / period
    atr_history.append(atr_current)
    
    for i in range(period, len(true_ranges)):
        atr_current = ((atr_current * (period - 1)) + true_ranges[i]) / period
        atr_history.append(atr_current)
    
    return atr_history

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
    
    # Lissage Wilder pour les valeurs suivantes
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
    logger = BitSniperLogger()
    logger.logger.info("🔧 DEBUG: Fonction calculate_complete_volatility_indexes_history appelée")
    
    if len(closes) < 28:
        logger.logger.warning(f"Pas assez de données pour calculer l'historique des VI. Nécessaire: 28, Disponible: {len(closes)}")
        return None
    
    # Calculer les True Ranges (méthode classique)
    true_ranges = []
    for i in range(1, len(closes)):
        high_low = highs[i] - lows[i]
        high_close_prev = abs(highs[i] - closes[i-1])
        low_close_prev = abs(lows[i] - closes[i-1])
        true_range = max(high_low, high_close_prev, low_close_prev)
        true_ranges.append(true_range)
    
    # Vérifier qu'on a assez de True Ranges
    if len(true_ranges) < 28:
        logger.logger.warning(f"Pas assez de True Ranges pour calculer l'historique ATR. Nécessaire: 28, Disponible: {len(true_ranges)}")
        return None
    
    # Calculer l'historique complet de l'ATR (RMA des True Ranges sur 28 périodes)
    atr_rma_history = calculate_complete_rma_history(true_ranges, 28)
    if atr_rma_history is None:
        logger.logger.warning("Impossible de calculer l'historique de l'ATR RMA")
        return None
    
    # Calculer l'historique complet de la ligne centrale (RMA des closes sur 28 périodes)
    center_line_history = calculate_complete_rma_history(closes, 28)
    if center_line_history is None:
        logger.logger.warning("Impossible de calculer l'historique de la ligne centrale RMA")
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
    # CORRECTION: Aligner correctement les indices pour correspondre aux mêmes périodes
    # Maintenant: close[i] correspond à atr[i-28] et center_line[i-28] (même période)
    for i in range(27, len(closes)):
        # Vérifier qu'on ne dépasse pas les indices
        if i >= len(closes) or (i - 28) >= len(atr_rma_history) or (i - 28) >= len(center_line_history):
            break
            
        close = closes[i]
        atr = atr_rma_history[i - 28]  # ATR correspondant à la même période (corrigé)
        center_line = center_line_history[i - 28]  # Ligne centrale correspondante (corrigé)
        
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
        
        # Logique de sélection des bandes basée sur les croisements
        # Si close > VI_upper → utiliser VI_lower (le prix traverse la bande supérieure vers le haut)
        # Si close < VI_lower → utiliser VI_upper (le prix traverse la bande inférieure vers le bas)
        # Valeurs par défaut si aucun croisement détecté
        
        # Sélection pour VI1 (défaut: lower)
        vi1_selected = vi1_lower  # Par défaut, utiliser le support
        if close > vi1_upper:
            vi1_selected = vi1_lower  # Le prix traverse la bande supérieure vers le haut → utiliser le support
        elif close < vi1_lower:
            vi1_selected = vi1_upper  # Le prix traverse la bande inférieure vers le bas → utiliser la résistance
        vi1_selected_history.append(vi1_selected)
        
        # Sélection pour VI2 (défaut: lower)
        vi2_selected = vi2_lower  # Par défaut, utiliser le support
        if close > vi2_upper:
            vi2_selected = vi2_lower  # Le prix traverse la bande supérieure vers le haut → utiliser le support
        elif close < vi2_lower:
            vi2_selected = vi2_upper  # Le prix traverse la bande inférieure vers le bas → utiliser la résistance
        vi2_selected_history.append(vi2_selected)
        
        # Sélection pour VI3 (défaut: lower)
        vi3_selected = vi3_lower  # Par défaut, utiliser le support
        if close > vi3_upper:
            vi3_selected = vi3_lower  # Le prix traverse la bande supérieure vers le haut → utiliser le support
        elif close < vi3_lower:
            vi3_selected = vi3_upper  # Le prix traverse la bande inférieure vers le bas → utiliser la résistance
        vi3_selected_history.append(vi3_selected)
    
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
    
    logger.logger.info(f"Historique complet des VI calculé: {len(vi1_selected_history)} valeurs")
    logger.logger.debug(f"Première valeur VI1: {vi1_selected_history[0] if vi1_selected_history else 'N/A'}")
    logger.logger.debug(f"Dernière valeur VI1: {vi1_selected_history[-1] if vi1_selected_history else 'N/A'}")
    
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
        print(f"   Sélection finale: VI1:{vi1_selected_history[-1]:.2f}, VI2:{vi2_selected_history[-1]:.2f}, VI3:{vi3_selected_history[-1]:.2f}")
    
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

def calculate_vi_phases(atr_history, period=28):
    """
    Calcule les phases VI (bullish/bearish) basées sur la comparaison ATR actuel vs ATR moyen.
    
    :param atr_history: liste des valeurs ATR (du plus ancien au plus récent)
    :param period: période pour calculer l'ATR moyen (défaut: 28)
    :return: dictionnaire avec les phases VI et données associées
    """
    logger = BitSniperLogger()
    logger.logger.info("🔧 DEBUG: Fonction calculate_vi_phases appelée")
    
    if len(atr_history) < period:
        logger.logger.warning(f"Pas assez de données ATR pour calculer les phases VI. Nécessaire: {period}, Disponible: {len(atr_history)}")
        return None
    
    # Calculer l'ATR moyen sur 28 périodes
    atr_moyen = sum(atr_history[-period:]) / period
    
    # ATR actuel (dernière valeur)
    atr_actuel = atr_history[-1]
    
    # Calculer les valeurs VI basées sur l'ATR actuel
    vi1_value = atr_actuel * 19
    vi2_value = atr_actuel * 10
    vi3_value = atr_actuel * 6
    
    # Déterminer les phases basées sur ATR actuel vs ATR moyen
    # Si ATR actuel < ATR moyen → changement de phase
    vi1_phase = 'BEARISH' if atr_actuel < atr_moyen else 'BULLISH'
    vi2_phase = 'BEARISH' if atr_actuel < atr_moyen else 'BULLISH'
    vi3_phase = 'BEARISH' if atr_actuel < atr_moyen else 'BULLISH'
    
    result = {
        'VI1_phase': vi1_phase,
        'VI2_phase': vi2_phase,
        'VI3_phase': vi3_phase,
        'VI1_value': vi1_value,
        'VI2_value': vi2_value,
        'VI3_value': vi3_value,
        'ATR_actuel': atr_actuel,
        'ATR_moyen': atr_moyen,
        'ATR_ratio': atr_actuel / atr_moyen if atr_moyen > 0 else 1.0
    }
    
    logger.logger.info(f"🔧 VI PHASES CALCULÉES:")
    logger.logger.info(f"   ATR actuel: {atr_actuel:.2f}")
    logger.logger.info(f"   ATR moyen (28p): {atr_moyen:.2f}")
    logger.logger.info(f"   Ratio ATR: {result['ATR_ratio']:.3f}")
    logger.logger.info(f"   VI1: {vi1_phase} (valeur: {vi1_value:.2f})")
    logger.logger.info(f"   VI2: {vi2_phase} (valeur: {vi2_value:.2f})")
    logger.logger.info(f"   VI3: {vi3_phase} (valeur: {vi3_value:.2f})")
    
    return result

def calculate_complete_vi_phases_history(atr_history, period=28):
    """
    Calcule l'historique complet des phases VI.
    Cette fonction est utilisée au démarrage pour initialiser correctement les indicateurs.
    
    :param atr_history: liste des valeurs ATR (du plus ancien au plus récent)
    :param period: période pour calculer l'ATR moyen (défaut: 28)
    :return: dictionnaire avec l'historique des phases VI
    """
    logger = BitSniperLogger()
    logger.logger.info("🔧 DEBUG: Fonction calculate_complete_vi_phases_history appelée")
    
    if len(atr_history) < period:
        logger.logger.warning(f"Pas assez de données ATR pour calculer l'historique des phases VI. Nécessaire: {period}, Disponible: {len(atr_history)}")
        return None
    
    # Historique des phases
    vi1_phases = []
    vi2_phases = []
    vi3_phases = []
    
    # Historique des valeurs
    vi1_values = []
    vi2_values = []
    vi3_values = []
    
    # Historique des ATR moyens
    atr_moyens = []
    
    # Commencer à partir de l'index period-1 (pour avoir assez de données pour calculer l'ATR moyen)
    for i in range(period-1, len(atr_history)):
        # ATR actuel
        atr_actuel = atr_history[i]
        
        # Calculer l'ATR moyen sur les 28 périodes précédentes
        atr_moyen = sum(atr_history[i-period+1:i+1]) / period
        
        # Calculer les valeurs VI
        vi1_value = atr_actuel * 19
        vi2_value = atr_actuel * 10
        vi3_value = atr_actuel * 6
        
        # Déterminer les phases
        vi1_phase = 'BEARISH' if atr_actuel < atr_moyen else 'BULLISH'
        vi2_phase = 'BEARISH' if atr_actuel < atr_moyen else 'BULLISH'
        vi3_phase = 'BEARISH' if atr_actuel < atr_moyen else 'BULLISH'
        
        # Stocker les résultats
        vi1_phases.append(vi1_phase)
        vi2_phases.append(vi2_phase)
        vi3_phases.append(vi3_phase)
        vi1_values.append(vi1_value)
        vi2_values.append(vi2_value)
        vi3_values.append(vi3_value)
        atr_moyens.append(atr_moyen)
    
    result = {
        'VI1_phases': vi1_phases,
        'VI2_phases': vi2_phases,
        'VI3_phases': vi3_phases,
        'VI1_values': vi1_values,
        'VI2_values': vi2_values,
        'VI3_values': vi3_values,
        'ATR_moyens': atr_moyens,
        'ATR_history': atr_history
    }
    
    logger.logger.info(f"Historique complet des phases VI calculé: {len(vi1_phases)} valeurs")
    if vi1_phases:
        logger.logger.info(f"Dernière phase VI1: {vi1_phases[-1]}")
        logger.logger.info(f"Dernière phase VI2: {vi2_phases[-1]}")
        logger.logger.info(f"Dernière phase VI3: {vi3_phases[-1]}")
    
    return result

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