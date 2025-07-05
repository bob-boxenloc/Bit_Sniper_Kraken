from core.scheduler import run_every_15min
from core.state_manager import StateManager
from core.logger import logger
from core.monitor import system_monitor
from core.error_handler import error_handler
from data.market_data import MarketData
from data.indicators import get_rsi_with_validation
from trading.kraken_client import KrakenFuturesClient
from trading.trade_manager import TradeManager
from signals.technical_analysis import analyze_candles, check_all_conditions, get_analysis_summary
from signals.decision import decide_action, get_decision_summary
from core.initialization import initialize_bot, is_initialization_ready

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
    print("NOUVELLE BOUGIE 15M - ANALYSE COMPLÈTE")
    print("="*60)
    
    # 1. Récupération des données de marché
    print("\n📊 RÉCUPÉRATION DES DONNÉES")
    
    # Initialiser le gestionnaire d'état
    sm = StateManager()
    
    try:
        md = MarketData()
        
        # Vérifier si on a des données d'initialisation
        if is_initialization_ready():
            print("🔄 Mode hybride : Transition progressive vers données temps réel")
            
            # Récupérer le nombre de bougies Kraken déjà récupérées
            kraken_count = sm.get_kraken_candles_count()
            total_required = 80  # Total requis pour la transition complète
            
            # Calculer combien de bougies Kraken récupérer cette fois
            # On récupère progressivement plus de bougies Kraken
            kraken_to_fetch = min(2 + kraken_count, total_required)
            
            print(f"📈 Progression: {kraken_count}/{total_required} bougies Kraken récupérées")
            print(f"🔄 Récupération de {kraken_to_fetch} bougies Kraken cette fois")
            
            # Récupérer les bougies Kraken temps réel
            current_candles = md.get_ohlcv_15m(limit=kraken_to_fetch)
            
            # Charger les données d'initialisation pour l'historique
            initial_candles, initial_rsi, initial_volume = initialize_bot()
            
            # Calculer combien de bougies historiques utiliser
            # On utilise de moins en moins de données historiques
            historical_to_use = max(0, total_required - kraken_to_fetch)
            historical_candles = initial_candles[:historical_to_use]
            
            # Utiliser les données historiques pour RSI et volume normalisé
            rsi = initial_rsi
            volume_normalized = initial_volume
            rsi_success = True
            rsi_message = f"RSI et volume depuis données historiques + {kraken_to_fetch} bougies Kraken"
            
            # Combiner les données : Kraken temps réel + historiques
            candles = current_candles + historical_candles
            
            print(f"✅ {len(current_candles)} bougies Kraken temps réel")
            print(f"✅ {len(historical_candles)} bougies historiques")
            print(f"✅ Total: {len(candles)} bougies combinées")
            
            # AFFICHER LES BOUGIES KRAKEN TEMPS RÉEL
            print(f"🔍 BOUGIES KRAKEN TEMPS RÉEL (pour décisions):")
            for i, candle in enumerate(current_candles[-2:]):  # Afficher les 2 dernières
                print(f"   N-{2-i}: {candle['datetime']} - Close: {candle['close']} - Volume: {candle['volume']}")
            
            # Mettre à jour la progression
            sm.update_data_progression(kraken_to_fetch)
            
            # Logger la progression
            logger.log_data_progression(sm.get_data_progression())
            
        else:
            print("📈 Récupération des données en temps réel")
            candles = md.get_ohlcv_15m(limit=35)  # On prend 35 bougies pour avoir assez d'historique pour RSI(12)+SMA(14) et Volume MA(20)+SMA(9)
            
            # Validation de l'historique pour le RSI
            rsi_success, rsi, rsi_message = get_rsi_with_validation(candles, period=12)
        
        if not rsi_success:
            logger.log_warning(f"Trading impossible: {rsi_message}")
            print(f"❌ TRADING IMPOSSIBLE: {rsi_message}")
            print("   Le bot attend d'avoir assez d'historique pour calculer le RSI de manière fiable.")
            return
            
    except Exception as e:
        logger.log_error(f"Erreur lors de la récupération des données de marché: {e}")
        print(f"❌ ERREUR RÉCUPÉRATION DONNÉES: {e}")
        print("   Le bot attendra la prochaine bougie pour réessayer.")
        return
    
    logger.log_candle_analysis(candles, rsi_success, rsi_message, sm.get_data_progression())
    print(f"✅ {rsi_message}")
    
    # IMPORTANT: Utiliser les bougies Kraken temps réel pour les décisions
    # Les 2 dernières bougies de la liste sont les bougies Kraken temps réel
    if is_initialization_ready():
        # En mode hybride, les bougies Kraken sont au début de la liste
        kraken_count = sm.get_kraken_candles_count()
        last_candle = current_candles[-1]  # Dernière bougie Kraken
        prev_candle = current_candles[-2]  # Avant-dernière bougie Kraken
    else:
        # En mode normal, utiliser les bougies de la liste combinée
        last_candle = candles[-1]
        prev_candle = candles[-2]
    
    last_rsi = rsi.iloc[-1]
    prev_rsi = rsi.iloc[-2]
    
    print(f"🎯 BOUGIES UTILISÉES POUR DÉCISIONS:")
    print(f"   N-2 ({prev_candle['datetime']}): Close={prev_candle['close']}, Volume={prev_candle['volume']}, RSI={prev_rsi:.2f}")
    print(f"   N-1 ({last_candle['datetime']}): Close={last_candle['close']}, Volume={last_candle['volume']}, RSI={last_rsi:.2f}")
    
    # Calculs pour la stratégie
    volume_n2 = float(prev_candle['volume'])
    volume_n1 = float(last_candle['volume'])
    delta_volume = volume_n1 / volume_n2 if volume_n2 > 0 else 0
    rsi_change = last_rsi - prev_rsi
    
    # 3. Analyse technique complète
    print("\n🔍 ANALYSE TECHNIQUE")
    analysis = analyze_candles(candles, rsi)
    conditions_check = check_all_conditions(analysis)
    analysis_summary = get_analysis_summary(analysis, conditions_check)
    print(analysis_summary)
    logger.log_technical_analysis(analysis, conditions_check)
    
    # 2. Récupération des infos du compte
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
    
    # 4. Prise de décision
    print("\n🎯 DÉCISION DE TRADING")
    decision = decide_action(analysis, conditions_check, account_summary, sm)
    decision_summary = get_decision_summary(decision)
    print(decision_summary)
    logger.log_trading_decision(decision)
    
    # 5. Exécution de la décision (si pas "hold")
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
                position_type = decision['action'].replace('enter_', '')
                sm.update_position(position_type, 'open', {
                    'entry_price': decision['entry_price'],
                    'entry_rsi': decision['entry_rsi'],
                    'size': decision['size']
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
    
    # 6. Affichage de l'état du bot
    print("\n" + sm.get_state_summary())
    logger.log_state_update(sm)
    
    # 7. Monitoring et sauvegarde des données
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
    print("BitSniper - Bot de trading BTC/USD sur Kraken Futures")
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