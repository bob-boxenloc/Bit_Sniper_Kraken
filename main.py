import os
import sys
import time
import json
import traceback
from datetime import datetime, timedelta
from core.error_handler import error_handler
from data.market_data import MarketData, CandleBuffer, RSIBuffer
from data.indicators import get_indicators_with_validation, calculate_complete_rsi_history, initialize_vi_history_from_user_values, calculate_vi_phases, calculate_complete_vi_phases_history, calculate_volatility_indexes_corrected, calculate_rsi_for_new_candle, calculate_atr_history
from trading.kraken_client import KrakenFuturesClient
from trading.trade_manager import TradeManager
from signals.technical_analysis import analyze_candles, check_all_conditions, get_analysis_summary
from signals.decision import decide_action, get_decision_summary
from core.initialization import initialize_bot, is_initialization_ready
from core.scheduler import run_every_15min
from core.logger import BitSniperLogger
from core.monitor import SystemMonitor
from core.notifications import BrevoNotifier
from core.state_manager import StateManager

# Variables globales
logger = BitSniperLogger()
system_monitor = SystemMonitor()
notification_manager = BrevoNotifier()
candle_buffer = CandleBuffer(max_candles=1920)  # 20 jours de bougies 15min pour VI
rsi_buffer = RSIBuffer(max_candles=1920)  # 20 jours de bougies 15min pour RSI
indicator_history = {}

def check_file_limits():
    """
    Vérifie le nombre de fichiers ouverts et envoie une alerte si nécessaire.
    """
    try:
        open_files = len(os.listdir('/proc/self/fd'))
        limit = 2048
        threshold = int(limit * 0.95)  # 95% = 1945
        
        if open_files > threshold:
            logger.log_warning(f"Trop de fichiers ouverts: {open_files}/{limit}")
            notification_manager.send_system_alert(
                'ALERTE FICHIERS', 
                f'''Trop de fichiers ouverts sur le serveur: {open_files}/{limit}

⚠️  ACTIONS À EFFECTUER :

1. Se connecter au serveur :
   ssh ubuntu@149.202.40.139
   su - bitsniper
   cd Bit_Sniper_Kraken
   source venv/bin/activate

2. Nettoyer les logs :
   sudo journalctl --vacuum-time=1d

3. Redémarrer le bot :
   sudo systemctl restart bitsniper

4. Vérifier :
   sudo systemctl status bitsniper
   sudo journalctl -u bitsniper -f

🔧 CAUSE PROBABLE : Accumulation de logs ou connexions non fermées'''
            )
            return True
        return False
    except Exception as e:
        logger.log_error(f"Erreur lors de la vérification des fichiers: {e}")
        return False

def initialize_indicator_history(candles):
    """
    Initialise l'historique complet des indicateurs avec les données historiques.
    Cette fonction est appelée au démarrage du bot.
    
    :param candles: liste des bougies historiques
    :return: True si l'initialisation réussit, False sinon
    """
    global indicator_history
    
    try:
        # Extraire les données OHLC
        highs = [float(candle['high']) for candle in candles]
        lows = [float(candle['low']) for candle in candles]
        closes = [float(candle['close']) for candle in candles]
        
        print(f"🔧 Initialisation de l'historique des indicateurs avec {len(candles)} bougies")
        
        # Calculer l'historique complet du RSI
        rsi_history = calculate_complete_rsi_history(closes, 40)
        if rsi_history is None:
            print("❌ Impossible de calculer l'historique RSI")
            return False
        
        # Initialiser l'historique des VI en partant des valeurs de départ fournies par l'utilisateur
        vi_history = initialize_vi_history_from_user_values(highs, lows, closes)
        if vi_history is None:
            print("❌ Impossible d'initialiser l'historique des VI avec les valeurs de départ")
            return False
        
        # CRITICAL FIX: Utiliser directement les valeurs de départ au lieu de recalculer
        # Les valeurs de départ fournies par l'utilisateur
        vi1_n1 = 116196  # BULLISH
        vi2_n1 = 121537  # BEARISH
        vi3_n1 = 120234  # BEARISH
        
        # Initialiser les phases VI avec les états de départ
        vi_phases_history = {
            'VI1_phases': ['BULLISH'],
            'VI2_phases': ['BEARISH'],
            'VI3_phases': ['BEARISH'],
            'VI1_values': [vi1_n1],
            'VI2_values': [vi2_n1],
            'VI3_values': [vi3_n1],
            'ATR_moyens': [vi_history['atr_history'][-1] if vi_history['atr_history'] else 200]
        }
        
        # Initialiser l'historique global avec les valeurs de départ
        indicator_history['rsi_history'] = rsi_history
        # CRITICAL FIX: Utiliser les valeurs de départ au lieu de l'historique calculé
        indicator_history['vi1_history'] = [vi1_n1]  # Valeur de départ utilisateur
        indicator_history['vi2_history'] = [vi2_n1]  # Valeur de départ utilisateur
        indicator_history['vi3_history'] = [vi3_n1]  # Valeur de départ utilisateur
        indicator_history['atr_history'] = vi_history['atr_history']
        indicator_history['true_ranges'] = vi_history['true_ranges']
        
        # Stocker aussi les bandes pour la logique dynamique future
        indicator_history['vi1_upper_history'] = vi_history['VI1_upper_history']
        indicator_history['vi1_lower_history'] = vi_history['VI1_lower_history']
        indicator_history['vi2_upper_history'] = vi_history['VI2_upper_history']
        indicator_history['vi2_lower_history'] = vi_history['VI2_lower_history']
        indicator_history['vi3_upper_history'] = vi_history['VI3_upper_history']
        indicator_history['vi3_lower_history'] = vi_history['VI3_lower_history']
        indicator_history['center_line_history'] = vi_history['center_line_history']
        
        # NOUVELLE LOGIQUE : Stocker les phases VI
        indicator_history['vi1_phases'] = vi_phases_history['VI1_phases']
        indicator_history['vi2_phases'] = vi_phases_history['VI2_phases']
        indicator_history['vi3_phases'] = vi_phases_history['VI3_phases']
        indicator_history['vi1_values'] = vi_phases_history['VI1_values']
        indicator_history['vi2_values'] = vi_phases_history['VI2_values']
        indicator_history['vi3_values'] = vi_phases_history['VI3_values']
        indicator_history['atr_moyens'] = vi_phases_history['ATR_moyens']
        
        print(f"✅ Historique initialisé avec valeurs de départ:")
        print(f"   RSI: {len(rsi_history)} valeurs (dernier: {rsi_history[-1]:.2f})")
        print(f"   VI1: {vi1_n1:.2f} (BULLISH) - VALEUR DE DÉPART UTILISATEUR")
        print(f"   VI2: {vi2_n1:.2f} (BEARISH) - VALEUR DE DÉPART UTILISATEUR")
        print(f"   VI3: {vi3_n1:.2f} (BEARISH) - VALEUR DE DÉPART UTILISATEUR")
        print(f"   ATR 28: {vi_history['atr_history'][-1]:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de l'historique: {e}")
        return False

def update_indicator_history(new_candle):
    """
    Recalcule l'historique complet des indicateurs avec toutes les bougies du buffer.
    Cela garantit que les calculs RMA sont corrects et cohérents.
    """
    global indicator_history
    
    print("🔄 update_indicator_history appelée !")
    
    # Récupérer les bougies pour RSI (buffer séparé)
    rsi_candles = rsi_buffer.get_candles()
    if len(rsi_candles) < 41:  # Minimum pour RSI(40)
        print("❌ Pas assez de bougies RSI pour recalculer")
        return False
    
    # Récupérer les bougies pour VI (buffer principal)
    vi_candles = candle_buffer.get_candles()
    if len(vi_candles) < 28:  # Minimum pour ATR(28)
        print("❌ Pas assez de bougies VI pour recalculer")
        return False
    
    print("🔄 Recalcul de l'historique complet des indicateurs...")
    
    # Extraire les données pour le RSI (buffer séparé)
    rsi_closes = [float(c['close']) for c in rsi_candles]
    
    # Extraire les données pour les VI (buffer principal)
    vi_closes = [float(c['close']) for c in vi_candles]
    vi_highs = [float(c['high']) for c in vi_candles]
    vi_lows = [float(c['low']) for c in vi_candles]
    
    # Calculer le RSI pour la nouvelle bougie seulement
    print("📊 Calcul RSI(40) pour la nouvelle bougie...")
    
    # Récupérer les moyennes RMA précédentes
    avg_gain_prev = indicator_history.get('rsi_avg_gain')
    avg_loss_prev = indicator_history.get('rsi_avg_loss')
    
    if avg_gain_prev is not None and avg_loss_prev is not None:
        # Calculer le RSI de la nouvelle bougie
        rsi_result = calculate_rsi_for_new_candle(rsi_closes, avg_gain_prev, avg_loss_prev, 40)
        if rsi_result:
            new_rsi, new_avg_gain, new_avg_loss = rsi_result
            
            # Mettre à jour l'historique RSI
            rsi_history = indicator_history.get('rsi_history', [])
            rsi_history.append(new_rsi)
            indicator_history['rsi_history'] = rsi_history
            
            # Stocker les nouvelles moyennes pour la prochaine bougie
            indicator_history['rsi_avg_gain'] = new_avg_gain
            indicator_history['rsi_avg_loss'] = new_avg_loss
            
            print(f"✅ RSI calculé pour la nouvelle bougie: {new_rsi:.2f}")
        else:
            print("❌ Impossible de calculer le RSI pour la nouvelle bougie")
            return False
    else:
        # Première fois - recalculer l'historique complet
        print("📊 Recalcul complet de l'historique RSI (première fois)...")
        rsi_history = calculate_complete_rsi_history(rsi_closes, 40)
    if rsi_history:
        indicator_history['rsi_history'] = rsi_history
        
            # Calculer et stocker les moyennes RMA finales
        deltas = []
        for i in range(1, len(rsi_closes)):
                deltas.append(rsi_closes[i] - rsi_closes[i-1])
        
        gains = [max(delta, 0) for delta in deltas]
        losses = [max(-delta, 0) for delta in deltas]
        
            # Calculer les moyennes RMA finales
        avg_gain = sum(gains[:40]) / 40
        avg_loss = sum(losses[:40]) / 40
        
        # Continuer le calcul RMA pour toutes les périodes suivantes
        for i in range(40, len(deltas)):
            avg_gain = (avg_gain * 39 + gains[i]) / 40
            avg_loss = (avg_loss * 39 + losses[i]) / 40
        
            # Stocker les moyennes finales
        indicator_history['rsi_avg_gain'] = avg_gain
        indicator_history['rsi_avg_loss'] = avg_loss
        
        print(f"✅ RSI recalculé: {len(rsi_history)} valeurs")
        print(f"   Dernière valeur: {rsi_history[-1]:.2f}")
    else:
        print("❌ Impossible de recalculer l'historique RSI")
        return False
    
    # Recalculer l'historique complet des Volatility Indexes
    print("📊 Recalcul Volatility Indexes...")
    
    # NOUVELLE LOGIQUE RÉELLE : Calculer les VI selon la vraie logique découverte
    print("📊 Calcul VI avec la vraie logique (croisements + ATR)...")
    
    # Extraire les données OHLC pour les VI (convertir en float)
    closes = vi_closes
    highs = vi_highs
    lows = vi_lows
    
    # Récupérer les VI précédents de l'historique global (si disponibles)
    # UTILISER LES VALEURS DE DÉPART FOURNIES PAR L'UTILISATEUR COMME BASE
    vi1_n1 = 116196  # Valeur de départ fournie par l'utilisateur
    vi2_n1 = 121537  # Valeur de départ fournie par l'utilisateur
    vi3_n1 = 120234  # Valeur de départ fournie par l'utilisateur
    
    # Utiliser les valeurs de départ si pas d'historique, sinon utiliser l'historique
    previous_vi1 = indicator_history.get('vi1_history', [vi1_n1])[-1] if indicator_history.get('vi1_history') else vi1_n1
    previous_vi2 = indicator_history.get('vi2_history', [vi2_n1])[-1] if indicator_history.get('vi2_history') else vi2_n1
    previous_vi3 = indicator_history.get('vi3_history', [vi3_n1])[-1] if indicator_history.get('vi3_history') else vi3_n1
    
    # Récupérer les états précédents des VI (si disponibles)
    # Utiliser les états de départ corrects pour VI1, VI2 et VI3
    previous_vi1_state = indicator_history.get('vi1_state', "BULLISH")
    previous_vi2_state = indicator_history.get('vi2_state', "BEARISH")
    previous_vi3_state = indicator_history.get('vi3_state', "BEARISH")
    
    # ✅ NOUVEAU : Récupérer les flags de croisement de la bougie précédente
    vi1_crossed_last_candle = indicator_history.get('vi1_crossed_last_candle', False)
    vi2_crossed_last_candle = indicator_history.get('vi2_crossed_last_candle', False)
    vi3_crossed_last_candle = indicator_history.get('vi3_crossed_last_candle', False)
    vi1_crossing_direction = indicator_history.get('vi1_crossing_direction', None)
    vi2_crossing_direction = indicator_history.get('vi2_crossing_direction', None)
    vi3_crossing_direction = indicator_history.get('vi3_crossing_direction', None)
    
    # Calculer l'ATR 28 pour avoir les données nécessaires
    atr_28_history = calculate_atr_history(vi_highs, vi_lows, vi_closes, period=28)
    if not atr_28_history or len(atr_28_history) < 2:
        print("❌ Impossible de calculer l'ATR 28 ou pas assez de données")
        return False
    
    # CRITICAL FIX: Utiliser la nouvelle fonction qui calcule seulement la nouvelle valeur
    current_close = float(vi_candles[-1]['close'])
    current_atr = atr_28_history[-1]
    previous_atr = atr_28_history[-2]
    
    vi_new_values = calculate_volatility_indexes_corrected(
        closes, highs, lows,
        previous_vi1, previous_vi2, previous_vi3,
        previous_vi1_state, previous_vi2_state, previous_vi3_state,
        vi1_crossed_last_candle, vi2_crossed_last_candle, vi3_crossed_last_candle,
        vi1_crossing_direction, vi2_crossing_direction, vi3_crossing_direction
    )
    
    if vi_new_values:
        # Stocker les nouvelles valeurs VI (seulement les valeurs finales)
        indicator_history['vi1_history'] = [vi_new_values['VI1']]
        indicator_history['vi2_history'] = [vi_new_values['VI2']]
        indicator_history['vi3_history'] = [vi_new_values['VI3']]
        
        # Stocker les états des VI pour la prochaine itération
        # Les états sont calculés dynamiquement selon la position par rapport au close
        indicator_history['vi1_state'] = "BEARISH" if vi_new_values['VI1'] > current_close else "BULLISH"
        indicator_history['vi2_state'] = "BEARISH" if vi_new_values['VI2'] > current_close else "BULLISH"
        indicator_history['vi3_state'] = "BEARISH" if vi_new_values['VI3'] > current_close else "BULLISH"
        
        # ✅ NOUVEAU : Stocker les flags de croisement pour la prochaine bougie
        indicator_history['vi1_crossed_last_candle'] = vi_new_values.get('vi1_crossed_last_candle', False)
        indicator_history['vi2_crossed_last_candle'] = vi_new_values.get('vi2_crossed_last_candle', False)
        indicator_history['vi3_crossed_last_candle'] = vi_new_values.get('vi3_crossed_last_candle', False)
        indicator_history['vi1_crossing_direction'] = vi_new_values.get('vi1_crossing_direction', None)
        indicator_history['vi2_crossing_direction'] = vi_new_values.get('vi2_crossing_direction', None)
        indicator_history['vi3_crossing_direction'] = vi_new_values.get('vi3_crossing_direction', None)
        
        # Calculer les phases VI basées sur la position par rapport au close ACTUEL
        # On utilise seulement les valeurs finales des VI
        current_close = float(vi_candles[-1]['close'])  # Close de la dernière bougie
        
        # VI1 phases (utiliser seulement la dernière valeur)
        vi1_final = vi_new_values['VI1']  # ✅ CORRECTION : Utiliser la clé correcte
        vi1_phase = "BEARISH" if vi1_final > current_close else "BULLISH"
        
        # VI2 phases (utiliser seulement la dernière valeur)
        vi2_final = vi_new_values['VI2']  # ✅ CORRECTION : Utiliser la clé correcte
        vi2_phase = "BEARISH" if vi2_final > current_close else "BULLISH"
        
        # VI3 phases (utiliser seulement la dernière valeur)
        vi3_final = vi_new_values['VI3']  # ✅ CORRECTION : Utiliser la clé correcte
        vi3_phase = "BEARISH" if vi3_final > current_close else "BULLISH"
        
        # Stocker seulement les phases finales (pas d'historique)
        indicator_history['vi1_phases'] = [vi1_phase]
        indicator_history['vi2_phases'] = [vi2_phase]
        indicator_history['vi3_phases'] = [vi3_phase]
        
        print(f"✅ VI calculés avec la logique correcte (calculate_volatility_indexes_corrected):")
        print(f"   VI1: {vi_new_values['VI1']:.2f} (Phase: {vi1_phase})")
        print(f"   VI2: {vi_new_values['VI2']:.2f} (Phase: {vi2_phase})")
        print(f"   VI3: {vi_new_values['VI3']:.2f} (Phase: {vi3_phase})")
        print(f"   États finaux:")
        print(f"     VI1: {indicator_history['vi1_state']}")
        print(f"     VI2: {indicator_history['vi2_state']}")
        print(f"     VI3: {indicator_history['vi3_state']}")
    else:
        print("❌ Impossible de calculer les VI avec la logique correcte")
        return False
    
    print("✅ Historique complet recalculé avec succès")
    return True

def trading_loop():
    """
    Boucle principale de trading avec gestion d'erreur globale.
    """
    try:
        _trading_loop_internal()
    except Exception as e:
        # 🚨 CRASH DÉTECTÉ DANS LA BOUCLE DE TRADING
        error_type = type(e).__name__
        error_message = str(e)
        
        logger.log_error(f"CRASH dans trading_loop: {error_type} - {error_message}")
        print(f"\n🚨 CRASH DÉTECTÉ DANS LA BOUCLE DE TRADING !")
        print(f"   Type d'erreur: {error_type}")
        print(f"   Message: {error_message}")
        
        # 📧 NOTIFICATION EMAIL D'URGENCE - CRASH TRADING
        try:
            import traceback
            stack_trace = traceback.format_exc()
            
            notification_manager.send_crash_notification(
                error_type="CRASH TRADING",
                error_message=error_message,
                stack_trace=stack_trace,
                context="Erreur fatale dans la boucle de trading (récupération données, analyse, exécution)"
            )
            print("   📧 Email d'urgence envoyé pour le crash trading")
            
        except Exception as email_error:
            logger.log_error(f"Impossible d'envoyer l'email de crash trading: {email_error}")
            print(f"   ❌ Impossible d'envoyer l'email de crash: {email_error}")
        
        # Relancer la boucle après un délai (pour éviter les boucles infinies de crash)
        print("   🔄 Redémarrage de la boucle dans 60 secondes...")
        time.sleep(60)
        return

def _trading_loop_internal():
    """
    Implémentation interne de la boucle de trading.
    """
    logger.log_scheduler_tick()
    
    # Vérifier la santé du système avant de commencer
    try:
        health = system_monitor.get_system_health()
        if not health.is_healthy:
            logger.log_warning(f"Système en mauvaise santé: {health.consecutive_errors} erreurs consécutives")
            print(f"⚠️  SYSTÈME EN MAUVAISE SANTÉ: {health.consecutive_errors} erreurs consécutives")
            
            # Vérifier les alertes
            alerts = system_monitor.check_alerts()
            if alerts:
                for alert in alerts:
                    print(f"🚨 {alert}")
            
            # Continuer malgré tout, mais avec prudence
            print("   Le bot continue mais avec prudence...")
    except Exception as e:
        logger.log_error(f"Erreur lors de la vérification de la santé système: {e}")
    
    # Vérifier les limites de fichiers
    check_file_limits()
    
    print("\n" + "="*60)
    print("NOUVELLE BOUGIE 15M - ANALYSE COMPLÈTE (Nouvelle Stratégie)")
    print("="*60)
    
    # 1. Récupération des données de marché
    print("\n📊 RÉCUPÉRATION DES DONNÉES")
    
    # Initialiser le gestionnaire d'état
    sm = StateManager()
    
    try:
        md = MarketData()
        
        # Initialisation du buffer VI - RÉCUPÉRATION FORCÉE D'HISTORIQUE
        if not candle_buffer.get_candles():
            print("🔄 Buffer VI vide - RÉCUPÉRATION FORCÉE D'HISTORIQUE")
            
            # Récupérer 20 jours d'historique (1920 bougies 15min) pour des calculs précis
            print("📥 Récupération de 20 jours d'historique (1920 bougies)...")
            historical_candles = md.get_ohlcv_15m(limit=1920)
            
            if historical_candles and len(historical_candles) >= 1920:
                # Ajouter toutes les bougies historiques au buffer VI (1920 bougies)
                for candle in historical_candles:
                    candle_buffer.add_candle(candle)
                
                print(f"✅ {len(historical_candles)} bougies historiques ajoutées au buffer VI (20 jours)")
                print(f"📊 Buffer VI: {len(candle_buffer.get_candles())}/{candle_buffer.max_candles} bougies")
                
                # Afficher le résumé détaillé du buffer
                print("📋 " + candle_buffer.get_buffer_summary())
                
                # INITIALISER L'HISTORIQUE COMPLET DES INDICATEURS
                candles = candle_buffer.get_candles()
                if not initialize_indicator_history(candles):
                    print("❌ ÉCHEC INITIALISATION - Le bot ne peut pas démarrer")
                    return
            else:
                print("❌ Impossible de récupérer 20 jours d'historique - attente des données Kraken")
                return
        else:
            print("✅ Buffer VI déjà initialisé avec données")
        
        # Initialisation du buffer RSI - RÉCUPÉRATION FORCÉE D'HISTORIQUE
        if not rsi_buffer.get_candles():
            print("🔄 Buffer RSI vide - RÉCUPÉRATION FORCÉE D'HISTORIQUE")
            
            # Récupérer 20 jours d'historique (1920 bougies 15min) pour le RSI avec l'ancienne logique
            print("📥 Récupération de 20 jours d'historique RSI (1920 bougies)...")
            historical_candles_rsi = md.get_ohlcv_15m_rsi(limit=1920)
            
            if historical_candles_rsi and len(historical_candles_rsi) >= 1920:
                # Ajouter toutes les bougies historiques au buffer RSI (1920 bougies)
                for candle in historical_candles_rsi:
                    rsi_buffer.add_candle(candle)
                
                print(f"✅ {len(historical_candles_rsi)} bougies historiques ajoutées au buffer RSI (20 jours)")
                print(f"📊 Buffer RSI: {len(rsi_buffer.get_candles())}/{rsi_buffer.max_candles} bougies")
            else:
                print("❌ Impossible de récupérer 20 jours d'historique RSI - attente des données Kraken")
                return
        else:
            print("✅ Buffer RSI déjà initialisé avec données")
        
        # Récupérer la dernière bougie fermée de Kraken pour VI
        print("�� Récupération de la dernière bougie fermée pour VI")
        new_candles = md.get_ohlcv_15m(limit=1)  # Récupérer seulement la dernière bougie
        
        print(f"🔄 DEBUG: new_candles récupérées: {len(new_candles) if new_candles else 0}")
        
        if new_candles:
            # Vérifier si la bougie n'est pas déjà dans le buffer VI
            new_candle = new_candles[-1]  # L'avant-dernière bougie (la dernière fermée)
            # Note: data/market_data.py retourne déjà l'avant-dernière bougie quand limit=1
            buffer_times = [c['time'] for c in candle_buffer.get_candles()]
            
            print(f"🔄 DEBUG: new_candle time: {new_candle['time']}")
            print(f"🔄 DEBUG: buffer_times contient {new_candle['time']}: {new_candle['time'] in buffer_times}")
            
            if new_candle['time'] not in buffer_times:
                candle_added = candle_buffer.add_candle(new_candle)
                
                if candle_added:
                    print(f"✅ Nouvelle bougie ajoutée: {new_candle['datetime']} - Close: {new_candle['close']} - Volume: {new_candle.get('volume', 'N/A')} - Count: {new_candle['count']}")
                    print(f"🔧 DEBUG BOUGIE DÉTAILLÉE:")
                    print(f"   Time: {new_candle['time']}")
                    print(f"   Open: {new_candle['open']}")
                    print(f"   High: {new_candle['high']}")
                    print(f"   Low: {new_candle['low']}")
                    print(f"   Close: {new_candle['close']}")
                    print(f"   True Range calculé: {float(new_candle['high']) - float(new_candle['low']):.2f}")
                else:
                    print(f"ℹ️  Bougie déjà présente dans le buffer: {new_candle['datetime']} - Continuation de l'analyse...")
            else:
                print(f"ℹ️  Bougie déjà présente dans le buffer VI: {new_candle['datetime']} - Continuation de l'analyse...")
            
            # Récupérer la dernière bougie fermée de Kraken pour RSI (ancienne logique)
            print("🔄 Récupération de la dernière bougie fermée pour RSI")
            new_candles_rsi = md.get_ohlcv_15m_rsi(limit=1)  # Récupérer avec l'ancienne logique
            
            if new_candles_rsi:
                new_candle_rsi = new_candles_rsi[-1]  # Dernière bougie fermée (ancienne logique)
                buffer_times_rsi = [c['time'] for c in rsi_buffer.get_candles()]
                
                if new_candle_rsi['time'] not in buffer_times_rsi:
                    rsi_candle_added = rsi_buffer.add_candle(new_candle_rsi)
                    if rsi_candle_added:
                        print(f"✅ Nouvelle bougie RSI ajoutée: {new_candle_rsi['datetime']} - Close: {new_candle_rsi['close']}")
                    else:
                        print(f"ℹ️  Bougie RSI déjà présente: {new_candle_rsi['datetime']}")
                else:
                    print(f"ℹ️  Bougie RSI déjà présente: {new_candle_rsi['datetime']}")
            
            # Mettre à jour l'historique des indicateurs dans tous les cas
            print("🔄 Tentative de mise à jour de l'historique des indicateurs...")
            print(f"🔄 DEBUG: Appel de update_indicator_history avec {new_candle['datetime']}")
            print("🔧 DEBUG: Fonction update_indicator_history appelée !")
            if update_indicator_history(new_candle):
                print("✅ Historique des indicateurs mis à jour")
            else:
                print("⚠️  Impossible de mettre à jour l'historique des indicateurs")
            
            # Afficher le statut du buffer
            status = candle_buffer.get_status()
            print(f"📊 Buffer: {status['total_candles']}/{status['max_candles']} bougies")
            print(f"   Dernière bougie: {status['latest_candle']}")
            
            # Afficher le résumé détaillé du buffer
            print("📋 " + candle_buffer.get_buffer_summary())
            
            # Récupérer toutes les bougies pour les calculs
            candles = candle_buffer.get_candles()
            
            # Vérifier qu'on a assez de données pour les indicateurs
            if len(candles) < 41:  # Minimum pour RSI(40) + ATR(28)
                logger.log_warning(f"Pas assez de données historiques: {len(candles)}/41")
                print(f"❌ TRADING IMPOSSIBLE: Pas assez de données historiques ({len(candles)}/41)")
                print("   Le bot attendra d'avoir au moins 41 bougies.")
                return
            
            # Récupérer les 2 dernières bougies pour les décisions
            latest_candles = candle_buffer.get_latest_candles(2)
            
            if len(latest_candles) < 2:
                logger.log_warning("Pas assez de bougies pour les décisions")
                print("❌ TRADING IMPOSSIBLE: Pas assez de bougies pour les décisions")
                print("   Le bot attendra d'avoir au moins 2 bougies fermées.")
                return
            
            # Vérifier que les bougies utilisées sont fermées (volume > 0)
            for i, candle in enumerate(latest_candles):
                if float(candle['volume']) == 0:
                    logger.log_warning(f"Bougie {i+1} a un volume de 0 (non fermée)")
                    print(f"⚠️  BOUGIE N-{2-i} NON FERMÉE: Volume = 0")
                    print("   Le bot continue avec les données disponibles...")
        
        else:
            logger.log_warning("Aucune bougie récupérée de Kraken")
            print("❌ TRADING IMPOSSIBLE: Aucune bougie récupérée de Kraken")
            return
            
    except Exception as e:
        logger.log_error(f"Erreur lors de la récupération des données de marché: {e}")
        print(f"❌ ERREUR RÉCUPÉRATION DONNÉES: {e}")
        print("   Le bot attendra la prochaine bougie pour réessayer.")
        return
    
    # 2. Calcul des indicateurs en temps réel
    print("\n🔍 CALCUL DES INDICATEURS")
    
    # Utiliser l'historique complet des indicateurs au lieu de recalculer
    if len(indicator_history['rsi_history']) > 0 and len(indicator_history['vi1_phases']) > 0:
        # Utiliser les valeurs de l'historique pour les indicateurs actuels
        rsi_current = indicator_history['rsi_history'][-1]
        
        # NOUVELLE LOGIQUE : Utiliser les phases VI
        vi1_phase = indicator_history['vi1_phases'][-1]
        vi2_phase = indicator_history['vi2_phases'][-1]
        vi3_phase = indicator_history['vi3_phases'][-1]
        
        # Ancienne logique (gardée pour debug)
        vi1_current_old = indicator_history['vi1_history'][-1]
        vi2_current_old = indicator_history['vi2_history'][-1]
        vi3_current_old = indicator_history['vi3_history'][-1]
        
        # CORRECTION CRITIQUE: Utiliser les vraies valeurs VI actuelles pour les croisements
        vi1_current = indicator_history['vi1_history'][-1]  # Dernière valeur VI1 calculée
        vi2_current = indicator_history['vi2_history'][-1]  # Dernière valeur VI2 calculée
        vi3_current = indicator_history['vi3_history'][-1]  # Dernière valeur VI3 calculée
        
        indicators = {
            'RSI': rsi_current,
            'VI1_phase': vi1_phase,
            'VI2_phase': vi2_phase,
            'VI3_phase': vi3_phase,
            # CORRECTION: Vraies valeurs VI actuelles pour les croisements
            'vi1': vi1_current,
            'vi2': vi2_current,
            'vi3': vi3_current
        }
        
        indicators_success = True
        indicators_message = "Indicateurs récupérés depuis l'historique (nouvelle logique phases VI)"
        
        print(f"✅ {indicators_message}")
        print(f"   RSI: {indicators['RSI']:.2f}")
        print(f"   NOUVELLE LOGIQUE - Phases VI:")
        print(f"     VI1: {indicators['VI1_phase']}")
        print(f"     VI2: {indicators['VI2_phase']}")
        print(f"     VI3: {indicators['VI3_phase']}")
        print(f"   VALEURS VI ACTUELLES (pour croisements):")
        print(f"     VI1: {indicators['VI1']:.2f}")  # ✅ CORRECTION : Clé correcte
        print(f"     VI2: {indicators['VI2']:.2f}")  # ✅ CORRECTION : Clé correcte
        print(f"     VI3: {indicators['VI3']:.2f}")  # ✅ CORRECTION : Clé correcte
        
        # Debug: Afficher les valeurs pour les 2 dernières bougies
        if len(indicator_history['rsi_history']) >= 2:
            print(f"🔧 DEBUG - Valeurs pour les 2 dernières bougies:")
            print(f"   RSI N-2: {indicator_history['rsi_history'][-2]:.2f}")
            print(f"   RSI N-1: {indicator_history['rsi_history'][-1]:.2f}")
            print(f"   VI1 Phase actuelle: {indicator_history['vi1_phases'][-1]}")
            print(f"   VI2 Phase actuelle: {indicator_history['vi2_phases'][-1]}")
            print(f"   VI3 Phase actuelle: {indicator_history['vi3_phases'][-1]}")
        
    else:
        # Fallback: calculer les indicateurs en temps réel (ancienne méthode)
        indicators_success, indicators, indicators_message = get_indicators_with_validation(candles, rsi_period=40)
    
    if not indicators_success:
        logger.log_warning(f"Indicateurs non calculables: {indicators_message}")
        print(f"❌ TRADING IMPOSSIBLE: {indicators_message}")
        return
    
        print(f"✅ {indicators_message}")
        print(f"   RSI: {indicators['RSI']:.2f}")
        print(f"   VI1: {indicators['VI1']:.2f}")  # ✅ CORRECTION : Clé correcte
        print(f"   VI2: {indicators['VI2']:.2f}")  # ✅ CORRECTION : Clé correcte
        print(f"   VI3: {indicators['VI3']:.2f}")  # ✅ CORRECTION : Clé correcte
    
    # Logger l'analyse des bougies
    logger.log_candle_analysis(candles, indicators_success, indicators_message)
    print(f"✅ {indicators_message}")
    
    # Logger le calcul des indicateurs
    logger.log_indicators_calculation(indicators)
    
    # Récupérer la dernière bougie pour l'analyse
    latest_candles = candle_buffer.get_latest_candles(1)
    if not latest_candles:
        logger.log_warning("Aucune bougie disponible pour l'analyse")
        print("❌ TRADING IMPOSSIBLE: Aucune bougie disponible")
        return
    
    current_candle = latest_candles[0]  # Dernière bougie
    
    print(f"🎯 BOUGIE ACTUELLE POUR ANALYSE:")
    print(f"   {current_candle['datetime']}: Close={current_candle['close']}, Volume={current_candle.get('volume', 'N/A')}, Count={current_candle['count']}")
    
    # Debug: Afficher les valeurs utilisées pour l'analyse
    print(f"🔧 DEBUG ANALYSE - Close actuel: {float(current_candle['close']):.2f}")
    print(f"   VI1 vs Close: {indicators['VI1']:.2f} vs {float(current_candle['close']):.2f}")  # ✅ CORRECTION : Clé correcte
    
    # 3. Analyse technique complète avec nouveaux indicateurs
    print("\n🔍 ANALYSE TECHNIQUE (Nouvelle Stratégie - Phases VI)")
    
    # NOUVELLE LOGIQUE : Utiliser les phases VI au lieu de la comparaison avec le prix
    vi1_current_phase = indicators['VI1_phase']
    vi2_current_phase = indicators['VI2_phase']
    vi3_current_phase = indicators['VI3_phase']
    
    print(f"🎯 PHASES VI ACTUELLES:")
    print(f"   VI1: {vi1_current_phase}")
    print(f"   VI2: {vi2_current_phase}")
    print(f"   VI3: {vi3_current_phase}")
    
    # ANCIENNE LOGIQUE (gardée pour debug)
    vi1_current_old = indicators['VI1']  # ✅ CORRECTION : Clé correcte
    current_close = float(current_candle['close'])
    vi1_above_close_old = vi1_current_old > current_close
    current_phase_old = 'SHORT' if vi1_above_close_old else 'LONG'
    
    print(f"🔧 DEBUG - Ancienne logique:")
    print(f"   VI1 vs Close: {vi1_current_old:.2f} vs {current_close:.2f}")
    print(f"   Phase ancienne: {current_phase_old}")
    
    # NOUVELLE LOGIQUE : Déterminer la phase principale basée sur VI1
    current_phase = 'SHORT' if vi1_current_phase == 'BEARISH' else 'LONG'
    
    # Vérifier si la phase VI1 a changé
    old_phase = sm.get_vi1_current_phase()
    sm.update_vi1_phase(current_phase)
    
    # Logger le changement de phase VI1 si nécessaire
    if old_phase != current_phase:
        logger.log_vi1_phase_change(old_phase, current_phase, time.time())
        print(f"🔄 CHANGEMENT DE PHASE VI1: {old_phase} → {current_phase}")
        print(f"   ATR actuel: {indicator_history['atr_history'][-1]:.2f}")
        print(f"   ATR moyen: {indicator_history['atr_moyens'][-1]:.2f}")
        print(f"   Ratio ATR: {indicator_history['atr_history'][-1] / indicator_history['atr_moyens'][-1]:.3f}")
    
    # CORRECTION: Passer les 2 dernières bougies pour détecter les croisements
    latest_candles = candle_buffer.get_latest_candles(2)
    if len(latest_candles) < 2:
        logger.log_warning("Pas assez de bougies pour détecter les croisements")
        print("❌ TRADING IMPOSSIBLE: Pas assez de bougies pour détecter les croisements")
        return
    
    analysis = analyze_candles(latest_candles, indicators)
    conditions_check = check_all_conditions(analysis, sm.get_last_position_type(), sm.get_vi1_phase_timestamp())
    analysis_summary = get_analysis_summary(analysis, conditions_check)
    print(analysis_summary)
    logger.log_technical_analysis(analysis, conditions_check)
    
    # 📧 NOTIFICATION EMAIL - CROISEMENTS VI1
    try:
        vi1_crossing_over = analysis.get('vi1_crossing_over', False)
        vi1_crossing_under = analysis.get('vi1_crossing_under', False)
        
        if vi1_crossing_over:
            # VI1 traverse le close vers le haut (BEARISH)
            current_price = float(analysis['current_candle']['close'])
            current_time = datetime.now().strftime("%d/%m %H:%M")
            
            notification_manager.send_trade_notification(
                action="CROISEMENT VI1",
                position_type="BEARISH (au-dessus)",
                price=f"${current_price:.2f}",
                datetime_str=current_time
            )
            print(f"   📧 Email de notification envoyé pour le croisement VI1 BEARISH")
            
        elif vi1_crossing_under:
            # VI1 traverse le close vers le bas (BULLISH)
            current_price = float(analysis['current_candle']['close'])
            current_time = datetime.now().strftime("%d/%m %H:%M")
            
            notification_manager.send_trade_notification(
                action="CROISEMENT VI1",
                position_type="BULLISH (en-dessous)",
                price=f"${current_price:.2f}",
                datetime_str=current_time
            )
            print(f"   📧 Email de notification envoyé pour le croisement VI1 BULLISH")
            
    except Exception as e:
        logger.log_error(f"Erreur lors de l'envoi de la notification de croisement VI1: {e}")
        print(f"   ⚠️  Erreur notification croisement VI1: {e}")
    
    # Logger l'état de la nouvelle stratégie
    logger.log_new_strategy_state(sm)
    
    # 4. Récupération des infos du compte
    print("\n💰 RÉCUPÉRATION DU COMPTE")
    try:
        kf = KrakenFuturesClient()
        current_price = float(current_candle['close'])
        account_summary = kf.get_account_summary(current_price)
        
        # Initialisation du gestionnaire de trades
        tm = TradeManager(kf.api_key, kf.api_secret)
        
    except Exception as e:
        logger.log_error(f"Erreur lors de la récupération du compte: {e}")
        print(f"❌ ERREUR RÉCUPÉRATION COMPTE: {e}")
        print("   Le bot attendra la prochaine bougie pour réessayer.")
        return
    
    logger.log_account_status(account_summary)
    
    wallet = account_summary['wallet']
    positions = account_summary['positions']
    max_size = account_summary['max_position_size']
    current_price = account_summary['current_btc_price']
    
    # Vérifications de sécurité sur le portefeuille
    if wallet['usd_balance'] <= 0:
        logger.log_warning(f"Solde USD insuffisant: ${wallet['usd_balance']:.2f}")
        print("❌ TRADING IMPOSSIBLE: Solde USD insuffisant")
        print(f"   Solde disponible: ${wallet['usd_balance']:.2f}")
        return
    
    if max_size['max_btc_size'] < 0.0001:
        logger.log_warning(f"Taille de position trop faible: {max_size['max_btc_size']:.4f} BTC")
        print("❌ TRADING IMPOSSIBLE: Taille de position maximale trop faible")
        print(f"   Taille max: {max_size['max_btc_size']:.4f} BTC (minimum: 0.0001 BTC)")
        return
    
    # 🚨 VÉRIFICATION CRITIQUE - POSITION APRÈS CRASH
    has_open_position = len(positions) > 0
    local_position = sm.get_current_position()
    
    if has_open_position and local_position is None:
        # 🚨 CRASH AVEC POSITION OUVERTE DÉTECTÉ !
        print("\n🚨 ALERTE CRITIQUE - POSITION APRÈS CRASH DÉTECTÉE !")
        print("   📊 Position sur Kraken: OUI")
        print("   💾 Position dans l'état local: NON")
        print("   🔒 TRADING BLOQUÉ - INTERVENTION HUMAINE REQUISE")
        
        # 📧 NOTIFICATION EMAIL D'URGENCE - CRASH AVEC POSITION
        try:
            position_info = positions[0]  # Première position
            position_side = position_info.get('side', 'UNKNOWN')
            position_size = position_info.get('size', 0)
            position_price = position_info.get('price', 0)
            
            notification_manager.send_crash_notification(
                error_type="CRASH AVEC POSITION OUVERTE",
                error_message=f"Position {position_side} {position_size:.4f} BTC @ ${position_price:.2f} détectée sur Kraken mais pas dans l'état local",
                context="Le bot a crashé avec une position ouverte. Intervention humaine requise pour fermer la position manuellement.",
                stack_trace="Position détectée après redémarrage - État local perdu lors du crash"
            )
            print("   📧 Email d'urgence envoyé pour crash avec position ouverte")
            
        except Exception as email_error:
            logger.log_error(f"Impossible d'envoyer l'email de crash avec position: {email_error}")
            print(f"   ❌ Erreur notification email: {email_error}")
        
        print("\n🔧 ACTIONS REQUISES:")
        print("   1. Se connecter au serveur: ssh bitsniper@149.202.40.139")
        print("   2. Fermer manuellement la position sur Kraken")
        print("   3. Redémarrer le bot: sudo systemctl restart bitsniper")
        print("   4. Vérifier que le bot redémarre sans position")
        
        print("\n⏸️  Bot en mode surveillance - Trading bloqué")
        return  # Skip tout le trading
    
    print(f"✅ Compte accessible - Solde: ${wallet['usd_balance']:.2f}")
    print(f"   Prix BTC actuel: ${current_price:.2f}")
    print(f"   Taille max position: {max_size['max_btc_size']:.4f} BTC (${max_size['max_usd_value']:.2f})")
    print(f"   Positions ouvertes: {len(positions)}")
    
    if positions:
        for pos in positions:
            print(f"     - {pos['side'].upper()} {pos['size']:.4f} BTC @ ${pos['price']:.2f}")
            print(f"       PnL: ${pos['unrealizedPnl']:.2f}, Marge: ${pos['margin']:.2f}")
    else:
        print("     - Aucune position ouverte")
    
    # 5. Prise de décision
    print("\n🎯 DÉCISION DE TRADING")
    
    # DEBUG: Logging détaillé de l'objet analysis pour éviter les crashes
    print("🔧 DEBUG - Structure de l'objet analysis:")
    if analysis:
        print(f"   Type: {type(analysis)}")
        print(f"   Clés disponibles: {list(analysis.keys())}")
        if 'current_candle' in analysis:
            print(f"   current_candle: {analysis['current_candle']}")
        if 'rsi' in analysis:
            print(f"   RSI: {analysis['rsi']}")
    else:
        print("   ❌ analysis est None ou vide !")
        logger.log_error("trading_loop: analysis est None ou vide avant decide_action")
        print("   Le bot va maintenir sa position actuelle.")
        return
    
    decision = decide_action(analysis, conditions_check, account_summary, sm)
    decision_summary = get_decision_summary(decision)
    print(decision_summary)
    logger.log_trading_decision(decision)
    
    # 6. Exécution de la décision (si pas "hold")
    if decision['action'] != 'hold':
        print("\n🚀 EXÉCUTION DE L'ORDRE")
        execution_result = tm.execute_decision(decision, account_summary)
        execution_summary = tm.get_execution_summary(execution_result)
        print(execution_summary)
        
        if execution_result.get('success', False):
            print("   ✅ Ordre exécuté avec succès")
            logger.log_order_execution(execution_result)
            
            # Mettre à jour l'état si l'ordre est réussi
            if decision['action'].startswith('enter_'):
                position_type = decision['position_type']
                sm.update_position(position_type, 'open', {
                    'entry_price': decision['entry_price'],
                    'entry_rsi': decision['entry_rsi'],
                    'size': decision['size'],
                    'entry_time': decision['entry_time']
                })
                
                # 📧 NOTIFICATION EMAIL - ENTRÉE EN POSITION
                try:
                    entry_price = decision['entry_price']
                    entry_time = datetime.fromtimestamp(decision['entry_time']).strftime("%d/%m %H:%M")
                    position_size = decision['size']
                    notification_manager.send_trade_notification(
                        action="ENTRÉE",
                        position_type=position_type,
                        price=f"${entry_price:.2f}",
                        datetime_str=entry_time,
                        size=position_size
                    )
                    print(f"   📧 Email de notification envoyé pour l'entrée en {position_type}")
                except Exception as e:
                    logger.log_error(f"Erreur lors de l'envoi de la notification email: {e}")
                    print(f"   ⚠️  Erreur notification email: {e}")
                
            elif decision['action'].startswith('exit_'):
                # Fermer la position dans l'état
                current_pos = sm.get_current_position()
                if current_pos:
                    sm.update_position(current_pos['type'], 'close', {
                        'exit_price': execution_result.get('price'),
                        'exit_rsi': analysis['rsi_n1'],
                        'pnl': execution_result.get('pnl', 0)
                    })
                    
                    # 📧 NOTIFICATION EMAIL - SORTIE DE POSITION
                    try:
                        exit_price = execution_result.get('price', 'N/A')
                        exit_time = datetime.now().strftime("%d/%m %H:%M")
                        pnl = execution_result.get('pnl', 0)
                        
                        # Déterminer le type de sortie
                        exit_type = "SORTIE"
                        if execution_result.get('exit_type') == 'emergency':
                            exit_type = "SORTIE D'URGENCE"
                        elif execution_result.get('exit_type') == 'control_3h':
                            exit_type = "SORTIE CONTRÔLE 3H"
                        
                        notification_manager.send_trade_notification(
                            action=exit_type,
                            position_type=current_pos['type'],
                            price=f"${exit_price}" if exit_price != 'N/A' else "N/A",
                            datetime_str=exit_time,
                            pnl=pnl
                        )
                        print(f"   📧 Email de notification envoyé pour la sortie de {current_pos['type']}")
                        
                        # Notification spéciale si PnL significatif
                        if pnl != 0:
                            pnl_str = f"${pnl:.2f}" if pnl > 0 else f"${pnl:.2f}"
                            print(f"   💰 PnL réalisé: {pnl_str}")
                            
                    except Exception as e:
                        logger.log_error(f"Erreur lors de l'envoi de la notification email: {e}")
                        print(f"   ⚠️  Erreur notification email: {e}")
        else:
            print("   ❌ Erreur lors de l'exécution")
            logger.log_order_execution(execution_result)
    else:
        print("\n⏸️  AUCUNE ACTION À EXÉCUTER")
    
    # 7. Affichage de l'état du bot
    print("\n" + sm.get_state_summary(candle_buffer))
    logger.log_state_update(sm)
    
    # 8. Monitoring et sauvegarde des données
    try:
        # Sauvegarder les données de monitoring toutes les 4 bougies (1 heure)
        if len(system_monitor.health_history) % 4 == 0:
            system_monitor.save_monitoring_data()
        
        # Afficher un résumé de monitoring toutes les 8 bougies (2 heures)
        if len(system_monitor.health_history) % 8 == 0:
            print("\n📊 RÉSUMÉ MONITORING SYSTÈME")
            system_monitor.print_status()
            
    except Exception as e:
        logger.log_error(f"Erreur lors du monitoring: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    logger.log_bot_start()
    print("BitSniper - Bot de trading BTC/USD sur Kraken Futures (Nouvelle Stratégie)")
    print("Synchronisé sur les bougies 15m. En attente de la prochaine clôture...")
    print("="*60)
    
    # Affichage initial du statut système
    try:
        print("\n📊 STATUT SYSTÈME INITIAL")
        system_monitor.print_status()
    except Exception as e:
        logger.log_error(f"Erreur lors de l'affichage du statut initial: {e}")
    
    try:
        run_every_15min(trading_loop)
    except KeyboardInterrupt:
        logger.log_bot_stop()
        print("\nBot arrêté par l'utilisateur")
        
        # Sauvegarder les données de monitoring avant de quitter
        try:
            system_monitor.save_monitoring_data("final_monitoring_data.json")
            print("Données de monitoring sauvegardées")
        except Exception as e:
            logger.log_error(f"Erreur lors de la sauvegarde finale: {e}")
            
    except Exception as e:
        logger.log_error(f"Erreur fatale: {str(e)}")
        print(f"\n🚨 ERREUR FATALE DÉTECTÉE !")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        
        # 📧 NOTIFICATION EMAIL D'URGENCE - CRASH FATAL
        try:
            import traceback
            stack_trace = traceback.format_exc()
            
            notification_manager.send_crash_notification(
                error_type="CRASH FATAL",
                error_message=str(e),
                stack_trace=stack_trace,
                context="Erreur fatale dans la boucle principale du bot"
            )
            print("   📧 Email d'urgence envoyé pour le crash fatal")
            
        except Exception as email_error:
            logger.log_error(f"Impossible d'envoyer l'email de crash: {email_error}")
            print(f"   ❌ Impossible d'envoyer l'email de crash: {email_error}")
        
        # Sauvegarder les données de monitoring en cas d'erreur fatale
        try:
            system_monitor.save_monitoring_data("error_monitoring_data.json")
            print("   💾 Données de monitoring sauvegardées (erreur fatale)")
        except Exception as save_error:
            logger.log_error(f"Erreur lors de la sauvegarde d'urgence: {save_error}")
            print(f"   ❌ Erreur sauvegarde monitoring: {save_error}")
        
        raise 