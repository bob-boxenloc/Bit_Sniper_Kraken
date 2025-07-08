import pandas as pd
import logging
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

def compute_rsi(closes, period=12):
    """
    Calcule le RSI selon la méthode Wilder (comme Kraken).
    
    :param closes: liste ou Series de prix de clôture
    :param period: période du RSI (par défaut 12)
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

# Test du module
if __name__ == "__main__":
    # Données fictives pour test
    closes = [100, 102, 101, 105, 107, 110, 108, 109, 111, 115, 117, 120, 119, 121, 123, 125]
    rsi = compute_rsi(closes, period=12)
    print("RSI(12) Wilder :")
    print(rsi)
    
    # Test de validation
    candles = [{'close': c} for c in closes]
    is_valid, message = has_sufficient_history_for_rsi(candles, 12)
    print(f"\nValidation: {is_valid} - {message}") 