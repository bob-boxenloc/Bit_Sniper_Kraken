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
    required_indicator_keys = ['RSI', 'VI1', 'VI2', 'VI3']
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
    vi1 = float(indicators['VI1'])  # ✅ CORRECTION : Utiliser la clé correcte
    vi2 = float(indicators['VI2'])  # ✅ CORRECTION : Utiliser la clé correcte
    vi3 = float(indicators['VI3'])  # ✅ CORRECTION : Utiliser la clé correcte
    
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
    vi1_phase = indicators.get('VI1_phase', 'BEARISH')  # Par défaut BEARISH
    vi2_phase = indicators.get('VI2_phase', 'BEARISH')  # Par défaut BEARISH
    vi3_phase = indicators.get('VI3_phase', 'BEARISH')  # Par défaut BEARISH
    
    # Analyse complète
    analysis = {
        # Données de la bougie actuelle
        'current_candle': current_candle,
        'rsi': rsi,
        'current_close': current_close,
        
        # Volatility Indexes (anciennes valeurs pour compatibilité)
        'VI1': vi1,
        'VI2': vi2,
        'VI3': vi3,
        
        # NOUVELLE LOGIQUE - Phases VI
        'vi1_phase': vi1_phase,
        'vi2_phase': vi2_phase,
        'vi3_phase': vi3_phase,
        
        # Positions des VI par rapport au close
        'vi1_above_close': vi1_above_close,
        'vi2_above_close': vi2_above_close,
        'vi3_above_close': vi3_above_close,
        
        # DÉTECTION DES CROISEMENTS - Exposés directement pour les notifications
        'vi1_crossing_over': vi1_crossing_over,      # VI1 traverse le close vers le haut
        'vi1_crossing_under': vi1_crossing_under,    # VI1 traverse le close vers le bas
        'vi2_crossing_over': vi2_crossing_over,      # VI2 traverse le close vers le haut
        'vi2_crossing_under': vi2_crossing_under,    # VI2 traverse le close vers le bas
        
        # Conditions pour SHORT
        'short_conditions': {
            'vi1_crossing_over': vi1_crossing_over,      # ✅ DÉCLENCHEUR: VI1 traverse le close vers le haut
            'rsi_condition': rsi <= 50,                   # ✅ CONDITION: RSI ≤ 50
            'vi2_phase_bearish': vi2_phase == 'BEARISH',  # ✅ CONDITION: VI2 en phase BEARISH
            'vi3_phase_bearish': vi3_phase == 'BEARISH'   # ✅ CONDITION: VI3 en phase BEARISH
        },
        
        # Conditions pour LONG_VI1
        'long_vi1_conditions': {
            'vi1_crossing_under': vi1_crossing_under,    # ✅ DÉCLENCHEUR: VI1 traverse le close vers le bas
            'rsi_condition': rsi >= 45,                   # ✅ CONDITION: RSI ≥ 45
            'vi2_phase_bullish': vi2_phase == 'BULLISH',  # ✅ CONDITION: VI2 en phase BULLISH
            'vi3_phase_bullish': vi3_phase == 'BULLISH'   # ✅ CONDITION: VI3 en phase BULLISH
        },
        
        # Conditions pour LONG_VI2
        'long_vi2_conditions': {
            'vi2_crossing_under': vi2_crossing_under,     # ✅ DÉCLENCHEUR: VI2 traverse le close vers le bas
            'rsi_condition': rsi >= 45,                   # ✅ CONDITION: RSI ≥ 45
            'vi1_phase_bullish': vi1_phase == 'BULLISH'   # ✅ CONDITION: VI1 en phase BULLISH
        },
        
        # Conditions pour LONG_REENTRY
        'long_reentry_conditions': {
            'vi2_crossing_under': vi2_crossing_under,     # ✅ DÉCLENCHEUR: VI2 traverse le close vers le bas
            'rsi_condition': rsi >= 45,                    # ✅ CONDITION: RSI ≥ 45
            'vi1_phase_bullish': vi1_phase == 'BULLISH',  # ✅ CONDITION: VI1 en phase BULLISH
            'vi3_phase_bullish': vi3_phase == 'BULLISH'   # ✅ CONDITION: VI3 en phase BULLISH
        }
    }
    
    return analysis

def check_all_conditions(analysis, last_position_type=None, vi1_phase_timestamp=None, vi1_current_phase=None, account_summary=None):
    """
    Vérifie toutes les conditions pour chaque stratégie.
    
    :param analysis: dict retourné par analyze_candles()
    :param last_position_type: type de la dernière position (pour LONG_REENTRY)
    :param vi1_phase_timestamp: timestamp du dernier changement de phase VI1
    :param vi1_current_phase: phase actuelle VI1 ('SHORT' ou 'LONG') pour la protection temporelle
    :param account_summary: résumé du compte pour vérifier les positions manuelles
    :return: dict avec les résultats des vérifications
    """
    import time
    
    # 🚨 NOUVELLE PROTECTION: Bloquer le trading si position manuelle détectée
    if account_summary and account_summary.get('has_open_position', False):
        return {
            'trading_allowed': False,
            'reason': 'Position manuelle détectée sur Kraken',
            'short_ready': False,
            'long_vi1_ready': False,
            'long_vi2_ready': False,
            'long_reentry_ready': False,
            'vi1_protection_active': False,
            'details': {
                'short': {},
                'long_vi1': {},
                'long_vi2': {},
                'long_reentry': {}
            }
        }
    
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
    # ✅ CORRECTION: Bloquer SHORT si protection active ET phase VI1 = LONG
    if vi1_protection_active and vi1_current_phase == "LONG":
        short_ready = False  # Bloquer SHORT après prise d'une position LONG_VI1
        logger.log_protection_activation("SHORT", "Bloqué par protection VI1 (72h) - Phase LONG active")
    
    # Vérification LONG_VI1
    long_vi1_ready = all(long_vi1_conditions.values())
    # ✅ CORRECTION: Bloquer tous les LONGS si protection active ET phase VI1 = SHORT
    if vi1_protection_active and vi1_current_phase == "SHORT":
        long_vi1_ready = False  # Bloquer LONG_VI1 après prise d'une position SHORT
        logger.log_protection_activation("LONG_VI1", "Bloqué par protection VI1 (72h) - Phase SHORT active")
    
    # Vérification LONG_VI2
    long_vi2_ready = all(long_vi2_conditions.values())
    # ✅ CORRECTION: Bloquer tous les LONGS si protection active ET phase VI1 = SHORT
    if vi1_protection_active and vi1_current_phase == "SHORT":
        long_vi2_ready = False  # Bloquer LONG_VI2 après prise d'une position SHORT
        logger.log_protection_activation("LONG_VI2", "Bloqué par protection VI1 (72h) - Phase SHORT active")
    # NOUVELLE PROTECTION: Bloquer LONG_VI2 si position précédente = LONG
    if last_position_type in ["LONG_VI1", "LONG_VI2", "LONG_REENTRY"]:
        long_vi2_ready = False  # Bloquer si on vient de faire un LONG
        logger.log_protection_activation("LONG_VI2", f"Bloqué: position précédente = {last_position_type}")
    
    # Vérification LONG_REENTRY
    long_reentry_ready = all(long_reentry_conditions.values())
    if last_position_type == "LONG_REENTRY":
        long_reentry_ready = False  # Interdire LONG_REENTRY consécutif
        logger.log_protection_activation("LONG_REENTRY", "Bloqué: LONG_REENTRY consécutif interdit")
    # ✅ CORRECTION: Bloquer tous les LONGS si protection active ET phase VI1 = SHORT
    if vi1_protection_active and vi1_current_phase == "SHORT":
        long_reentry_ready = False  # Bloquer LONG_REENTRY après prise d'une position SHORT
        logger.log_protection_activation("LONG_REENTRY", "Bloqué par protection VI1 (72h) - Phase SHORT active")
    
    # NOUVELLE PROTECTION GLOBALE: Bloquer tous les LONGS après LONG_REENTRY
    if last_position_type == "LONG_REENTRY":
        long_vi1_ready = False  # Bloquer LONG_VI1 après LONG_REENTRY
        long_vi2_ready = False  # Bloquer LONG_VI2 après LONG_REENTRY
        long_reentry_ready = False  # Bloquer LONG_REENTRY après LONG_REENTRY
        logger.log_protection_activation("TOUS LES LONGS", "Bloqués: position précédente = LONG_REENTRY")
    
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
    summary.append(f"   VI1: {analysis['VI1']:.2f} ({'au-dessus' if analysis['vi1_above_close'] else 'en-dessous'} du close)")
    summary.append(f"   VI2: {analysis['VI2']:.2f} ({'au-dessus' if analysis['vi2_above_close'] else 'en-dessous'} du close)")
    summary.append(f"   VI3: {analysis['VI3']:.2f} ({'au-dessus' if analysis['vi3_above_close'] else 'en-dessous'} du close)")
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
    conditions = check_all_conditions(analysis, None, None, "LONG", None)
    summary = get_analysis_summary(analysis, conditions)
    
    print(summary) 