import pandas as pd

def compute_rsi(closes, period=12):
    """
    Calcule le RSI sur une liste de prix de clôture.
    :param closes: liste ou Series de prix de clôture
    :param period: période du RSI (par défaut 12)
    :return: Series du RSI
    """
    closes = pd.Series(closes)
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
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