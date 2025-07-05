#!/usr/bin/env python3
"""
BitSniper - Bot de trading automatisé pour Kraken Futures
Utilise RSI(12) avec smoothing SMA(14) et volume normalisé pour les décisions de trading
"""

import time
import sys
from datetime import datetime
from core.logger import get_logger
from core.state_manager import StateManager
from core.scheduler import Scheduler
from data.market_data import MarketDataManager
from data.indicators import TechnicalIndicators
from signals.decision import DecisionEngine
from trading.kraken_client import KrakenFuturesClient
from trading.trade_manager import TradeManager

logger = get_logger(__name__)

def initialize_bot_with_historical_data():
    """Initialise le bot avec les données historiques"""
    logger.info("=== INITIALISATION DU BOT AVEC DONNÉES HISTORIQUES ===")
    
    # Charger le gestionnaire d'état
    state_manager = StateManager()
    
    # Vérifier si déjà initialisé
    if state_manager.is_initialized():
        logger.info("Bot déjà initialisé avec données historiques")
        return True
    
    # Charger les données d'initialisation
    initial_data = state_manager.load_initial_data()
    if not initial_data:
        logger.error("Impossible de charger les données d'initialisation")
        return False
    
    # Initialiser les indicateurs techniques
    indicators = TechnicalIndicators()
    if not indicators.initialize_with_historical_data(initial_data):
        logger.error("Échec de l'initialisation des indicateurs")
        return False
    
    # Marquer comme initialisé
    state_manager.mark_initialized()
    
    logger.info("=== INITIALISATION TERMINÉE AVEC SUCCÈS ===")
    return True

def main():
    """Fonction principale du bot"""
    logger.info("=== DÉMARRAGE DE BITSNIPER ===")
    
    try:
        # Initialiser avec les données historiques
        if not initialize_bot_with_historical_data():
            logger.error("Échec de l'initialisation, arrêt du bot")
            return
        
        # Initialiser les composants
        state_manager = StateManager()
        market_data = MarketDataManager()
        indicators = TechnicalIndicators()
        decision_engine = DecisionEngine(state_manager)
        kraken_client = KrakenFuturesClient()
        trade_manager = TradeManager(kraken_client, state_manager)
        scheduler = Scheduler()
        
        logger.info("Tous les composants initialisés avec succès")
        
        # Boucle principale
        while True:
            try:
                # Attendre la prochaine exécution (toutes les 15 minutes)
                next_run = scheduler.wait_until_next_run()
                logger.info(f"Prochaine exécution à {next_run}")
                
                # Récupérer les données de marché
                candles = market_data.get_ohlcv_15m()
                if not candles:
                    logger.error("Impossible de récupérer les données de marché")
                    continue
                
                # Ajouter la nouvelle bougie aux indicateurs
                if len(candles) >= 2:
                    latest_candle = candles[-2]  # Utiliser N-1 (dernière bougie fermée)
                    indicators.add_candle(
                        timestamp=latest_candle['datetime'],
                        close=float(latest_candle['close']),
                        rsi=float(latest_candle['rsi']),
                        volume_normalized=float(latest_candle['volume_normalized'])
                    )
                
                # Vérifier si les indicateurs sont prêts
                if not indicators.is_ready():
                    logger.warning("Indicateurs pas encore prêts, attente...")
                    continue
                
                # Obtenir les données actuelles
                current_data = indicators.get_latest_data()
                logger.info(f"Données actuelles: {current_data}")
                
                # Prendre une décision
                action = decision_engine.decide_action(
                    current_rsi=current_data['rsi'],
                    current_volume=current_data['volume_normalized'],
                    current_price=current_data['price']
                )
                
                logger.info(f"Décision: {action}")
                
                # Exécuter l'action
                if action != 'hold':
                    trade_manager.execute_action(action, current_data['price'])
                
            except KeyboardInterrupt:
                logger.info("Arrêt demandé par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"Erreur dans la boucle principale: {e}")
                time.sleep(60)  # Attendre 1 minute avant de réessayer
                
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 