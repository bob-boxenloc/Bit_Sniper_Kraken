"""
Module d'analyse technique pour BitSniper
Calcule tous les indicateurs nécessaires pour la nouvelle stratégie de trading
"""

from core.logger import logger

def analyze_candles(candles, indicators):
    """
    Analyse complète des bougies pour la nouvelle stratégie de trading.
    
    :param candles: liste des bougies (format Kraken Futures API)
                   chaque bougie = {'time', 'open', 'high', 'low', 'close', 'volume', 'count', 'datetime'}
    :param indicators: dict avec RSI et Volatility Indexes calculés
    :return: dict avec tous les indicateurs calculés et conditions
    """
    if len(candles) < 2:
        raise ValueError("Il faut au moins 2 bougies pour l'analyse")
    
    # IMPORTANT: Utiliser les bougies Kraken temps réel pour les décisions
    # Les 2 dernières bougies de la liste sont les bougies Kraken temps réel
    candle_n1 = candles[-1]  # Dernière bougie Kraken temps réel
    candle_n2 = candles[-2]  # Avant-dernière bougie Kraken temps réel
    
    # RSI actuel
    rsi = float(indicators['RSI'])
    
    # Volatility Indexes actuels
    vi1 = float(indicators['VI1'])
    vi2 = float(indicators['VI2'])
    vi3 = float(indicators['VI3'])
    
    # Prix de clôture des bougies Kraken temps réel
    close_n1 = float(candle_n1['close'])
    close_n2 = float(candle_n2['close'])
    
    # Positions des VI par rapport au close
    vi1_above_close = vi1 > close_n1
    vi2_above_close = vi2 > close_n1
    vi3_above_close = vi3 > close_n1
    
    # Analyse complète
    analysis = {
        # Données brutes (bougies Kraken temps réel)
        'candle_n1': candle_n1,
        'candle_n2': candle_n2,
        'rsi': rsi,
        'close_n1': close_n1,
        'close_n2': close_n2,
        
        # Volatility Indexes
        'vi1': vi1,
        'vi2': vi2,
        'vi3': vi3,
        
        # Positions des VI par rapport au close
        'vi1_above_close': vi1_above_close,
        'vi2_above_close': vi2_above_close,
        'vi3_above_close': vi3_above_close,
        
        # Conditions pour SHORT
        'short_conditions': {
            'vi1_crossing_over': vi1_above_close,  # VI1 au-dessus du close
            'vi2_above_close': vi2_above_close,     # VI2 au-dessus du close
            'vi3_above_close': vi3_above_close,     # VI3 au-dessus du close
            'rsi_condition': rsi <= 50              # RSI ≤ 50
        },
        
        # Conditions pour LONG_VI1
        'long_vi1_conditions': {
            'vi1_crossing_under': not vi1_above_close,  # VI1 en-dessous du close
            'vi2_above_close': not vi2_above_close,     # VI2 en-dessous du close
            'vi3_above_close': not vi3_above_close,     # VI3 en-dessous du close
            'rsi_condition': rsi >= 45                   # RSI ≥ 45
        },
        
        # Conditions pour LONG_VI2
        'long_vi2_conditions': {
            'vi1_already_under': not vi1_above_close,   # VI1 déjà en-dessous du close
            'vi2_crossing_under': not vi2_above_close,  # VI2 crossing-under
            'rsi_condition': rsi >= 45                   # RSI ≥ 45
        },
        
        # Conditions pour LONG_REENTRY
        'long_reentry_conditions': {
            'vi1_not_crossed_over': not vi1_above_close,  # VI1 pas encore repassé au-dessus
            'vi3_under_close': not vi3_above_close,       # VI3 sous le close
            'vi2_above_close': vi2_above_close,           # VI2 au-dessus du close
            'vi2_crossing_under': not vi2_above_close,    # VI2 crossing-under
            'rsi_condition': rsi >= 45                     # RSI ≥ 45
        }
    }
    
    return analysis

def check_all_conditions(analysis, last_position_type=None, vi1_phase_timestamp=None):
    """
    Vérifie toutes les conditions pour chaque stratégie.
    
    :param analysis: dict retourné par analyze_candles()
    :param last_position_type: type de la dernière position (pour LONG_REENTRY)
    :param vi1_phase_timestamp: timestamp du dernier changement de phase VI1
    :return: dict avec les résultats des vérifications
    """
    import time
    
    short_conditions = analysis['short_conditions']
    long_vi1_conditions = analysis['long_vi1_conditions']
    long_vi2_conditions = analysis['long_vi2_conditions']
    long_reentry_conditions = analysis['long_reentry_conditions']
    
    # Vérification de la règle de protection temporelle VI1 (72h)
    vi1_protection_active = False
    if vi1_phase_timestamp is not None:
        current_time = time.time()
        time_elapsed = current_time - vi1_phase_timestamp
        vi1_protection_active = time_elapsed < 259200  # 72h en secondes
        
        if vi1_protection_active:
            hours_remaining = (259200 - time_elapsed) / 3600
            logger.log_protection_activation("VI1 (72h)", f"Protection active, {hours_remaining:.1f}h restantes")
    
    # Vérification SHORT
    short_ready = all(short_conditions.values())
    if vi1_protection_active and analysis['vi1_above_close']:
        short_ready = False  # Interdire SHORT si protection active
        logger.log_protection_activation("SHORT", "Bloqué par protection VI1 (72h)")
    
    # Vérification LONG_VI1
    long_vi1_ready = all(long_vi1_conditions.values())
    if vi1_protection_active and not analysis['vi1_above_close']:
        long_vi1_ready = False  # Interdire LONGS si protection active
        logger.log_protection_activation("LONG_VI1", "Bloqué par protection VI1 (72h)")
    
    # Vérification LONG_VI2
    long_vi2_ready = all(long_vi2_conditions.values())
    if vi1_protection_active and not analysis['vi1_above_close']:
        long_vi2_ready = False  # Interdire LONGS si protection active
        logger.log_protection_activation("LONG_VI2", "Bloqué par protection VI1 (72h)")
    
    # Vérification LONG_REENTRY
    long_reentry_ready = all(long_reentry_conditions.values())
    if last_position_type == "LONG_REENTRY":
        long_reentry_ready = False  # Interdire LONG_REENTRY consécutif
        logger.log_protection_activation("LONG_REENTRY", "Bloqué: LONG_REENTRY consécutif interdit")
    if vi1_protection_active and not analysis['vi1_above_close']:
        long_reentry_ready = False  # Interdire LONGS si protection active
        logger.log_protection_activation("LONG_REENTRY", "Bloqué par protection VI1 (72h)")
    
    return {
        'trading_allowed': True,
        'reason': 'Conditions normales',
        'short_ready': short_ready,
        'long_vi1_ready': long_vi1_ready,
        'long_vi2_ready': long_vi2_ready,
        'long_reentry_ready': long_reentry_ready,
        'vi1_protection_active': vi1_protection_active,
        'details': {
            'short': short_conditions,
            'long_vi1': long_vi1_conditions,
            'long_vi2': long_vi2_conditions,
            'long_reentry': long_reentry_conditions
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
    summary.append("📊 ANALYSE TECHNIQUE (nouvelle stratégie):")
    summary.append(f"   RSI: {analysis['rsi']:.2f}")
    summary.append(f"   VI1: {analysis['vi1']:.2f} ({'au-dessus' if analysis['vi1_above_close'] else 'en-dessous'} du close)")
    summary.append(f"   VI2: {analysis['vi2']:.2f} ({'au-dessus' if analysis['vi2_above_close'] else 'en-dessous'} du close)")
    summary.append(f"   VI3: {analysis['vi3']:.2f} ({'au-dessus' if analysis['vi3_above_close'] else 'en-dessous'} du close)")
    summary.append(f"   Close: {analysis['close_n1']:.2f}")
    
    if conditions_check['vi1_protection_active']:
        summary.append("   ⚠️ PROTECTION VI1 ACTIVE (72h)")
    
    summary.append("   ✅ TRADING AUTORISÉ")
    if conditions_check['short_ready']:
        summary.append("   🟢 SHORT: Conditions remplies")
    if conditions_check['long_vi1_ready']:
        summary.append("   🟢 LONG_VI1: Conditions remplies")
    if conditions_check['long_vi2_ready']:
        summary.append("   🟢 LONG_VI2: Conditions remplies")
    if conditions_check['long_reentry_ready']:
        summary.append("   🟢 LONG_REENTRY: Conditions remplies")
    
    if not any([conditions_check['short_ready'], conditions_check['long_vi1_ready'], 
                conditions_check['long_vi2_ready'], conditions_check['long_reentry_ready']]):
        summary.append("   ⚪ Aucune stratégie prête")
    
    return "\n".join(summary)

# Test du module
if __name__ == "__main__":
    # Données de test
    test_candles = [
        {'close': 40000, 'high': 40100, 'low': 39900},   # N-2
        {'close': 40100, 'high': 40200, 'low': 40000}    # N-1
    ]
    
    # Indicateurs fictifs pour test
    test_indicators = {
        'RSI': 55.0,
        'VI1': 40200,
        'VI2': 40150,
        'VI3': 40100
    }
    
    analysis = analyze_candles(test_candles, test_indicators)
    conditions = check_all_conditions(analysis)
    summary = get_analysis_summary(analysis, conditions)
    
    print(summary) 