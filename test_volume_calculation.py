#!/usr/bin/env python3
"""
Script de test pour vérifier l'approche de ChatGPT sur le calcul du volume BTC
"""

import requests
import time
import json
from kraken.futures import Market

def test_kraken_api():
    """Test direct de l'API Kraken pour voir les données retournées"""
    
    base_url = "https://futures.kraken.com/api/charts/v1"
    symbol = "PI_XBTUSD"
    
    # Test 1: Endpoint OHLC standard (celui qui devrait avoir le volume)
    print("=== TEST 1: Endpoint OHLC standard ===")
    end_time = int(time.time())
    start_time = end_time - (5 * 15 * 60)  # 5 bougies 15m
    
    url = f"{base_url}/{symbol}/900"  # Endpoint OHLC standard
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
    
    # Test 2: Endpoint trade (celui qui ne marche pas)
    print("=== TEST 2: Endpoint /trade/{symbol}/900 ===")
    
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
                
                if 'volume' in first_candle:
                    print(f"✅ Volume présent: {first_candle['volume']}")
                else:
                    print("❌ Volume absent")
        else:
            print("❌ Pas de 'candles' dans la réponse")
            
    except Exception as e:
        print(f"Erreur: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: SDK Kraken pour OHLC (corrigé selon la doc)
    print("=== TEST 3: SDK Kraken OHLC (corrigé) ===")
    
    try:
        # Initialiser le client SDK
        client = Market()
        
        # Récupérer les données OHLC via le SDK (selon la doc)
        # get_ohlc(symbol, resolution, since=None, to=None)
        ohlc_data = client.get_ohlc(symbol, resolution=15, since=start_time)
        
        print(f"Type de réponse SDK: {type(ohlc_data)}")
        print(f"Clés de la réponse: {list(ohlc_data.keys()) if isinstance(ohlc_data, dict) else 'Pas un dict'}")
        
        if isinstance(ohlc_data, dict) and 'candles' in ohlc_data:
            candles = ohlc_data['candles']
            print(f"Nombre de bougies SDK: {len(candles)}")
            
            if candles:
                first_candle = candles[0]
                print(f"Première bougie SDK: {json.dumps(first_candle, indent=2)}")
                
                # Vérifier si volume est présent
                if 'volume' in first_candle:
                    print(f"✅ Volume présent dans SDK: {first_candle['volume']}")
                else:
                    print("❌ Volume absent dans SDK")
                    
                if 'count' in first_candle:
                    print(f"Count dans SDK: {first_candle['count']}")
                else:
                    print("❌ Count absent dans SDK")
        else:
            print(f"Réponse SDK complète: {json.dumps(ohlc_data, indent=2)}")
            
    except Exception as e:
        print(f"Erreur SDK: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 4: SDK Kraken avec différents paramètres
    print("=== TEST 4: SDK Kraken avec différents paramètres ===")
    
    try:
        client = Market()
        
        # Essayer sans paramètres
        print("Test 1: Sans paramètres")
        ohlc_data = client.get_ohlc(symbol)
        print(f"Type: {type(ohlc_data)}")
        if isinstance(ohlc_data, dict):
            print(f"Clés: {list(ohlc_data.keys())}")
            if 'candles' in ohlc_data and ohlc_data['candles']:
                first_candle = ohlc_data['candles'][0]
                print(f"Volume présent: {'volume' in first_candle}")
                if 'volume' in first_candle:
                    print(f"Volume: {first_candle['volume']}")
        
        # Essayer avec resolution=900 (15 minutes en secondes)
        print("\nTest 2: Avec resolution=900")
        ohlc_data = client.get_ohlc(symbol, resolution=900)
        print(f"Type: {type(ohlc_data)}")
        if isinstance(ohlc_data, dict):
            print(f"Clés: {list(ohlc_data.keys())}")
            if 'candles' in ohlc_data and ohlc_data['candles']:
                first_candle = ohlc_data['candles'][0]
                print(f"Volume présent: {'volume' in first_candle}")
                if 'volume' in first_candle:
                    print(f"Volume: {first_candle['volume']}")
                    
    except Exception as e:
        print(f"Erreur SDK: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 5: Endpoint analytics trade-volume
    print("=== TEST 5: Endpoint analytics trade-volume ===")
    
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
        
        if 'result' in data:
            print(f"✅ 'result' présent")
            result = data['result']
            print(f"Type de result: {type(result)}")
            if isinstance(result, dict):
                print(f"Keys de result: {list(result.keys())}")
                if 'data' in result and 'timestamp' in result:
                    print(f"Volumes USD: {result['data']}")
                    print(f"Timestamps: {result['timestamp']}")
        else:
            print("❌ Pas de 'result' dans la réponse")
            
    except Exception as e:
        print(f"Erreur: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 6: Endpoint analytics trade-count
    print("=== TEST 6: Endpoint analytics trade-count ===")
    
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
        
        if 'result' in data:
            print(f"✅ 'result' présent")
            result = data['result']
            print(f"Type de result: {type(result)}")
            if isinstance(result, dict):
                print(f"Keys de result: {list(result.keys())}")
                if 'data' in result and 'timestamp' in result:
                    print(f"Counts: {result['data']}")
                    print(f"Timestamps: {result['timestamp']}")
        else:
            print("❌ Pas de 'result' dans la réponse")
            
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    test_kraken_api() 