from core.scheduler import run_every_15min
from core.state_manager import StateManager
from core.logger import logger
from core.monitor import system_monitor
from core.error_handler import error_handler
from data.market_data import MarketData, CandleBuffer
from data.indicators import get_indicators_with_validation
from trading.kraken_client import KrakenFuturesClient
from trading.trade_manager import TradeManager
from signals.technical_analysis import analyze_candles, check_all_conditions, get_analysis_summary
from signals.decision import decide_action, get_decision_summary
from core.initialization import initialize_bot, is_initialization_ready
import time

# Buffer global pour les bougies
candle_buffer = CandleBuffer(max_candles=50)  # Augmenté pour RSI(40) + ATR(28)

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
            
            # Récupérer 60 bougies historiques pour avoir assez de données
            print("📥 Récupération de 60 bougies historiques...")
            historical_candles = md.get_ohlcv_15m(limit=60)
            
            if historical_candles and len(historical_candles) >= 50:
                # Ajouter toutes les bougies historiques au buffer
                for candle in historical_candles:
                    candle_buffer.add_candle(candle)
                
                print(f"✅ {len(historical_candles)} bougies historiques ajoutées au buffer")
                print(f"📊 Buffer: {len(candle_buffer.get_candles())}/{candle_buffer.max_candles} bougies")
                
                # Afficher le résumé détaillé du buffer
                print("📋 " + candle_buffer.get_buffer_summary())
            else:
                print("❌ Impossible de récupérer l'historique - attente des données Kraken")
                return
        else:
            print("✅ Buffer déjà initialisé avec données")
        
        # Récupérer les dernières bougies fermées de Kraken (mise à jour)
        print("🔄 Récupération des dernières bougies fermées")
        new_candles = md.get_ohlcv_15m(limit=5)  # Récupérer 5 bougies pour avoir assez de données fermées
        
        if new_candles:
            # Utiliser la dernière bougie fermée (celle avec le volume le plus élevé parmi les récentes)
            new_candle = new_candles[-1]  # La dernière bougie fermée
            candle_buffer.add_candle(new_candle)
            
            print(f"✅ Nouvelle bougie ajoutée: {new_candle['datetime']} - Close: {new_candle['close']} - Volume: {new_candle.get('volume', 'N/A')} - Count: {new_candle['count']}")
            
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
                    print("   Le bot attendra la prochaine bougie fermée.")
                    return
        
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
    
    # Validation de l'historique pour les nouveaux indicateurs
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