import pandas as pd
import logging

def compute_rsi(closes, period=12, smoothing_period=14):
    """
    Calcule le RSI sur une liste de prix de clôture avec lissage SMA.
    
    :param closes: liste ou Series de prix de clôture
    :param period: période du RSI (par défaut 12)
    :param smoothing_period: période du lissage SMA sur le RSI (par défaut 14)
    :return: Series du RSI lissé
    """
    logger = logging.getLogger(__name__)
    
    closes = pd.Series(closes)
    
    # Log des données d'entrée pour debug
    logger.debug(f"Calcul RSI({period}) avec lissage SMA({smoothing_period}) - {len(closes)} prix de clôture")
    logger.debug(f"Prix de clôture: {closes.tolist()}")
    
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    # Log des variations pour debug
    logger.debug(f"Variations (delta): {delta.tolist()}")
    logger.debug(f"Gains: {gain.tolist()}")
    logger.debug(f"Pertes: {loss.tolist()}")
    
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    # Log des moyennes pour debug
    logger.debug(f"Moyenne gains: {avg_gain.tolist()}")
    logger.debug(f"Moyenne pertes: {avg_loss.tolist()}")
    
    rs = avg_gain / avg_loss
    rsi_brut = 100 - (100 / (1 + rs))
    
    # Log du RSI brut pour debug
    logger.debug(f"RS final: {rs.tolist()}")
    logger.debug(f"RSI brut: {rsi_brut.tolist()}")
    
    # APPLIQUER LE LISSAGE SMA(14) SUR LE RSI (comme Kraken)
    rsi_lisse = rsi_brut.rolling(window=smoothing_period, min_periods=smoothing_period).mean()
    
    logger.debug(f"RSI lissé SMA({smoothing_period}): {rsi_lisse.tolist()}")
    
    # Log JSON détaillé pour debug
    rsi_debug = {
        'period': period,
        'smoothing_period': smoothing_period,
        'input_closes': closes.tolist(),
        'deltas': delta.tolist(),
        'gains': gain.tolist(),
        'losses': loss.tolist(),
        'avg_gains': avg_gain.tolist(),
        'avg_losses': avg_loss.tolist(),
        'rs_values': rs.tolist(),
        'rsi_brut': rsi_brut.tolist(),
        'rsi_lisse': rsi_lisse.tolist(),
        'last_5_rsi_brut': rsi_brut.tail(5).tolist() if len(rsi_brut) >= 5 else rsi_brut.tolist(),
        'last_5_rsi_lisse': rsi_lisse.tail(5).tolist() if len(rsi_lisse) >= 5 else rsi_lisse.tolist()
    }
    
    logger.info(f"RSI_CALCULATION_DEBUG: {rsi_debug}")
    
    return rsi_lisse

def has_sufficient_history_for_rsi(candles, period=12, smoothing_period=14):
    """
    Vérifie qu'on a assez d'historique pour calculer le RSI de manière fiable.
    :param candles: liste des bougies
    :param period: période du RSI (par défaut 12)
    :param smoothing_period: période du lissage SMA (par défaut 14)
    :return: (bool, str) - (suffisant, message d'erreur)
    """
    # Total nécessaire : period + smoothing_period + 1 pour avoir une valeur valide
    total_needed = period + smoothing_period + 1
    
    if len(candles) < total_needed:
        return False, f"Pas assez d'historique. Nécessaire: {total_needed}, Disponible: {len(candles)}"
    
    # Vérifier que les dernières bougies ont des valeurs RSI valides (pas NaN)
    closes = [float(c['close']) for c in candles]
    rsi = compute_rsi(closes, period, smoothing_period)
    
    # Vérifier que les 2 dernières valeurs RSI sont valides (pour N-1 et N-2)
    if pd.isna(rsi.iloc[-1]) or pd.isna(rsi.iloc[-2]):
        return False, f"RSI pas encore calculable. Dernières valeurs: {rsi.iloc[-2:].tolist()}"
    
    return True, f"Historique suffisant pour le trading (RSI({period}) + SMA({smoothing_period}))"

def get_rsi_with_validation(candles, period=12, smoothing_period=14):
    """
    Calcule le RSI avec validation de l'historique.
    :param candles: liste des bougies
    :param period: période du RSI (par défaut 12)
    :param smoothing_period: période du lissage SMA (par défaut 14)
    :return: (bool, rsi_series, message) - (succès, RSI, message)
    """
    is_valid, message = has_sufficient_history_for_rsi(candles, period, smoothing_period)
    if not is_valid:
        return False, None, message
    
    closes = [float(c['close']) for c in candles]
    rsi = compute_rsi(closes, period, smoothing_period)
    return True, rsi, f"RSI({period}) + SMA({smoothing_period}) calculé avec succès"

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
    volumes = [float(c['volume']) for c in candles]
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
    is_valid, message = has_sufficient_history_for_volume(candles, ma_length, smoothing_period)
    if not is_valid:
        return False, None, message
    
    volumes = [float(c['volume']) for c in candles]
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