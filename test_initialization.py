#!/usr/bin/env python3
"""
Script de test pour diagnostiquer l'initialisation
"""

import json
import os
from core.initialization import InitializationManager

def test_initialization():
    print("🔍 DIAGNOSTIC INITIALISATION")
    print("="*50)
    
    # 1. Vérifier si le fichier existe
    file_path = "initial_data.json"
    print(f"1. Fichier existe: {os.path.exists(file_path)}")
    
    if not os.path.exists(file_path):
        print("❌ Fichier non trouvé!")
        return
    
    # 2. Tester le chargement JSON
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        print("✅ Chargement JSON réussi")
    except Exception as e:
        print(f"❌ Erreur JSON: {e}")
        return
    
    # 3. Vérifier la structure
    required_keys = ['description', 'instructions', 'required_periods', 'data']
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        print(f"❌ Clés manquantes: {missing_keys}")
        return
    else:
        print("✅ Structure correcte")
    
    # 4. Vérifier le nombre de périodes
    data_count = len(data['data'])
    required_periods = data['required_periods']
    print(f"   Données: {data_count} bougies")
    print(f"   Requis: {required_periods} bougies")
    
    if data_count != required_periods:
        print(f"❌ Nombre incorrect: {data_count} != {required_periods}")
        return
    else:
        print("✅ Nombre de périodes correct")
    
    # 5. Vérifier la première bougie
    if data['data']:
        first_candle = data['data'][0]
        required_fields = ['datetime', 'close', 'rsi', 'volume_normalized']
        missing_fields = [field for field in required_fields if field not in first_candle]
        
        if missing_fields:
            print(f"❌ Champs manquants dans la première bougie: {missing_fields}")
            return
        else:
            print("✅ Première bougie valide")
            
            # Tester les types
            try:
                float(first_candle['close'])
                float(first_candle['rsi'])
                float(first_candle['volume_normalized'])
                from datetime import datetime
                datetime.fromisoformat(first_candle['datetime'])
                print("✅ Types de données corrects")
            except Exception as e:
                print(f"❌ Erreur de type: {e}")
                return
    
    # 6. Tester la fonction is_ready()
    print("\n🧪 TEST FONCTION is_ready()")
    manager = InitializationManager()
    is_ready = manager.is_ready()
    print(f"is_ready() retourne: {is_ready}")
    
    if not is_ready:
        print("❌ La fonction is_ready() retourne False malgré des données valides!")
        print("   Problème dans la logique de validation...")
    else:
        print("✅ is_ready() fonctionne correctement")

if __name__ == "__main__":
    test_initialization() 