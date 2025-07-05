#!/usr/bin/env python3
"""
Script de test pour vérifier l'initialisation avec données historiques
"""

import json
from core.state_manager import StateManager
from data.indicators import TechnicalIndicators
from core.logger import get_logger

logger = get_logger(__name__)

def test_initialization():
    """Teste l'initialisation avec les données historiques"""
    logger.info("=== TEST D'INITIALISATION ===")
    
    # Test 1: Chargement des données
    logger.info("Test 1: Chargement des données d'initialisation")
    state_manager = StateManager()
    initial_data = state_manager.load_initial_data()
    
    if not initial_data:
        logger.error("❌ Échec du chargement des données")
        return False
    
    logger.info(f"✅ Données chargées: {len(initial_data)} bougies")
    
    # Test 2: Validation des données
    logger.info("Test 2: Validation des données")
    if len(initial_data) < 27:
        logger.error(f"❌ Données insuffisantes: {len(initial_data)} bougies (minimum 27)")
        return False
    
    # Vérifier le format
    for i, candle in enumerate(initial_data):
        required_fields = ['datetime', 'close', 'rsi', 'volume_normalized']
        missing_fields = [field for field in required_fields if field not in candle]
        if missing_fields:
            logger.error(f"❌ Bougie {i} manque: {missing_fields}")
            return False
    
    logger.info("✅ Format des données valide")
    
    # Test 3: Initialisation des indicateurs
    logger.info("Test 3: Initialisation des indicateurs")
    indicators = TechnicalIndicators()
    
    if not indicators.initialize_with_historical_data(initial_data):
        logger.error("❌ Échec de l'initialisation des indicateurs")
        return False
    
    logger.info("✅ Indicateurs initialisés")
    
    # Test 4: Vérification des données
    logger.info("Test 4: Vérification des données")
    
    current_data = indicators.get_latest_data()
    logger.info(f"Données actuelles: {current_data}")
    
    if not indicators.is_ready():
        logger.error("❌ Indicateurs pas prêts")
        return False
    
    logger.info("✅ Indicateurs prêts")
    
    # Test 5: Affichage des dernières valeurs
    logger.info("Test 5: Affichage des dernières valeurs")
    logger.info(f"Prix actuel: {indicators.get_current_price():.2f}")
    logger.info(f"RSI actuel: {indicators.get_current_rsi():.2f}")
    logger.info(f"Volume normalisé actuel: {indicators.get_current_volume_normalized():.2f}")
    
    # Test 6: Test d'ajout d'une nouvelle bougie
    logger.info("Test 6: Test d'ajout d'une nouvelle bougie")
    indicators.add_candle(
        timestamp="2025-07-05T12:00:00",
        close=108200.0,
        rsi=52.5,
        volume_normalized=15.0
    )
    
    logger.info(f"Nouveau prix: {indicators.get_current_price():.2f}")
    logger.info(f"Nouveau RSI: {indicators.get_current_rsi():.2f}")
    logger.info(f"Nouveau volume: {indicators.get_current_volume_normalized():.2f}")
    
    logger.info("✅ Test d'ajout réussi")
    
    # Test 7: Marquer comme initialisé
    logger.info("Test 7: Marquage comme initialisé")
    state_manager.mark_initialized()
    
    if state_manager.is_initialized():
        logger.info("✅ Bot marqué comme initialisé")
    else:
        logger.error("❌ Échec du marquage")
        return False
    
    logger.info("=== TOUS LES TESTS RÉUSSIS ===")
    return True

if __name__ == "__main__":
    success = test_initialization()
    if success:
        print("\n🎉 Initialisation réussie ! Le bot est prêt à fonctionner.")
    else:
        print("\n❌ Échec de l'initialisation. Vérifiez les logs ci-dessus.") 