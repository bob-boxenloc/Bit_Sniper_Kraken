"""
Module d'analyse technique pour BitSniper
Calcule tous les indicateurs nécessaires pour la stratégie de trading
"""

def analyze_candles(candles, rsi_series):
    """
    Analyse complète des bougies pour la stratégie de trading.
    
    :param candles: liste des bougies (format Kraken Futures API)
                   chaque bougie = {'time', 'open', 'high', 'low', 'close', 'volume', 'count', 'datetime'}
    :param rsi_series: Series pandas du RSI calculé
    :return: dict avec tous les indicateurs calculés
    """
    if len(candles) < 2:
        raise ValueError("Il faut au moins 2 bougies pour l'analyse")
    
    # IMPORTANT: Utiliser les bougies Kraken temps réel pour les décisions
    # Les 2 dernières bougies de la liste sont les bougies Kraken temps réel
    candle_n1 = candles[-1]  # Dernière bougie Kraken temps réel
    candle_n2 = candles[-2]  # Avant-dernière bougie Kraken temps réel
    
    # RSI N-1 et N-2 (calculé avec toutes les données mais utilisé sur les bougies Kraken)
    rsi_n1 = float(rsi_series.iloc[-1])
    rsi_n2 = float(rsi_series.iloc[-2])
    
    # Nombre de trades (count) des bougies Kraken temps réel
    count_n1 = int(candle_n1['count'])
    count_n2 = int(candle_n2['count'])
    
    # Prix de clôture des bougies Kraken temps réel
    close_n1 = float(candle_n1['close'])
    close_n2 = float(candle_n2['close'])
    
    # Calculs dérivés
    delta_count = count_n1 / count_n2 if count_n2 > 0 else 0
    rsi_change = rsi_n1 - rsi_n2  # Variation du RSI
    
    # Analyse complète
    analysis = {
        # Données brutes (bougies Kraken temps réel)
        'candle_n1': candle_n1,
        'candle_n2': candle_n2,
        'rsi_n1': rsi_n1,
        'rsi_n2': rsi_n2,
        'count_n1': count_n1,
        'count_n2': count_n2,
        'close_n1': close_n1,
        'close_n2': close_n2,
        
        # Calculs dérivés
        'delta_count': delta_count,
        'rsi_change': rsi_change,
        
        # Conditions pour long1
        'long1_conditions': {
            'count_sufficient': count_n1 >= 90,
            'rsi_n2_in_range': 10 <= rsi_n2 <= 26,
            'rsi_increasing': rsi_change >= 4,
            'rsi_n1_below_40': rsi_n1 < 40,
            'delta_count_in_range': 0.3 <= delta_count <= 1.8
        },
        
        # Conditions pour long2
        'long2_conditions': {
            'count_sufficient': count_n1 >= 90,
            'count_increasing': count_n1 > count_n2,
            'delta_count_in_range': delta_count > 1,
            'rsi_n2_in_range': 72 <= rsi_n2 <= 86,
            'rsi_decreasing': rsi_change <= -2.5
        },
        
        # Conditions pour short
        'short_conditions': {
            'count_sufficient': count_n1 >= 90,
            'count_decreasing': count_n1 < count_n2,
            'delta_count_in_range': 0.7 <= delta_count < 1,
            'rsi_n2_in_range': 72 <= rsi_n2 <= 83,
            'rsi_decreasing': rsi_change <= -3.5,
            'rsi_n1_above_60': rsi_n1 > 60
        },
        
        # Règle générale de sécurité (extrêmes RSI)
        'safety_rule': {
            'rsi_extreme_high': rsi_n1 > 86,
            'rsi_extreme_low': rsi_n1 < 10,
            'rsi_passed_50': 10 <= rsi_n1 <= 86  # RSI dans la zone "normale"
        }
    }
    
    return analysis

def check_all_conditions(analysis):
    """
    Vérifie toutes les conditions pour chaque stratégie.
    
    :param analysis: dict retourné par analyze_candles()
    :return: dict avec les résultats des vérifications
    """
    long1_conditions = analysis['long1_conditions']
    long2_conditions = analysis['long2_conditions']
    short_conditions = analysis['short_conditions']
    safety_rule = analysis['safety_rule']
    
    # Vérification de la règle de sécurité
    if safety_rule['rsi_extreme_high'] or safety_rule['rsi_extreme_low']:
        # RSI en zone extrême, trading bloqué
        return {
            'trading_allowed': False,
            'reason': 'RSI en zone extrême (RSI < 10 ou RSI > 86)',
            'long1_ready': False,
            'long2_ready': False,
            'short_ready': False
        }
    
    # Vérification long1 (toutes les conditions doivent être vraies)
    long1_ready = all(long1_conditions.values())
    
    # Vérification long2 (toutes les conditions doivent être vraies)
    long2_ready = all(long2_conditions.values())
    
    # Vérification short (toutes les conditions doivent être vraies)
    short_ready = all(short_conditions.values())
    
    return {
        'trading_allowed': True,
        'reason': 'Conditions normales',
        'long1_ready': long1_ready,
        'long2_ready': long2_ready,
        'short_ready': short_ready,
        'details': {
            'long1': long1_conditions,
            'long2': long2_conditions,
            'short': short_conditions
        }
    }

def get_analysis_summary(analysis, conditions_check):
    """
    Génère un résumé lisible de l'analyse.
    
    :param analysis: dict retourné par analyze_candles()
    :param conditions_check: dict retourné par check_all_conditions()
    :return: str avec le résumé
    """
    summary = []
    summary.append("📊 ANALYSE TECHNIQUE (bougies Kraken temps réel):")
    summary.append(f"   RSI N-2: {analysis['rsi_n2']:.2f}")
    summary.append(f"   RSI N-1: {analysis['rsi_n1']:.2f}")
    summary.append(f"   Variation RSI: {analysis['rsi_change']:+.2f}")
    summary.append(f"   Trades N-2 (count): {analysis['count_n2']}")
    summary.append(f"   Trades N-1 (count): {analysis['count_n1']}")
    summary.append(f"   Delta Trades: {analysis['delta_count']:.3f}")
    
    if not conditions_check['trading_allowed']:
        summary.append(f"   ❌ TRADING BLOQUÉ: {conditions_check['reason']}")
    else:
        summary.append("   ✅ TRADING AUTORISÉ")
        if conditions_check['long1_ready']:
            summary.append("   🟢 LONG1: Conditions remplies")
        if conditions_check['long2_ready']:
            summary.append("   🟢 LONG2: Conditions remplies")
        if conditions_check['short_ready']:
            summary.append("   🟢 SHORT: Conditions remplies")
        
        if not any([conditions_check['long1_ready'], conditions_check['long2_ready'], conditions_check['short_ready']]):
            summary.append("   ⚪ Aucune stratégie prête")
    
    return "\n".join(summary)

# Test du module
if __name__ == "__main__":
    # Données de test
    test_candles = [
        {'close': 40000, 'volume': 50, 'count': 10},   # N-2
        {'close': 40100, 'volume': 95, 'count': 20}    # N-1
    ]
    
    # RSI fictif pour test
    import pandas as pd
    test_rsi = pd.Series([25.0, 29.0])  # RSI N-2=25, N-1=29
    
    analysis = analyze_candles(test_candles, test_rsi)
    conditions = check_all_conditions(analysis)
    summary = get_analysis_summary(analysis, conditions)
    
    print(summary) 