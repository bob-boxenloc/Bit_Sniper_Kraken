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

# Fonction supprimée - trop complexe, on va faire plus simple

def calculate_atr_history(highs, lows, closes, period=28):
    """
    Calcule l'historique complet de l'ATR avec Moyenne Mobile Simple (SMA).
    ⚠️ CHANGEMENT : Remplacé Wilder Smoothing par SMA pour plus de réactivité !
    
    :param highs: Liste des prix hauts
    :param lows: Liste des prix bas
    :param closes: Liste des prix de clôture
    :param period: Période pour l'ATR
    :return: Liste des valeurs ATR
    """
    if len(closes) < period:
        return []
    
    # Vérifier que toutes les listes ont la même longueur
    if len(highs) != len(closes) or len(lows) != len(closes):
        print(f"❌ ERREUR: Longueurs différentes - highs: {len(highs)}, lows: {len(lows)}, closes: {len(closes)}")
        return []
    
    # Calculer les True Ranges (comme Kraken: High - Low seulement)
    true_ranges = []
    print(f"🔧 DEBUG - DONNÉES OHLC UTILISÉES:")
    print(f"   Nombre de bougies: {len(closes)}")
    print(f"   Dernières 5 bougies (High, Low, Close):")
    for i in range(max(0, len(closes)-5), len(closes)):
        print(f"     Bougie {i}: H={highs[i]:.2f}, L={lows[i]:.2f}, C={closes[i]:.2f}")
    
    for i in range(0, len(closes)):
        # Kraken utilise simplement: High - Low
        true_range = highs[i] - lows[i]
        true_ranges.append(true_range)
    
    # Vérifier qu'on a assez de True Ranges
    if len(true_ranges) < period:
        print(f"❌ ERREUR: Pas assez de True Ranges - Nécessaire: {period}, Disponible: {len(true_ranges)}")
        return []
    
    # LOG DÉTAILLÉ ATR
    print(f"🔧 DEBUG ATR - CALCUL DÉTAILLÉ:")
    print(f"   Nombre de True Ranges calculés: {len(true_ranges)}")
    print(f"   Période ATR: {period}")
    
    # Log des 28 derniers True Ranges utilisés
    if len(true_ranges) >= period:
        print(f"   Les {period} derniers True Ranges utilisés:")
        for i, tr in enumerate(true_ranges[-period:]):
            print(f"     TR[{i+1}]: {tr:.2f}")
    
    # ✅ NOUVEAU : Calculer l'ATR avec Moyenne Mobile Simple (SMA) au lieu de Wilder
    atr_history = calculate_complete_sma_history(true_ranges, period)
    
    if atr_history:
        print(f"   Premier ATR (moyenne des {period} premiers): {atr_history[0]:.2f}")
        print(f"   Dernier ATR (SMA): {atr_history[-1]:.2f}")
        print(f"   Nombre d'ATR calculés: {len(atr_history)}")
        print(f"   ⚠️ CHANGEMENT : Utilisation SMA au lieu de Wilder pour plus de réactivité !")
    
    return atr_history

def calculate_complete_sma_history(values, period):
    """
    Calcule l'historique complet du SMA (Moyenne Mobile Simple) pour toutes les valeurs.
    ✅ NOUVEAU : Remplacé RMA par SMA pour plus de réactivité !
    
    :param values: liste des valeurs (du plus ancien au plus récent)
    :param period: période du SMA
    :return: liste des valeurs SMA calculées
    """
    if len(values) < period:
        return None
    
    # Calculer SMA glissant pour toutes les valeurs
    smas = []
    
    # Premier SMA : moyenne des 'period' premières valeurs
    first_sma = sum(values[:period]) / period
    smas.append(first_sma)
    
    # SMA glissant pour les valeurs suivantes
    for i in range(period, len(values)):
        # Supprimer la plus ancienne valeur et ajouter la nouvelle
        window_sum = sum(values[i-period+1:i+1])
        sma = window_sum / period
        smas.append(sma)
    
    return smas

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
    
    # Calculer les True Ranges (comme Kraken: High - Low seulement)
    true_ranges = []
    for i in range(0, len(closes)):  # CORRECTION: commencer à i=0 pour inclure toutes les bougies
        # Kraken utilise simplement: High - Low
        true_range = highs[i] - lows[i]
        true_ranges.append(true_range)
    
    # Vérifier qu'on a assez de True Ranges
    if len(true_ranges) < 28:
        logger.logger.warning(f"Pas assez de True Ranges pour calculer l'historique ATR. Nécessaire: 28, Disponible: {len(true_ranges)}")
        return None
    
    # LOG DÉTAILLÉ ATR
    logger.logger.info("🔧 DEBUG ATR - CALCUL DÉTAILLÉ:")
    logger.logger.info(f"   Nombre de True Ranges calculés: {len(true_ranges)}")
    logger.logger.info(f"   Période ATR: 28")
    
    # Log des 28 derniers True Ranges utilisés (excluant le dernier)
    if len(true_ranges) >= 29:  # On a besoin d'au moins 29 pour exclure le dernier
        logger.logger.info(f"   Les 28 derniers True Ranges utilisés (excluant le dernier):")
        for i, tr in enumerate(true_ranges[-29:-1]):  # Exclure le dernier
            logger.logger.info(f"     TR[{i+1}]: {tr:.2f}")
        logger.logger.info(f"     TR[{len(true_ranges)}]: {true_ranges[-1]:.2f} (EXCLUÉ - anormal)")
    
    # Calculer l'historique complet de l'ATR (RMA des True Ranges sur 28 périodes)
    # Exclure le dernier True Range comme dans calculate_volatility_indexes_corrected
    true_ranges_for_atr = true_ranges[:-1]  # Exclure le dernier True Range
    atr_rma_history = calculate_complete_sma_history(true_ranges_for_atr, 28)
    if atr_rma_history is None:
        logger.logger.warning("Impossible de calculer l'historique de l'ATR RMA")
        return None
    
    if atr_rma_history:
        logger.logger.info(f"   Premier ATR (moyenne des 28 premiers): {atr_rma_history[0]:.2f}")
        logger.logger.info(f"   Dernier ATR (Wilder): {atr_rma_history[-1]:.2f}")
        logger.logger.info(f"   Nombre d'ATR calculés: {len(atr_rma_history)}")
    
    # Calculer l'historique complet de la ligne centrale (RMA des closes sur 28 périodes)
    center_line_history = calculate_complete_sma_history(closes, 28)
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

def initialize_vi_history_from_user_values(highs, lows, closes):
    """
    Initialise l'historique des VI en partant des valeurs de départ fournies par l'utilisateur.
    Cette fonction évite de recalculer tout l'historique et utilise les valeurs de référence.
    
    :param highs: liste des prix hauts
    :param lows: liste des prix bas  
    :param closes: liste des prix de clôture
    :return: dictionnaire avec les historiques des VI
    """
    logger = BitSniperLogger()
    logger.logger.info("🔧 DEBUG: Fonction initialize_vi_history_from_user_values appelée")
    
    # Valeurs de départ fournies par l'utilisateur
    vi1_n1 = 113868  # BULLISH
    vi2_n1 = 123897  # BEARISH
    vi3_n1 = 121677  # BEARISH
    
    # États initiaux
    vi1_state = "BULLISH"
    vi2_state = "BEARISH"
    vi3_state = "BEARISH"
    
    # Calculer l'ATR 28 pour avoir les données nécessaires
    atr_28_history = calculate_atr_history(highs, lows, closes, period=28)
    if not atr_28_history:
        logger.logger.warning("Impossible de calculer l'ATR 28")
        return None
    
    # Créer des historiques factices basés sur les valeurs de départ
    # On va créer un historique cohérent en partant des valeurs de départ
    vi1_history = [vi1_n1]  # Valeur de départ
    vi2_history = [vi2_n1]  # Valeur de départ  
    vi3_history = [vi3_n1]  # Valeur de départ
    
    # Créer des historiques pour les phases VI
    vi1_phases = [vi1_state]
    vi2_phases = [vi2_state]
    vi3_phases = [vi3_state]
    
    # Créer des historiques pour les bandes (pour compatibilité)
    center_line_history = [closes[-1]]  # Utiliser le close actuel comme ligne centrale
    atr_current = atr_28_history[-1] if atr_28_history else 200  # ATR actuel ou valeur par défaut
    
    # Calculer les bandes basées sur les valeurs de départ
    vi1_upper = center_line_history[-1] + (atr_current * 19)
    vi1_lower = center_line_history[-1] - (atr_current * 19)
    vi2_upper = center_line_history[-1] + (atr_current * 10)
    vi2_lower = center_line_history[-1] - (atr_current * 10)
    vi3_upper = center_line_history[-1] + (atr_current * 6)
    vi3_lower = center_line_history[-1] - (atr_current * 6)
    
    # Créer les historiques des bandes
    vi1_upper_history = [vi1_upper]
    vi1_lower_history = [vi1_lower]
    vi2_upper_history = [vi2_upper]
    vi2_lower_history = [vi2_lower]
    vi3_upper_history = [vi3_upper]
    vi3_lower_history = [vi3_lower]
    
    # Sélectionner les bonnes bandes selon les valeurs de départ
    vi1_selected = vi1_lower if vi1_n1 < closes[-1] else vi1_upper
    vi2_selected = vi2_lower if vi2_n1 < closes[-1] else vi2_upper
    vi3_selected = vi3_lower if vi3_n1 < closes[-1] else vi3_upper
    
    vi1_selected_history = [vi1_selected]
    vi2_selected_history = [vi2_selected]
    vi3_selected_history = [vi3_selected]
    
    # Créer des True Ranges factices pour compatibilité
    true_ranges = [atr_current]  # Utiliser l'ATR comme True Range
    
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
        'atr_history': atr_28_history,
        'true_ranges': true_ranges
    }
    
    logger.logger.info(f"✅ Historique VI initialisé avec valeurs de départ:")
    logger.logger.info(f"   VI1: {vi1_n1} (État: {vi1_state})")
    logger.logger.info(f"   VI2: {vi2_n1} (État: {vi2_state})")
    logger.logger.info(f"   VI3: {vi3_n1} (État: {vi3_state})")
    logger.logger.info(f"   ATR 28: {atr_28_history[-1]:.2f}")
    
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
    volatility_indexes = calculate_volatility_indexes_corrected(closes, highs, lows)
    
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
    volatility_indexes = calculate_volatility_indexes_corrected(closes, highs, lows)
    
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

def calculate_volatility_indexes_corrected(closes, highs, lows, previous_vi1=None, previous_vi2=None, previous_vi3=None, previous_vi1_state=None, previous_vi2_state=None, previous_vi3_state=None, vi1_crossed_last_candle=False, vi2_crossed_last_candle=False, vi3_crossed_last_candle=False, vi1_crossing_direction=None, vi2_crossing_direction=None, vi3_crossing_direction=None):
    """
    Calcule les Volatility Indexes selon la vraie logique découverte (CORRIGÉE).
    
    Logique corrigée :
    - Différence ATR sert à calculer les VI n-1 (pas les VI n)
    - VI n = VI n-1 ± (ATR n × multiplicateur) si croisement
    - VI n = VI n-1 ± (différence_ATR n-1 × multiplicateur) si pas de croisement
    
    Différence ATR = abs(ATR_n-2 - ATR_n-1) (toujours positive)
    
    :param closes: Liste des prix de clôture
    :param highs: Liste des prix hauts
    :param lows: Liste des prix bas
    :param previous_vi1: VI1 précédent (si None, utilise la valeur de départ)
    :param previous_vi2: VI2 précédent (si None, utilise la valeur de départ)
    :param previous_vi3: VI3 précédent (si None, utilise la valeur de départ)
    :param previous_vi1_state: État précédent de VI1 (si None, utilise l'état initial)
    :param previous_vi2_state: État précédent de VI2 (si None, utilise l'état initial)
    :param previous_vi3_state: État précédent de VI3 (si None, utilise l'état initial)
    :param vi1_crossed_last_candle: Flag indiquant si VI1 a croisé à la bougie précédente
    :param vi2_crossed_last_candle: Flag indiquant si VI2 a croisé à la bougie précédente
    :param vi3_crossed_last_candle: Flag indiquant si VI3 a croisé à la bougie précédente
    :param vi1_crossing_direction: Direction du croisement VI1 ("UP" ou "DOWN")
    :param vi2_crossing_direction: Direction du croisement VI2 ("UP" ou "DOWN")
    :param vi3_crossing_direction: Direction du croisement VI3 ("UP" ou "DOWN")
    :return: Dictionnaire avec les VI calculés
    """
    if len(closes) < 28:
        print("❌ Pas assez de données pour calculer les VI")
        return None
    
    # Vérifier que toutes les listes ont la même longueur
    if len(highs) != len(closes) or len(lows) != len(closes):
        print(f"❌ ERREUR: Longueurs différentes - highs: {len(highs)}, lows: {len(lows)}, closes: {len(closes)}")
        return None
    
    # Valeurs de départ fournies par l'utilisateur (utilisées seulement si pas de valeurs précédentes)
    vi1_n1 = 113868  # BULLISH
    vi2_n1 = 123897  # BEARISH
    vi3_n1 = 121677  # BEARISH
    
    # États initiaux (utilisés seulement si pas d'états précédents)
    vi1_state_initial = "BULLISH"
    vi2_state_initial = "BEARISH"
    vi3_state_initial = "BEARISH"
    
    # Utiliser les valeurs précédentes si fournies, sinon utiliser les valeurs de départ
    vi1_previous = previous_vi1 if previous_vi1 is not None else vi1_n1
    vi2_previous = previous_vi2 if previous_vi2 is not None else vi2_n1
    vi3_previous = previous_vi3 if previous_vi3 is not None else vi3_n1
    
    vi1_state = previous_vi1_state if previous_vi1_state is not None else vi1_state_initial
    vi2_state = previous_vi2_state if previous_vi2_state is not None else vi2_state_initial
    vi3_state = previous_vi3_state if previous_vi3_state is not None else vi3_state_initial
    
    # ✅ NOUVEAU : Utiliser les flags de croisement passés en paramètres
    # Ces flags indiquent si un croisement a été détecté à la bougie précédente
    # et seront appliqués MAINTENANT (bougie N) si ils sont True
    
    # Initialiser les historiques avec la valeur précédente (ou de départ)
    vi1_history = [vi1_previous]  # n-1
    vi2_history = [vi2_previous]  # n-1
    vi3_history = [vi3_previous]  # n-1
    
    # Calculer UNIQUEMENT l'ATR 28 (utilisé pour tous les VI)
    atr_28_history = calculate_atr_history(highs, lows, closes, period=28)
    
    # Vérifier que l'ATR a été calculé correctement
    if not atr_28_history:
        print("❌ ERREUR: Impossible de calculer l'ATR 28")
        return None
    
    # LOGGER L'ATR 28 UNIQUE
    print(f"🔧 DEBUG VI CALCUL - ATR 28 UNIQUE:")
    print(f"   Close actuel: {closes[-1]:.2f}")
    print(f"   ATR 28: {atr_28_history[-1]:.2f}")
    print(f"   ATR 28 précédent: {atr_28_history[-2]:.2f}")
    print(f"   Différence ATR 28: {atr_28_history[-1] - atr_28_history[-2]:.2f}")
    print(f"   VI1 précédent: {vi1_previous:.2f} (État: {vi1_state})")
    print(f"   VI2 précédent: {vi2_previous:.2f} (État: {vi2_state})")
    print(f"   VI3 précédent: {vi3_previous:.2f} (État: {vi3_state})")
    
    # Calculer les VI pour la nouvelle bougie (n) seulement
    # Utiliser les 2 dernières bougies comme point de départ
    if len(closes) >= 2:
        current_close = closes[-1]  # Dernière bougie (nouvelle)
        
        # VI1 (ATR 28 × 19)
        if len(atr_28_history) >= 2:
            atr_28_current = atr_28_history[-1]  # ATR de la nouvelle bougie
            atr_28_previous = atr_28_history[-2]  # ATR de la bougie précédente
            
            # ✅ CORRECTION : Supprimer le calcul vi1_temp inutile qui contredisait la logique finale
            
            # Détecter le croisement en comparant la position PRÉCÉDENTE avec le close ACTUEL
            vi1_crossing = False
            vi1_direction = None
            if vi1_state == "BULLISH" and vi1_history[-1] > current_close:
                # VI1 était en dessous (BULLISH) et EST MAINTENANT au-dessus → croisement vers le HAUT
                vi1_crossing = True
                vi1_direction = "UP"
                vi1_crossed_last_candle = True  # ✅ MARQUER pour la prochaine bougie
                vi1_crossing_direction = "UP"
                print(f"   🔍 VI1 CROISEMENT HAUT DÉTECTÉ ! (sera appliqué à la prochaine bougie)")
            elif vi1_state == "BEARISH" and vi1_history[-1] < current_close:
                # VI1 était au-dessus (BEARISH) et EST MAINTENANT en dessous → croisement vers le BAS
                vi1_crossing = True
                vi1_direction = "DOWN"
                vi1_crossed_last_candle = True  # ✅ MARQUER pour la prochaine bougie
                vi1_crossing_direction = "DOWN"
                print(f"   🔍 VI1 CROISEMENT BAS DÉTECTÉ ! (sera appliqué à la prochaine bougie)")
            
            # ✅ NOUVELLE LOGIQUE : Vérifier s'il y a eu un croisement à la bougie précédente
            if vi1_crossed_last_candle:
                # Croisement détecté à la bougie précédente - utiliser ATR entier MAINTENANT
                if vi1_crossing_direction == "UP":
                    # Explosion vers le HAUT (VI1 était passé au-dessus du close)
                    vi1_new = vi1_history[-1] + (atr_28_current * 19)
                    vi1_state = "BEARISH"  # ✅ CHANGER L'ÉTAT MAINTENANT
                    print(f"   🔥 VI1 CROISEMENT HAUT APPLIQUÉ ! {vi1_history[-1]:.2f} → {vi1_new:.2f}")
                else:  # vi1_crossing_direction == "DOWN"
                    # Explosion vers le BAS (VI1 était passé en dessous du close)
                    vi1_new = vi1_history[-1] - (atr_28_current * 19)
                    vi1_state = "BULLISH"  # ✅ CHANGER L'ÉTAT MAINTENANT
                    print(f"   🔥 VI1 CROISEMENT BAS APPLIQUÉ ! {vi1_history[-1]:.2f} → {vi1_new:.2f}")
                
                # ✅ RÉINITIALISER le flag après application
                vi1_crossed_last_candle = False
                vi1_crossing_direction = None
            else:
                # Pas de croisement - utiliser différence ATR (avec signe)
                atr_diff = atr_28_current - atr_28_previous  # Différence avec ATR précédent
                if vi1_state == "BEARISH":  # VI1 > close
                    # BEARISH: VI monte si ATR monte, baisse si ATR baisse
                    vi1_new = vi1_history[-1] + (atr_diff * 19)
                else:  # vi1_state == "BULLISH" - VI1 < close
                    # BULLISH: VI baisse si ATR monte, monte si ATR baisse
                    vi1_new = vi1_history[-1] - (atr_diff * 19)
            
            vi1_history.append(vi1_new)
            print(f"   VI1 calculé: {vi1_new:.2f} (État: {vi1_state})")
        
        # VI2 (ATR 28 × 10)
        if len(atr_28_history) >= 2:
            atr_28_current = atr_28_history[-1]  # ATR de la nouvelle bougie
            atr_28_previous = atr_28_history[-2]  # ATR de la bougie précédente
            
            # ✅ CORRECTION : Supprimer le calcul vi2_temp inutile qui contredisait la logique finale
            
            # Détecter le croisement en comparant la position PRÉCÉDENTE avec le close ACTUEL
            vi2_crossing = False
            vi2_direction = None
            if vi2_state == "BULLISH" and vi2_history[-1] > current_close:
                # VI2 était en dessous (BULLISH) et EST MAINTENANT au-dessus → croisement vers le HAUT
                vi2_crossing = True
                vi2_direction = "UP"
                vi2_crossed_last_candle = True  # ✅ MARQUER pour la prochaine bougie
                vi2_crossing_direction = "UP"
                print(f"   🔍 VI2 CROISEMENT HAUT DÉTECTÉ ! (sera appliqué à la prochaine bougie)")
            elif vi2_state == "BEARISH" and vi2_history[-1] < current_close:
                # VI2 était au-dessus (BEARISH) et EST MAINTENANT en dessous → croisement vers le BAS
                vi2_crossing = True
                vi2_direction = "DOWN"
                vi2_crossed_last_candle = True  # ✅ MARQUER pour la prochaine bougie
                vi2_crossing_direction = "DOWN"
                print(f"   🔍 VI2 CROISEMENT BAS DÉTECTÉ ! (sera appliqué à la prochaine bougie)")
            
            # ✅ NOUVELLE LOGIQUE : Vérifier s'il y a eu un croisement à la bougie précédente
            if vi2_crossed_last_candle:
                # Croisement détecté à la bougie précédente - utiliser ATR entier MAINTENANT
                if vi2_crossing_direction == "UP":
                    # Explosion vers le HAUT (VI2 était passé au-dessus du close)
                    vi2_new = vi2_history[-1] + (atr_28_current * 10)
                    vi2_state = "BEARISH"  # ✅ CHANGER L'ÉTAT MAINTENANT
                    print(f"   🔥 VI2 CROISEMENT HAUT APPLIQUÉ ! {vi2_history[-1]:.2f} → {vi2_new:.2f}")
                else:  # vi2_crossing_direction == "DOWN"
                    # Explosion vers le BAS (VI2 était passé en dessous du close)
                    vi2_new = vi2_history[-1] - (atr_28_current * 10)
                    vi2_state = "BULLISH"  # ✅ CHANGER L'ÉTAT MAINTENANT
                    print(f"   🔥 VI2 CROISEMENT BAS APPLIQUÉ ! {vi2_history[-1]:.2f} → {vi2_new:.2f}")
                
                # ✅ RÉINITIALISER le flag après application
                vi2_crossed_last_candle = False
                vi2_crossing_direction = None
            else:
                # Pas de croisement - utiliser différence ATR (avec signe)
                atr_diff = atr_28_current - atr_28_previous  # Différence avec ATR précédent
                if vi2_state == "BEARISH":  # VI2 > close
                    # BEARISH: VI monte si ATR monte, baisse si ATR baisse
                    vi2_new = vi2_history[-1] + (atr_diff * 10)  # ✅ CORRECTION: Même logique que VI1
                else:  # vi2_state == "BULLISH" - VI2 < close
                    # BULLISH: VI baisse si ATR monte, monte si ATR baisse
                    vi2_new = vi2_history[-1] - (atr_diff * 10)  # ✅ CORRECTION: Même logique que VI1
            
            vi2_history.append(vi2_new)
            print(f"   VI2 calculé: {vi2_new:.2f} (État: {vi2_state})")
        
        # VI3 (ATR 28 × 6)
        if len(atr_28_history) >= 2:
            atr_28_current = atr_28_history[-1]  # ATR de la nouvelle bougie
            atr_28_previous = atr_28_history[-2]  # ATR de la bougie précédente
            
            # ✅ CORRECTION : VI3 suit maintenant la même logique unifiée que VI1 et VI2
            
            # Détecter le croisement en comparant la position PRÉCÉDENTE avec le close ACTUEL
            vi3_crossing = False
            vi3_direction = None
            if vi3_state == "BULLISH" and vi3_history[-1] > current_close:
                # VI3 était en dessous (BULLISH) et EST MAINTENANT au-dessus → croisement vers le HAUT
                vi3_crossing = True
                vi3_direction = "UP"
                vi3_crossed_last_candle = True  # ✅ MARQUER pour la prochaine bougie
                vi3_crossing_direction = "UP"
                print(f"   🔍 VI3 CROISEMENT HAUT DÉTECTÉ ! (sera appliqué à la prochaine bougie)")
            elif vi3_state == "BEARISH" and vi3_history[-1] < current_close:
                # VI3 était au-dessus (BEARISH) et EST MAINTENANT en dessous → croisement vers le BAS
                vi3_crossing = True
                vi3_direction = "DOWN"
                vi3_crossed_last_candle = True  # ✅ MARQUER pour la prochaine bougie
                vi3_crossing_direction = "DOWN"
                print(f"   🔍 VI3 CROISEMENT BAS DÉTECTÉ ! (sera appliqué à la prochaine bougie)")
            
            # ✅ NOUVELLE LOGIQUE : Vérifier s'il y a eu un croisement à la bougie précédente
            if vi3_crossed_last_candle:
                # Croisement détecté à la bougie précédente - utiliser ATR entier MAINTENANT
                if vi3_crossing_direction == "UP":
                    # Explosion vers le HAUT (VI3 était passé au-dessus du close)
                    vi3_new = vi3_history[-1] + (atr_28_current * 6)
                    vi3_state = "BEARISH"  # ✅ CHANGER L'ÉTAT MAINTENANT
                    print(f"   🔥 VI3 CROISEMENT HAUT APPLIQUÉ ! {vi3_history[-1]:.2f} → {vi3_new:.2f}")
                else:  # vi3_crossing_direction == "DOWN"
                    # Explosion vers le BAS (VI3 était passé en dessous du close)
                    vi3_new = vi3_history[-1] - (atr_28_current * 6)
                    vi3_state = "BULLISH"  # ✅ CHANGER L'ÉTAT MAINTENANT
                    print(f"   🔥 VI3 CROISEMENT BAS APPLIQUÉ ! {vi3_history[-1]:.2f} → {vi3_new:.2f}")
                
                # ✅ RÉINITIALISER le flag après application
                vi3_crossed_last_candle = False
                vi3_crossing_direction = None
            else:
                # Pas de croisement - utiliser différence ATR (avec signe)
                atr_diff = atr_28_current - atr_28_previous  # Différence avec ATR précédent
                if vi3_state == "BEARISH":  # VI3 > close
                    # BEARISH: VI monte si ATR monte, baisse si ATR baisse
                    vi3_new = vi3_history[-1] + (atr_diff * 6)  # ✅ CORRECTION: Même logique que VI1
                else:  # vi3_state == "BULLISH" - VI3 < close
                    # BULLISH: VI baisse si ATR monte, monte si ATR baisse
                    vi3_new = vi3_history[-1] - (atr_diff * 6)  # ✅ CORRECTION: Même logique que VI1
    
            vi3_history.append(vi3_new)
            print(f"   VI3 calculé: {vi3_new:.2f} (État: {vi3_state})")
    
    return {
        'VI1': vi1_history[-1],
        'VI2': vi2_history[-1],
        'VI3': vi3_history[-1],
        'VI1_upper': vi1_history[-1] + (atr_28_current * 19),
        'VI1_lower': vi1_history[-1] - (atr_28_current * 19),
        'VI2_upper': vi2_history[-1] + (atr_28_current * 10),
        'VI2_lower': vi2_history[-1] - (atr_28_current * 10),
        'VI3_upper': vi3_history[-1] + (atr_28_current * 6),
        'VI3_lower': vi3_history[-1] - (atr_28_current * 6),
        'center_line': closes[-1],  # Utiliser le close actuel comme ligne centrale
        
        # ✅ NOUVEAU : Flags de croisement pour la prochaine bougie
        'vi1_crossed_last_candle': vi1_crossed_last_candle,
        'vi2_crossed_last_candle': vi2_crossed_last_candle,
        'vi3_crossed_last_candle': vi3_crossed_last_candle,
        'vi1_crossing_direction': vi1_crossing_direction,
        'vi2_crossing_direction': vi2_crossing_direction,
        'vi3_crossing_direction': vi3_crossing_direction
    }

def calculate_rsi_for_new_candle(closes, avg_gain_prev, avg_loss_prev, period=40):
    """
    Calcule le RSI pour la nouvelle bougie en utilisant les moyennes RMA précédentes.
    Cette fonction évite de recalculer tout l'historique.
    
    :param closes: Liste des closes (du plus ancien au plus récent)
    :param avg_gain_prev: Moyenne des gains de la période précédente
    :param avg_loss_prev: Moyenne des pertes de la période précédente
    :param period: Période du RSI (défaut: 40)
    :return: RSI pour la nouvelle bougie
    """
    if len(closes) < 2:
        return None
    
    # Calculer le delta de la nouvelle bougie
    new_delta = closes[-1] - closes[-2]
    
    # Calculer gain et perte de la nouvelle bougie
    new_gain = max(new_delta, 0)
    new_loss = max(-new_delta, 0)
    
    # Calculer les nouvelles moyennes RMA
    new_avg_gain = (avg_gain_prev * (period - 1) + new_gain) / period
    new_avg_loss = (avg_loss_prev * (period - 1) + new_loss) / period
    
    # Calculer le RSI
    if new_avg_loss == 0:
        return 100.0
    
    rs = new_avg_gain / new_avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi, new_avg_gain, new_avg_loss

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
    vi = calculate_volatility_indexes_corrected(closes, highs, lows)
    print("\nVolatility Indexes :")
    for name, value in vi.items():
        print(f"{name}: {value}")
    
    # Test de validation
    candles = [{'close': c, 'high': h, 'low': l} for c, h, l in zip(closes, highs, lows)]
    is_valid, message = has_sufficient_history_for_indicators(candles, 40)
    print(f"\nValidation: {is_valid} - {message}") 