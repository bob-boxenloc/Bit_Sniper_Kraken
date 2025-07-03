import pandas as pd
import logging

def compute_rsi(closes, period=12):
    """
    Calcule le RSI sur une liste de prix de clôture.
    :param closes: liste ou Series de prix de clôture
    :param period: période du RSI (par défaut 12)
    :return: Series du RSI
    """
    logger = logging.getLogger(__name__)
    
    closes = pd.Series(closes)
    
    # Log des données d'entrée pour debug
    logger.debug(f"Calcul RSI({period}) - {len(closes)} prix de clôture")
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
    rsi = 100 - (100 / (1 + rs))
    
    # Log du RSI final pour debug
    logger.debug(f"RS final: {rs.tolist()}")
    logger.debug(f"RSI final: {rsi.tolist()}")
    
    # Log JSON détaillé pour debug
    rsi_debug = {
        'period': period,
        'input_closes': closes.tolist(),
        'deltas': delta.tolist(),
        'gains': gain.tolist(),
        'losses': loss.tolist(),
        'avg_gains': avg_gain.tolist(),
        'avg_losses': avg_loss.tolist(),
        'rs_values': rs.tolist(),
        'rsi_values': rsi.tolist(),
        'last_5_rsi': rsi.tail(5).tolist() if len(rsi) >= 5 else rsi.tolist()
    }
    
    logger.info(f"RSI_CALCULATION_DEBUG: {rsi_debug}")
    
    return rsi

def has_sufficient_history_for_rsi(candles, period=12):
    """
    Vérifie qu'on a assez d'historique pour calculer le RSI de manière fiable.
    :param candles: liste des bougies
    :param period: période du RSI (par défaut 12)
    :return: (bool, str) - (suffisant, message d'erreur)
    """
    if len(candles) < period + 1:
        return False, f"Pas assez d'historique. Nécessaire: {period + 1}, Disponible: {len(candles)}"
    
    # Vérifier que les dernières bougies ont des valeurs RSI valides (pas NaN)
    closes = [float(c['close']) for c in candles]
    rsi = compute_rsi(closes, period)
    
    # Vérifier que les 2 dernières valeurs RSI sont valides (pour N-1 et N-2)
    if pd.isna(rsi.iloc[-1]) or pd.isna(rsi.iloc[-2]):
        return False, f"RSI pas encore calculable. Dernières valeurs: {rsi.iloc[-2:].tolist()}"
    
    return True, "Historique suffisant pour le trading"

def get_rsi_with_validation(candles, period=12):
    """
    Calcule le RSI avec validation de l'historique.
    :param candles: liste des bougies
    :param period: période du RSI (par défaut 12)
    :return: (bool, rsi_series, message) - (succès, RSI, message)
    """
    is_valid, message = has_sufficient_history_for_rsi(candles, period)
    if not is_valid:
        return False, None, message
    
    closes = [float(c['close']) for c in candles]
    rsi = compute_rsi(closes, period)
    return True, rsi, "RSI calculé avec succès"

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