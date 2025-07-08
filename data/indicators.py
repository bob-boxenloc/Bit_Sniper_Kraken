import pandas as pd
import logging
from core.initialization import is_initialization_ready, initialization_manager
import numpy as np

def calculate_rsi_wilder(closes: list, length: int = 12) -> float:
    """
    Calcule le RSI selon la méthode Wilder (lissage exponentiel discret).
    
    Args:
        closes: Liste des prix de clôture (du plus ancien au plus récent)
        length: Période du RSI (défaut: 12)
    
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

def calculate_rsi_sma_signal(closes: list, length_rsi: int = 12, length_ma: int = 14) -> float:
    """
    Calcule le RSI Wilder puis applique un SMA pour la ligne de signal.
    
    Args:
        closes: Liste des prix de clôture
        length_rsi: Période du RSI (défaut: 12)
        length_ma: Période du SMA (défaut: 14)
    
    Returns:
        RSI avec lissage SMA pour la dernière période
    """
    if len(closes) < length_rsi + length_ma:
        return None
    
    # Calculer les RSI bruts pour les dernières périodes
    rsi_values = []
    for i in range(length_ma):
        start_idx = len(closes) - length_ma - length_rsi + i
        end_idx = len(closes) - length_ma + i + 1
        period_closes = closes[start_idx:end_idx]
        rsi = calculate_rsi_wilder(period_closes, length_rsi)
        if rsi is not None:
            rsi_values.append(rsi)
    
    if len(rsi_values) < length_ma:
        return None
    
    # Appliquer SMA sur les RSI bruts
    return sum(rsi_values) / len(rsi_values)

def compute_rsi(closes, period=12, smoothing_period=14):
    """
    Calcule le RSI selon la méthode Wilder (comme Kraken).
    
    :param closes: liste ou Series de prix de clôture
    :param period: période du RSI (par défaut 12)
    :param smoothing_period: période du lissage SMA (optionnel, par défaut 14)
    :return: RSI Wilder pour la dernière période
    """
    logger = logging.getLogger(__name__)
    
    # Convertir en liste si c'est une Series
    if isinstance(closes, pd.Series):
        closes = closes.tolist()
    
    # Log des données d'entrée pour debug
    logger.debug(f"Calcul RSI Wilder({period}) - {len(closes)} prix de clôture")
    logger.debug(f"Prix de clôture: {closes}")
    
    # Utiliser la méthode Wilder
    rsi_wilder = calculate_rsi_wilder(closes, period)
    
    if rsi_wilder is None:
        logger.warning(f"Impossible de calculer RSI Wilder - données insuffisantes")
        return None
    
    logger.debug(f"RSI Wilder({period}): {rsi_wilder}")
    
    # Log JSON détaillé pour debug
    rsi_debug = {
        'period': period,
        'method': 'Wilder',
        'input_closes': closes,
        'rsi_wilder': rsi_wilder
    }
    
    logger.info(f"RSI_CALCULATION_DEBUG: {rsi_debug}")
    
    return rsi_wilder

def has_sufficient_history_for_rsi(candles, period=12):
    """
    Vérifie qu'on a assez d'historique pour calculer le RSI de manière fiable.
    :param candles: liste des bougies
    :param period: période du RSI (par défaut 12)
    :return: (bool, str) - (suffisant, message d'erreur)
    """
    # Total nécessaire : period + 1 pour avoir une valeur valide
    total_needed = period + 1
    
    if len(candles) < total_needed:
        return False, f"Pas assez d'historique pour RSI. Nécessaire: {total_needed}, Disponible: {len(candles)}"
    
    # Vérifier que les dernières bougies ont des valeurs RSI valides
    closes = [float(c['close']) for c in candles]
    rsi = compute_rsi(closes, period)
    
    # Vérifier que le RSI est calculable
    if rsi is None:
        return False, f"RSI pas encore calculable avec {len(closes)} prix de clôture"
    
    return True, f"Historique suffisant pour le trading (RSI({period}) Wilder)"

def get_rsi_with_validation(candles, period=12):
    """
    Calcule le RSI avec validation de l'historique.
    :param candles: liste des bougies
    :param period: période du RSI (par défaut 12)
    :return: (bool, rsi_value, message) - (succès, RSI, message)
    """
    # Vérifier si on a assez de données
    is_valid, message = has_sufficient_history_for_rsi(candles, period)
    if not is_valid:
        return False, None, message
    
    # Calculer le RSI avec les données Kraken
    closes = [float(c['close']) for c in candles]
    rsi = compute_rsi(closes, period)
    return True, rsi, f"RSI({period}) Wilder calculé avec succès"

def compute_normalized_volume(volumes, ma_length=20, smoothing_period=9):
    """
    Calcule le volume normalisé comme Kraken.
    
    :param volumes: liste des volumes (en BTC)
    :param ma_length: longueur de la moyenne mobile (par défaut 20)
    :param smoothing_period: période du lissage SMA (par défaut 9)
    :return: Series du volume normalisé
    """
    logger = logging.getLogger(__name__)
    
    volumes_series = pd.Series(volumes)
    
    # Log des données d'entrée pour debug
    logger.debug(f"Calcul volume normalisé - MA({ma_length}) + SMA({smoothing_period}) - {len(volumes)} volumes")
    logger.debug(f"Volumes bruts: {volumes_series.tolist()}")
    
    # 1. Calculer la moyenne mobile du volume sur ma_length périodes
    volume_ma = volumes_series.rolling(window=ma_length, min_periods=ma_length).mean()
    
    logger.debug(f"Volume MA({ma_length}): {volume_ma.tolist()}")
    
    # 2. Calculer le ratio : Volume actuel / Volume moyen
    volume_ratio = volumes_series / volume_ma
    
    logger.debug(f"Volume ratio: {volume_ratio.tolist()}")
    
    # 3. Appliquer le lissage SMA sur le ratio
    volume_normalized = volume_ratio.rolling(window=smoothing_period, min_periods=smoothing_period).mean()
    
    # 4. Multiplier par 100 pour correspondre à l'affichage Kraken
    volume_normalized = volume_normalized * 100
    
    logger.debug(f"Volume normalisé SMA({smoothing_period}): {volume_normalized.tolist()}")
    
    # Log JSON détaillé pour debug
    volume_debug = {
        'ma_length': ma_length,
        'smoothing_period': smoothing_period,
        'input_volumes': volumes_series.tolist(),
        'volume_ma': volume_ma.tolist(),
        'volume_ratio': volume_ratio.tolist(),
        'volume_normalized': volume_normalized.tolist(),
        'last_5_volumes': volumes_series.tail(5).tolist() if len(volumes_series) >= 5 else volumes_series.tolist(),
        'last_5_normalized': volume_normalized.tail(5).tolist() if len(volume_normalized) >= 5 else volume_normalized.tolist()
    }
    
    logger.info(f"VOLUME_CALCULATION_DEBUG: {volume_debug}")
    
    return volume_normalized

def has_sufficient_history_for_volume(candles, ma_length=20, smoothing_period=9):
    """
    Vérifie qu'on a assez d'historique pour calculer le volume normalisé.
    :param candles: liste des bougies
    :param ma_length: longueur de la moyenne mobile (par défaut 20)
    :param smoothing_period: période du lissage SMA (par défaut 9)
    :return: (bool, str) - (suffisant, message d'erreur)
    """
    # Total nécessaire : ma_length + smoothing_period + 1 pour avoir une valeur valide
    total_needed = ma_length + smoothing_period + 1
    
    if len(candles) < total_needed:
        return False, f"Pas assez d'historique pour volume. Nécessaire: {total_needed}, Disponible: {len(candles)}"
    
    # Vérifier que les dernières bougies ont des valeurs volume valides (pas NaN)
    # Gérer les deux formats : 'volume' (Kraken) et 'volume_normalized' (initial_data.json)
    volumes = []
    for c in candles:
        if 'volume' in c:
            volumes.append(float(c['volume']))
        elif 'volume_normalized' in c:
            # Si c'est déjà normalisé, on l'utilise tel quel
            volumes.append(float(c['volume_normalized']))
        else:
            raise ValueError(f"Champ volume manquant dans la bougie: {c}")
    
    volume_normalized = compute_normalized_volume(volumes, ma_length, smoothing_period)
    
    # Vérifier que les 2 dernières valeurs volume sont valides (pour N-1 et N-2)
    if pd.isna(volume_normalized.iloc[-1]) or pd.isna(volume_normalized.iloc[-2]):
        return False, f"Volume normalisé pas encore calculable. Dernières valeurs: {volume_normalized.iloc[-2:].tolist()}"
    
    return True, f"Historique suffisant pour le volume (MA({ma_length}) + SMA({smoothing_period}))"

def get_volume_with_validation(candles, ma_length=20, smoothing_period=9):
    """
    Calcule le volume normalisé avec validation de l'historique.
    :param candles: liste des bougies
    :param ma_length: longueur de la moyenne mobile (par défaut 20)
    :param smoothing_period: période du lissage SMA (par défaut 9)
    :return: (bool, volume_series, message) - (succès, Volume normalisé, message)
    """
    # Vérifier si on a des données d'initialisation
    if is_initialization_ready():
        logger = logging.getLogger(__name__)
        logger.info("Utilisation des données d'initialisation pour le volume")
        initial_volume = initialization_manager.get_initial_volume_series()
        return True, initial_volume, "Volume initialisé avec données historiques"
    
    # Sinon, calculer normalement
    is_valid, message = has_sufficient_history_for_volume(candles, ma_length, smoothing_period)
    if not is_valid:
        return False, None, message
    
    # Gérer les deux formats : 'volume' (Kraken) et 'volume_normalized' (initial_data.json)
    volumes = []
    for c in candles:
        if 'volume' in c:
            volumes.append(float(c['volume']))
        elif 'volume_normalized' in c:
            # Si c'est déjà normalisé, on l'utilise tel quel
            volumes.append(float(c['volume_normalized']))
        else:
            raise ValueError(f"Champ volume manquant dans la bougie: {c}")
    
    volume_normalized = compute_normalized_volume(volumes, ma_length, smoothing_period)
    return True, volume_normalized, f"Volume MA({ma_length}) + SMA({smoothing_period}) calculé avec succès"

# Exemple d'utilisation
if __name__ == "__main__":
    # Données fictives pour test
    closes = [100, 102, 101, 105, 107, 110, 108, 109, 111, 115, 117, 120, 119, 121, 123, 125]
    rsi = compute_rsi(closes, period=12)
    print("RSI(12) :")
    print(rsi)
    
    # Test de validation
    candles = [{'close': c} for c in closes]
    is_valid, message = has_sufficient_history_for_rsi(candles, 12)
    print(f"\nValidation: {is_valid} - {message}") 