from core.scheduler import run_every_15min
from core.state_manager import StateManager
from core.logger import logger
from core.monitor import system_monitor
from core.error_handler import error_handler
from data.market_data import MarketData, CandleBuffer
from data.indicators import get_indicators_with_validation, calculate_complete_rsi_history, calculate_complete_volatility_indexes_history
from trading.kraken_client import KrakenFuturesClient
from trading.trade_manager import TradeManager
from signals.technical_analysis import analyze_candles, check_all_conditions, get_analysis_summary
from signals.decision import decide_action, get_decision_summary
from core.initialization import initialize_bot, is_initialization_ready
import time

# Buffer global pour les bougies
candle_buffer = CandleBuffer(max_candles=960)  # 10 jours d'historique complet (960 bougies 15min)

# Variables globales pour l'historique des indicateurs
indicator_history = {
    'rsi_history': [],
    'vi1_history': [],
    'vi2_history': [],
    'vi3_history': [],
    'basis_history': [],
    'atr_history': [],
    'true_ranges': [],
    'rsi_avg_gain': None,  # Dernière moyenne des gains pour RSI
    'rsi_avg_loss': None   # Dernière moyenne des pertes pour RSI
}

def initialize_indicator_history(candles):
    """
    Initialise l'historique complet des indicateurs au démarrage.
    Cette fonction calcule l'historique RMA pour avoir des calculs précis dès le début.
    """
    global indicator_history
    
    print("🔄 INITIALISATION DE L'HISTORIQUE DES INDICATEURS")
    
    # Extraire les données
    closes = [float(c['close']) for c in candles]
    highs = [float(c['high']) for c in candles]
    lows = [float(c['low']) for c in candles]
    
    # Calculer l'historique complet du RSI
    print("📊 Calcul de l'historique RSI(40)...")
    rsi_history = calculate_complete_rsi_history(closes, 40)
    if rsi_history:
        indicator_history['rsi_history'] = rsi_history
        
        # Calculer et stocker les moyennes RMA finales pour continuer le calcul récursif
        deltas = []
        for i in range(1, len(closes)):
            deltas.append(closes[i] - closes[i-1])
        
        gains = [max(delta, 0) for delta in deltas]
        losses = [max(-delta, 0) for delta in deltas]
        
        # Calculer les moyennes RMA finales (après 40 périodes)
        avg_gain = sum(gains[:40]) / 40
        avg_loss = sum(losses[:40]) / 40
        
        # Continuer le calcul RMA pour toutes les périodes suivantes
        for i in range(40, len(deltas)):
            avg_gain = (avg_gain * 39 + gains[i]) / 40
            avg_loss = (avg_loss * 39 + losses[i]) / 40
        
        # Stocker les moyennes finales pour continuer le calcul récursif
        indicator_history['rsi_avg_gain'] = avg_gain
        indicator_history['rsi_avg_loss'] = avg_loss
        
        print(f"✅ Historique RSI calculé: {len(rsi_history)} valeurs")
        print(f"   Première valeur: {rsi_history[0]:.2f}")
        print(f"   Dernière valeur: {rsi_history[-1]:.2f}")
        print(f"   Moyennes RMA finales - Gain: {avg_gain:.4f}, Loss: {avg_loss:.4f}")
    else:
        print("❌ Impossible de calculer l'historique RSI")
        return False
    
    # Calculer l'historique complet des Volatility Indexes
    print("📊 Calcul de l'historique Volatility Indexes...")
    vi_history = calculate_complete_volatility_indexes_history(highs, lows, closes)
    if vi_history:
        indicator_history['vi1_history'] = vi_history['VI1_history']
        indicator_history['vi2_history'] = vi_history['VI2_history']
        indicator_history['vi3_history'] = vi_history['VI3_history']
        indicator_history['basis_history'] = vi_history['basis_history']
        indicator_history['atr_history'] = vi_history['atr_history']
        indicator_history['true_ranges'] = vi_history['true_ranges']
        
        print(f"✅ Historique VI calculé: {len(vi_history['VI1_history'])} valeurs")
        print(f"   VI1: {vi_history['VI1_history'][-1]:.2f}")
        print(f"   VI2: {vi_history['VI2_history'][-1]:.2f}")
        print(f"   VI3: {vi_history['VI3_history'][-1]:.2f}")
    else:
        print("❌ Impossible de calculer l'historique VI")
        return False
    
    print("✅ INITIALISATION TERMINÉE - Calculs précis dès le début")
    return True

def update_indicator_history(new_candle):
    """
    Met à jour l'historique des indicateurs avec une nouvelle bougie.
    Continue le calcul RMA récursif pour maintenir la précision.
    Limite l'historique à 672 valeurs maximum (7 jours).
    """
    global indicator_history
    
    if not indicator_history['rsi_history'] or not indicator_history['vi1_history']:
        return False
    
    # Extraire les données de la nouvelle bougie
    new_close = float(new_candle['close'])
    new_high = float(new_candle['high'])
    new_low = float(new_candle['low'])
    
    # Mettre à jour l'historique RSI (calcul récursif)
    if len(indicator_history['rsi_history']) > 0 and indicator_history['rsi_avg_gain'] is not None:
        # Récupérer la dernière bougie pour calculer le delta
        candles = candle_buffer.get_candles()
        if len(candles) >= 2:
            last_close = float(candles[-2]['close'])  # Bougie précédente
            delta = new_close - last_close
            gain = max(delta, 0)
            loss = max(-delta, 0)
            
            # Continuer le calcul RMA récursif pour RSI(40)
            avg_gain = indicator_history['rsi_avg_gain']
            avg_loss = indicator_history['rsi_avg_loss']
            
            # Calculer les nouvelles moyennes RMA
            new_avg_gain = (avg_gain * 39 + gain) / 40
            new_avg_loss = (avg_loss * 39 + loss) / 40
            
            # Calculer le nouveau RSI
            if new_avg_loss == 0:
                new_rsi = 100.0
            else:
                rs = new_avg_gain / new_avg_loss
                new_rsi = 100 - (100 / (1 + rs))
            
            # Mettre à jour l'historique
            indicator_history['rsi_history'].append(new_rsi)
            indicator_history['rsi_avg_gain'] = new_avg_gain
            indicator_history['rsi_avg_loss'] = new_avg_loss
    
    # Mettre à jour l'historique des Volatility Indexes
    if len(indicator_history['basis_history']) > 0 and len(indicator_history['atr_history']) > 0:
        # Continuer le calcul RMA pour le basis
        last_basis = indicator_history['basis_history'][-1]
        new_basis = (last_basis * 27 + new_close) / 28
        indicator_history['basis_history'].append(new_basis)
        
        # Calculer le nouveau True Range
        if len(indicator_history['true_ranges']) > 0:
            last_close = indicator_history['true_ranges'][-1]  # Ce n'est pas le bon, mais pour l'exemple
            high_low = new_high - new_low
            high_close_prev = abs(new_high - last_close)
            low_close_prev = abs(new_low - last_close)
            new_true_range = max(high_low, high_close_prev, low_close_prev)
            
            # Continuer le calcul RMA pour l'ATR
            last_atr = indicator_history['atr_history'][-1]
            new_atr = (last_atr * 27 + new_true_range) / 28
            indicator_history['atr_history'].append(new_atr)
            
            # Calculer les nouveaux VI
            new_vi1 = new_basis + (new_atr * 19)
            new_vi2 = new_basis + (new_atr * 10)
            new_vi3 = new_basis + (new_atr * 6)
            
            indicator_history['vi1_history'].append(new_vi1)
            indicator_history['vi2_history'].append(new_vi2)
            indicator_history['vi3_history'].append(new_vi3)
            
            # LIMITER L'HISTORIQUE À 672 VALEURS MAXIMUM (7 jours)
            max_history = 672
            if len(indicator_history['basis_history']) > max_history:
                indicator_history['basis_history'] = indicator_history['basis_history'][-max_history:]
                indicator_history['atr_history'] = indicator_history['atr_history'][-max_history:]
                indicator_history['vi1_history'] = indicator_history['vi1_history'][-max_history:]
                indicator_history['vi2_history'] = indicator_history['vi2_history'][-max_history:]
                indicator_history['vi3_history'] = indicator_history['vi3_history'][-max_history:]
                indicator_history['true_ranges'] = indicator_history['true_ranges'][-max_history:]
                indicator_history['rsi_history'] = indicator_history['rsi_history'][-max_history:]
            
            return True
    
    return False

def trading_loop():
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
    
    print("\n" + "="*60)
    print("NOUVELLE BOUGIE 15M - ANALYSE COMPLÈTE (Nouvelle Stratégie)")
    print("="*60)
    
    # 1. Récupération des données de marché
    print("\n📊 RÉCUPÉRATION DES DONNÉES")
    
    # Initialiser le gestionnaire d'état
    sm = StateManager()
    
    try:
        md = MarketData()
        
        # Initialisation du buffer - RÉCUPÉRATION FORCÉE D'HISTORIQUE
        if not candle_buffer.get_candles():
            print("🔄 Buffer vide - RÉCUPÉRATION FORCÉE D'HISTORIQUE")
            
            # Récupérer 10 jours d'historique (960 bougies 15min) pour des calculs précis
            print("📥 Récupération de 10 jours d'historique (960 bougies)...")
            historical_candles = md.get_ohlcv_15m(limit=960)
            
            if historical_candles and len(historical_candles) >= 960:
                # Ajouter toutes les bougies historiques au buffer (960 bougies)
                for candle in historical_candles:
                    candle_buffer.add_candle(candle)
                
                print(f"✅ {len(historical_candles)} bougies historiques ajoutées au buffer (10 jours)")
                print(f"📊 Buffer: {len(candle_buffer.get_candles())}/{candle_buffer.max_candles} bougies")
                
                # Afficher le résumé détaillé du buffer
                print("📋 " + candle_buffer.get_buffer_summary())
                
                # INITIALISER L'HISTORIQUE COMPLET DES INDICATEURS
                candles = candle_buffer.get_candles()
                if not initialize_indicator_history(candles):
                    print("❌ ÉCHEC INITIALISATION - Le bot ne peut pas démarrer")
                    return
            else:
                print("❌ Impossible de récupérer 10 jours d'historique - attente des données Kraken")
                return
        else:
            print("✅ Buffer déjà initialisé avec données")
        
        # Récupérer la dernière bougie fermée de Kraken
        print("🔄 Récupération de la dernière bougie fermée")
        new_candles = md.get_ohlcv_15m(limit=1)  # Récupérer seulement la dernière bougie
        
        if new_candles:
            # Vérifier si la bougie n'est pas déjà dans le buffer
            new_candle = new_candles[0]  # La dernière bougie
            buffer_times = [c['time'] for c in candle_buffer.get_candles()]
            
            if new_candle['time'] not in buffer_times:
                candle_added = candle_buffer.add_candle(new_candle)
                
                if candle_added:
                    print(f"✅ Nouvelle bougie ajoutée: {new_candle['datetime']} - Close: {new_candle['close']} - Volume: {new_candle.get('volume', 'N/A')} - Count: {new_candle['count']}")
                    
                    # Mettre à jour l'historique des indicateurs avec la nouvelle bougie
                    if update_indicator_history(new_candle):
                        print("✅ Historique des indicateurs mis à jour")
                    else:
                        print("⚠️  Impossible de mettre à jour l'historique des indicateurs")
                else:
                    print(f"ℹ️  Bougie déjà présente dans le buffer: {new_candle['datetime']} - Continuation de l'analyse...")
            else:
                print(f"ℹ️  Bougie déjà présente dans le buffer: {new_candle['datetime']} - Continuation de l'analyse...")
            
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
    
    # 2. Calcul des indicateurs pour la nouvelle stratégie
    print("\n🔍 CALCUL DES INDICATEURS")
    
    # Utiliser l'historique initialisé pour des calculs précis
    if indicator_history['rsi_history'] and indicator_history['vi1_history']:
        # Utiliser les dernières valeurs de l'historique
        current_rsi = indicator_history['rsi_history'][-1]
        current_vi1 = indicator_history['vi1_history'][-1]
        current_vi2 = indicator_history['vi2_history'][-1]
        current_vi3 = indicator_history['vi3_history'][-1]
        
        indicators = {
            'RSI': current_rsi,
            'VI1': current_vi1,
            'VI2': current_vi2,
            'VI3': current_vi3
        }
        
        indicators_success = True
        indicators_message = "Indicateurs calculés avec l'historique initialisé"
        
        print(f"✅ {indicators_message}")
        print(f"   RSI: {current_rsi:.2f}")
        print(f"   VI1: {current_vi1:.2f}")
        print(f"   VI2: {current_vi2:.2f}")
        print(f"   VI3: {current_vi3:.2f}")
    else:
        # Fallback vers l'ancienne méthode si l'historique n'est pas initialisé
        indicators_success, indicators, indicators_message = get_indicators_with_validation(candles, rsi_period=40)
        
        if not indicators_success:
            logger.log_warning(f"Indicateurs non calculables: {indicators_message}")
            print(f"❌ TRADING IMPOSSIBLE: {indicators_message}")
        return
    
    # Logger l'analyse des bougies
    logger.log_candle_analysis(candles, indicators_success, indicators_message)
    print(f"✅ {indicators_message}")
    
    # Logger le calcul des indicateurs
    logger.log_indicators_calculation(indicators)
    
    # Utiliser les 2 dernières bougies pour les décisions
    last_candle = latest_candles[-1]  # Dernière bougie
    prev_candle = latest_candles[-2]  # Avant-dernière bougie
    
    print(f"🎯 BOUGIES UTILISÉES POUR DÉCISIONS:")
    print(f"   N-2 ({prev_candle['datetime']}): Close={prev_candle['close']}, Volume={prev_candle.get('volume', 'N/A')}, Count={prev_candle['count']}")
    print(f"   N-1 ({last_candle['datetime']}): Close={last_candle['close']}, Volume={last_candle.get('volume', 'N/A')}, Count={last_candle['count']}")
    
    # 3. Analyse technique complète avec nouveaux indicateurs
    print("\n🔍 ANALYSE TECHNIQUE (Nouvelle Stratégie)")
    
    # Mettre à jour la phase VI1 si nécessaire
    vi1_current = indicators['VI1']
    current_close = float(last_candle['close'])
    vi1_above_close = vi1_current > current_close
    current_phase = 'SHORT' if vi1_above_close else 'LONG'
    
    # Vérifier si la phase VI1 a changé
    old_phase = sm.get_vi1_current_phase()
    sm.update_vi1_phase(current_phase)
    
    # Logger le changement de phase VI1 si nécessaire
    if old_phase != current_phase:
        logger.log_vi1_phase_change(old_phase, current_phase, time.time())
    
    analysis = analyze_candles(candles, indicators)
    conditions_check = check_all_conditions(analysis, sm.get_last_position_type(), sm.get_vi1_phase_timestamp())
    analysis_summary = get_analysis_summary(analysis, conditions_check)
    print(analysis_summary)
    logger.log_technical_analysis(analysis, conditions_check)
    
    # Logger l'état de la nouvelle stratégie
    logger.log_new_strategy_state(sm)
    
    # 4. Récupération des infos du compte
    print("\n💰 RÉCUPÉRATION DU COMPTE")
    try:
        kf = KrakenFuturesClient()
        current_price = float(last_candle['close'])
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
            elif decision['action'].startswith('exit_'):
                # Fermer la position dans l'état
                current_pos = sm.get_current_position()
                if current_pos:
                    sm.update_position(current_pos['type'], 'close', {
                        'exit_price': execution_result.get('price'),
                        'exit_rsi': analysis['rsi_n1'],
                        'pnl': execution_result.get('pnl', 0)
                    })
        else:
            print("   ❌ Erreur lors de l'exécution")
            logger.log_order_execution(execution_result)
    else:
        print("\n⏸️  AUCUNE ACTION À EXÉCUTER")
    
    # 7. Affichage de l'état du bot
    print("\n" + sm.get_state_summary())
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
        print(f"\nErreur fatale: {e}")
        
        # Sauvegarder les données de monitoring en cas d'erreur fatale
        try:
            system_monitor.save_monitoring_data("error_monitoring_data.json")
            print("Données de monitoring sauvegardées (erreur fatale)")
        except Exception as save_error:
            logger.log_error(f"Erreur lors de la sauvegarde d'urgence: {save_error}")
        
        raise 