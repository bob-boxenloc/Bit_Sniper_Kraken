#!/usr/bin/env python3
"""
Test de la méthode RSI Wilder avec les données du rapport.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.indicators import calculate_rsi_wilder

def test_rsi_wilder():
    """Test avec les données du rapport."""
    
    # Données de test du rapport (63 valeurs)
    closes = [
        108078, 107563, 107756, 108042, 108192, 108220, 108135, 108081, 108006,
        108057, 108024, 107897, 107977, 107813, 108076, 108183, 108060, 108005,
        108111, 108040, 108210, 108202, 108216, 108277, 108298, 108437, 108531,
        108295, 108186, 108061, 107889, 107703, 107660, 107923, 107750, 107784,
        107796, 107907, 107962, 107911, 107838, 107872, 107991, 108052, 108034,
        108109, 108159, 108219, 108251, 108199, 108322, 108303, 108250, 108366,
        108424, 108498, 108498, 108415, 108299, 108277, 108362, 108410, 108508
    ]
    
    print("Test RSI Wilder avec les données du rapport")
    print("=" * 50)
    
    # Calculer le RSI Wilder pour la dernière période
    rsi_wilder = calculate_rsi_wilder(closes, length=12)
    
    print(f"RSI Wilder(12) calculé: {rsi_wilder}")
    print(f"RSI Wilder(12) attendu: 64.4649")
    
    if rsi_wilder is not None:
        difference = abs(rsi_wilder - 64.4649)
        print(f"Différence: {difference:.4f}")
        
        if difference < 0.01:
            print("✅ SUCCÈS: RSI Wilder calculé correctement!")
        else:
            print("❌ ÉCHEC: RSI Wilder ne correspond pas à la valeur attendue")
    else:
        print("❌ ÉCHEC: Impossible de calculer le RSI Wilder")
    
    # Test avec les données que vous aviez données
    print("\n" + "=" * 50)
    print("Test avec vos données précédentes:")
    
    test_closes = [
        107907, 107962, 107911, 107838, 107872, 107991, 108052, 108034, 
        108109, 108159, 108219, 108251, 108199
    ]
    
    rsi_test = calculate_rsi_wilder(test_closes, length=12)
    print(f"RSI Wilder(12) pour vos données: {rsi_test}")

if __name__ == "__main__":
    test_rsi_wilder() 