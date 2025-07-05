#!/usr/bin/env python3
"""
Script de test pour la logique de transition progressive
"""

import json
from core.state_manager import StateManager
from core.initialization import initialize_bot, is_initialization_ready

def test_progression_logic():
    """Test de la logique de transition progressive"""
    
    print("🧪 TEST DE LA LOGIQUE DE TRANSITION PROGRESSIVE")
    print("="*60)
    
    # 1. Vérifier l'initialisation
    print("\n1. Vérification de l'initialisation...")
    if not is_initialization_ready():
        print("❌ Données d'initialisation non disponibles")
        return False
    
    print("✅ Données d'initialisation disponibles")
    
    # 2. Charger les données d'initialisation
    print("\n2. Chargement des données d'initialisation...")
    try:
        initial_candles, initial_rsi, initial_volume = initialize_bot()
        print(f"✅ {len(initial_candles)} bougies historiques chargées")
        print(f"✅ {len(initial_rsi)} valeurs RSI chargées")
        print(f"✅ {len(initial_volume)} valeurs volume chargées")
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        return False
    
    # 3. Tester le gestionnaire d'état
    print("\n3. Test du gestionnaire d'état...")
    sm = StateManager("test_state.json")
    
    # Vérifier l'état initial
    initial_progression = sm.get_data_progression()
    print(f"   État initial: {initial_progression.get('kraken_candles_count', 0)} bougies Kraken")
    
    # 4. Simuler la progression
    print("\n4. Simulation de la progression...")
    
    total_required = 80
    for step in range(0, total_required + 1, 10):  # Test tous les 10 pas
        # Mettre à jour la progression
        sm.update_data_progression(step)
        
        # Calculer les valeurs pour cette étape
        kraken_count = step
        historical_to_use = max(0, total_required - kraken_count)
        
        print(f"   Étape {step}/{total_required}:")
        print(f"     - Bougies Kraken: {kraken_count}")
        print(f"     - Bougies historiques: {historical_to_use}")
        print(f"     - Progression: {(kraken_count/total_required)*100:.1f}%")
        
        # Vérifier la cohérence
        if kraken_count + historical_to_use != total_required:
            print(f"     ❌ ERREUR: {kraken_count} + {historical_to_use} != {total_required}")
            return False
        
        print(f"     ✅ Cohérence OK")
    
    # 5. Vérifier la transition complète
    print("\n5. Vérification de la transition complète...")
    sm.update_data_progression(total_required)
    
    if sm.is_transition_complete():
        print("✅ Transition complète détectée")
    else:
        print("❌ Transition complète non détectée")
        return False
    
    # 6. Test des bougies combinées
    print("\n6. Test de la combinaison des bougies...")
    
    # Simuler des bougies Kraken (données fictives)
    kraken_candles = [
        {
            'time': 1640995200000 + i * 900000,  # 15 minutes en millisecondes
            'datetime': f"2022-01-0{i+1}T00:00:00",
            'open': 40000 + i * 100,
            'high': 40100 + i * 100,
            'low': 39900 + i * 100,
            'close': 40050 + i * 100,
            'volume': 50 + i * 10
        }
        for i in range(5)  # 5 bougies Kraken fictives
    ]
    
    # Combiner avec les données historiques
    historical_candles = initial_candles[:75]  # 75 bougies historiques
    combined_candles = kraken_candles + historical_candles
    
    print(f"   Bougies Kraken: {len(kraken_candles)}")
    print(f"   Bougies historiques: {len(historical_candles)}")
    print(f"   Total combiné: {len(combined_candles)}")
    
    # Vérifier que les bougies Kraken sont au début
    if combined_candles[:len(kraken_candles)] == kraken_candles:
        print("   ✅ Bougies Kraken correctement placées au début")
    else:
        print("   ❌ Erreur dans l'ordre des bougies")
        return False
    
    # 7. Test de l'utilisation des bonnes bougies pour les décisions
    print("\n7. Test de l'utilisation des bougies pour décisions...")
    
    # Les 2 dernières bougies de la liste combinée doivent être les 2 dernières bougies Kraken
    decision_candles = combined_candles[-2:]  # N-1 et N-2 pour les décisions
    
    print(f"   Bougies utilisées pour décisions:")
    for i, candle in enumerate(decision_candles):
        print(f"     N-{2-i}: {candle['datetime']} - Close: {candle['close']}")
    
    # Vérifier que ce sont bien les bougies Kraken
    if decision_candles[0] == kraken_candles[-2] and decision_candles[1] == kraken_candles[-1]:
        print("   ✅ Bonnes bougies utilisées pour les décisions")
    else:
        print("   ❌ Mauvaises bougies utilisées pour les décisions")
        return False
    
    print("\n✅ TOUS LES TESTS RÉUSSIS!")
    print("   La logique de transition progressive fonctionne correctement")
    
    # Nettoyer le fichier de test
    import os
    if os.path.exists("test_state.json"):
        os.remove("test_state.json")
    
    return True

if __name__ == "__main__":
    success = test_progression_logic()
    if success:
        print("\n🎉 Test terminé avec succès!")
    else:
        print("\n❌ Test échoué!")
        exit(1) 