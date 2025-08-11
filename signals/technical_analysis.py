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
    # VALIDATION DES DONNÉES D'ENTRÉE - PROTECTION CONTRE LES CRASHES
    if not candles or len(candles) < 2:
        logger.log_error("analyze_candles: candles est None, vide ou trop court")
        raise ValueError("Il faut au moins 2 bougies pour détecter les croisements")
    
    if not indicators:
        logger.log_error("analyze_candles: indicators est None ou vide")
        raise ValueError("Indicateurs requis pour l'analyse")
    
    # Vérifier que les clés essentielles existent dans indicators
    required_indicator_keys = ['RSI', 'vi1', 'vi2', 'vi3']
    missing_keys = [key for key in required_indicator_keys if key not in indicators]
    
    if missing_keys:
        logger.log_error(f"analyze_candles: Clés manquantes dans indicators: {missing_keys}")
        raise ValueError(f"Indicateurs incomplets - clés manquantes: {missing_keys}")
    
    # Utiliser les 2 dernières bougies pour détecter les croisements
    current_candle = candles[-1]    # Bougie N-1 (actuelle)
    previous_candle = candles[-2]    # Bougie N-2 (précédente)
    
    # Vérifier que les bougies ont les bonnes clés
    if 'close' not in current_candle or 'close' not in previous_candle:
        logger.log_error("analyze_candles: current_candle ou previous_candle n'a pas de clé 'close'")
        raise ValueError("Bougies incomplètes - clé close manquante")
    
    # RSI actuel
    rsi = float(indicators['RSI'])
    
    # Volatility Indexes actuels (nouvelle logique - utiliser les vraies valeurs)
    vi1 = float(indicators['vi1'])
    vi2 = float(indicators['vi2'])
    vi3 = float(indicators['vi3'])
    
    # Prix de clôture des 2 bougies
    current_close = float(current_candle['close'])
    previous_close = float(previous_candle['close'])
    
    # Positions des VI par rapport au close ACTUEL (conditions statiques)
    vi1_above_close = vi1 > current_close
    vi2_above_close = vi2 > current_close
    vi3_above_close = vi3 > current_close
    
    # DÉTECTION DES VRAIS CROISEMENTS (comparaison 2 bougies)
    # On utilise les indicateurs des 2 bougies pour détecter les croisements
    vi1_current_above = vi1 > current_close
    vi1_previous_above = vi1 > previous_close
    
    vi2_current_above = vi2 > current_close
    vi2_previous_above = vi2 > previous_close
    
    # Croisements VI1
    vi1_crossing_over = vi1_previous_above == False and vi1_current_above == True   # VI1 traverse vers le haut
    vi1_crossing_under = vi1_previous_above == True and vi1_current_above == False  # VI1 traverse vers le bas
    
    # Croisements VI2
    vi2_crossing_over = vi2_previous_above == False and vi2_current_above == True   # VI2 traverse vers le haut
    vi2_crossing_under = vi2_previous_above == True and vi2_current_above == False  # VI2 traverse vers le bas
    
    # NOUVELLE LOGIQUE - Phases VI
    vi1_phase = indicators.get('VI1_phase', 'BULLISH')  # Par défaut BULLISH
    vi2_phase = indicators.get('VI2_phase', 'BULLISH')  # Par défaut BULLISH
    vi3_phase = indicators.get('VI3_phase', 'BULLISH')  # Par défaut BULLISH
    
    # Analyse complète
    analysis = {
        # Données de la bougie actuelle
        'current_candle': current_candle,
        'rsi': rsi,
        'current_close': current_close,
        
        # Volatility Indexes (anciennes valeurs pour compatibilité)
        'vi1': vi1,
        'vi2': vi2,
        'vi3': vi3,
        
        # NOUVELLE LOGIQUE - Phases VI
        'vi1_phase': vi1_phase,
        'vi2_phase': vi2_phase,
        'vi3_phase': vi3_phase,
        
        # Positions des VI par rapport au close
        'vi1_above_close': vi1_above_close,
        'vi2_above_close': vi2_above_close,
        'vi3_above_close': vi3_above_close,
        
        # Conditions pour SHORT
        'short_conditions': {
            'vi1_crossing_over': vi1_crossing_over,      # ✅ DÉCLENCHEUR: VI1 traverse le close vers le haut
            'vi2_above_close': vi2_above_close,           # ✅ CONDITION: VI2 est au-dessus du close
            'vi3_above_close': vi3_above_close,           # ✅ CONDITION: VI3 est au-dessus du close
            'rsi_condition': rsi <= 50,                   # ✅ CONDITION: RSI ≤ 50
            # NOUVELLE LOGIQUE - Phases VI
            'vi1_phase_bearish': vi1_phase == 'BEARISH',  # ✅ CONDITION: VI1 en phase BEARISH
            'vi2_phase_bearish': vi2_phase == 'BEARISH',  # ✅ CONDITION: VI2 en phase BEARISH
            'vi3_phase_bearish': vi3_phase == 'BEARISH'   # ✅ CONDITION: VI3 en phase BEARISH
        },
        
        # Conditions pour LONG_VI1
        'long_vi1_conditions': {
            'vi1_crossing_under': vi1_crossing_under,    # ✅ DÉCLENCHEUR: VI1 traverse le close vers le bas
            'vi2_above_close': not vi2_above_close,       # ✅ CONDITION: VI2 est en-dessous du close
            'vi3_above_close': not vi3_above_close,       # ✅ CONDITION: VI3 est en-dessous du close
            'rsi_condition': rsi >= 45,                   # ✅ CONDITION: RSI ≥ 45
            # NOUVELLE LOGIQUE - Phases VI
            'vi1_phase_bullish': vi1_phase == 'BULLISH',  # ✅ CONDITION: VI1 en phase BULLISH
            'vi2_phase_bullish': vi2_phase == 'BULLISH',  # ✅ CONDITION: VI2 en phase BULLISH
            'vi3_phase_bullish': vi3_phase == 'BULLISH'   # ✅ CONDITION: VI3 en phase BULLISH
        },
        
        # Conditions pour LONG_VI2
        'long_vi2_conditions': {
            'vi1_already_under': not vi1_above_close,     # ✅ CONDITION: VI1 est déjà en-dessous du close
            'vi2_crossing_under': vi2_crossing_under,     # ✅ DÉCLENCHEUR: VI2 traverse le close vers le bas
            'rsi_condition': rsi >= 45,                   # ✅ CONDITION: RSI ≥ 45
            # NOUVELLE LOGIQUE - Phases VI
            'vi1_phase_bullish': vi1_phase == 'BULLISH',  # ✅ CONDITION: VI1 en phase BULLISH
            'vi2_phase_bullish': vi2_phase == 'BULLISH'   # ✅ CONDITION: VI2 en phase BULLISH
        },
        
        # Conditions pour LONG_REENTRY
        'long_reentry_conditions': {
            'vi1_not_crossed_over': not vi1_above_close,  # ✅ CONDITION: VI1 pas encore repassé au-dessus
            'vi3_under_close': not vi3_above_close,       # ✅ CONDITION: VI3 est sous le close
            'vi2_above_close': vi2_above_close,           # ✅ CONDITION: VI2 est au-dessus du close
            'vi2_crossing_under': vi2_crossing_under,     # ✅ DÉCLENCHEUR: VI2 traverse le close vers le bas
            'rsi_condition': rsi >= 45,                    # ✅ CONDITION: RSI ≥ 45
            # NOUVELLE LOGIQUE - Phases VI
            'vi1_phase_bullish': vi1_phase == 'BULLISH',  # ✅ CONDITION: VI1 en phase BULLISH
            'vi2_phase_bullish': vi2_phase == 'BULLISH',  # ✅ CONDITION: VI2 en phase BULLISH
            'vi3_phase_bullish': vi3_phase == 'BULLISH'   # ✅ CONDITION: VI3 en phase BULLISH
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
    summary.append(f"   Close: {analysis['current_close']:.2f}")
    
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