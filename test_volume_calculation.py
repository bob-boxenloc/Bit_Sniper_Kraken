#!/usr/bin/env python3
"""
Script de test pour vérifier l'approche de ChatGPT sur le calcul du volume BTC
"""

import requests
import time
import json

def test_kraken_api():
    """Test direct de l'API Kraken pour voir les données retournées"""
    
    base_url = "https://futures.kraken.com/api/charts/v1"
    symbol = "PI_XBTUSD"
    
    # Test 1: Endpoint trade standard
    print("=== TEST 1: Endpoint /trade/{symbol}/900 ===")
    end_time = int(time.time())
    start_time = end_time - (5 * 15 * 60)  # 5 bougies 15m
    
    url = f"{base_url}/trade/{symbol}/900"
    params = {
        "from": start_time,
        "to": end_time
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"URL: {response.url}")
        print(f"Data keys: {list(data.keys())}")
        
        if 'candles' in data:
            print(f"Nombre de bougies: {len(data['candles'])}")
            if data['candles']:
                first_candle = data['candles'][0]
                print(f"Première bougie: {json.dumps(first_candle, indent=2)}")
                
                # Vérifier si volume est présent
                if 'volume' in first_candle:
                    print(f"✅ Volume présent: {first_candle['volume']}")
                else:
                    print("❌ Volume absent")
                    
                if 'count' in first_candle:
                    print(f"Count: {first_candle['count']}")
                else:
                    print("❌ Count absent")
        else:
            print("❌ Pas de 'candles' dans la réponse")
            
    except Exception as e:
        print(f"Erreur: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Endpoint analytics trade-volume
    print("=== TEST 2: Endpoint analytics trade-volume ===")
    
    url = f"{base_url}/analytics/{symbol}/trade-volume"
    params = {
        "since": start_time,
        "to": end_time,
        "interval": 900
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"URL: {response.url}")
        print(f"Data keys: {list(data.keys())}")
        
        # Afficher le contenu complet pour voir la structure
        print(f"Contenu complet: {json.dumps(data, indent=2)}")
        
        if 'result' in data:
            print(f"✅ 'result' présent")
            result = data['result']
            print(f"Type de result: {type(result)}")
            if isinstance(result, dict):
                print(f"Keys de result: {list(result.keys())}")
            elif isinstance(result, list):
                print(f"Nombre d'éléments dans result: {len(result)}")
                if result:
                    print(f"Premier élément: {result[0]}")
        else:
            print("❌ Pas de 'result' dans la réponse")
            
    except Exception as e:
        print(f"Erreur: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Endpoint analytics trade-count
    print("=== TEST 3: Endpoint analytics trade-count ===")
    
    url = f"{base_url}/analytics/{symbol}/trade-count"
    params = {
        "since": start_time,
        "to": end_time,
        "interval": 900
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"URL: {response.url}")
        print(f"Data keys: {list(data.keys())}")
        
        # Afficher le contenu complet pour voir la structure
        print(f"Contenu complet: {json.dumps(data, indent=2)}")
        
        if 'result' in data:
            print(f"✅ 'result' présent")
            result = data['result']
            print(f"Type de result: {type(result)}")
            if isinstance(result, dict):
                print(f"Keys de result: {list(result.keys())}")
            elif isinstance(result, list):
                print(f"Nombre d'éléments dans result: {len(result)}")
                if result:
                    print(f"Premier élément: {result[0]}")
        else:
            print("❌ Pas de 'result' dans la réponse")
            
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    test_kraken_api() 