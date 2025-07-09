#!/usr/bin/env python3
"""
Script de test pour vérifier l'approche de ChatGPT sur le calcul du volume BTC
"""

import requests
import time
import json
from datetime import datetime, timedelta

def test_volume_calculation():
    """Test de l'approche ChatGPT pour calculer le volume BTC"""
    
    print("🧪 TEST DE L'APPROCHE CHATGPT POUR LE VOLUME BTC")
    print("=" * 60)
    
    # 1. Récupérer les données candles (OHLCV)
    print("\n📊 1. Récupération des données candles...")
    
    # Timestamp pour les 15 dernières minutes
    end_time = int(time.time())
    start_time = end_time - (15 * 60)  # 15 minutes
    
    candles_url = "https://futures.kraken.com/api/charts/v1/PI_XBTUSD/900"
    candles_params = {
        "from": start_time,
        "to": end_time
    }
    
    try:
        candles_resp = requests.get(candles_url, params=candles_params)
        candles_resp.raise_for_status()
        candles_data = candles_resp.json()
        
        print(f"✅ Candles récupérées: {len(candles_data.get('candles', []))} bougies")
        
        if candles_data.get('candles'):
            latest_candle = candles_data['candles'][-1]
            print(f"   Dernière bougie: {datetime.fromtimestamp(latest_candle['time']/1000)}")
            print(f"   Close: ${latest_candle['close']}")
            print(f"   Volume (contrats): {latest_candle['volume']}")
            print(f"   Count (trades): {latest_candle.get('count', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Erreur candles: {e}")
        return
    
    # 2. Récupérer les analytics trade-volume (USD)
    print("\n💰 2. Récupération des analytics trade-volume...")
    
    analytics_url = "https://futures.kraken.com/api/charts/v1/analytics/PI_XBTUSD/trade-volume"
    analytics_params = {
        "since": start_time,
        "to": end_time,
        "interval": 900  # 15 minutes
    }
    
    try:
        analytics_resp = requests.get(analytics_url, params=analytics_params)
        analytics_resp.raise_for_status()
        analytics_data = analytics_resp.json()
        
        print(f"✅ Analytics récupérées: {len(analytics_data.get('data', []))} points")
        
        if analytics_data.get('data'):
            latest_analytics = analytics_data['data'][-1]
            timestamp, usd_volume = latest_analytics[0], latest_analytics[1]
            print(f"   Timestamp: {datetime.fromtimestamp(timestamp)}")
            print(f"   Volume USD: ${usd_volume:,.2f}")
        
    except Exception as e:
        print(f"❌ Erreur analytics: {e}")
        return
    
    # 3. Calculer le volume BTC approximatif
    print("\n🧮 3. Calcul du volume BTC approximatif...")
    
    if candles_data.get('candles') and analytics_data.get('data'):
        latest_candle = candles_data['candles'][-1]
        latest_analytics = analytics_data['data'][-1]
        
        close_price = float(latest_candle['close'])
        usd_volume = float(latest_analytics[1])
        
        # Calcul approximatif selon ChatGPT
        btc_volume_approx = usd_volume / close_price
        
        print(f"   Close price: ${close_price}")
        print(f"   Volume USD: ${usd_volume:,.2f}")
        print(f"   Volume BTC (calculé): {btc_volume_approx:.4f} BTC")
        
        # Comparer avec le volume des candles
        candle_volume = float(latest_candle['volume'])
        print(f"   Volume candles (contrats): {candle_volume}")
        
        # Calculer le ratio
        if candle_volume > 0:
            ratio = btc_volume_approx / candle_volume
            print(f"   Ratio BTC/Contrats: {ratio:.6f}")
    
    # 4. Test de l'endpoint history (selon ChatGPT)
    print("\n🔍 4. Test de l'endpoint history (selon ChatGPT)...")
    
    history_url = "https://futures.kraken.com/api/history/v3/public/PI_XBTUSD"
    history_params = {
        "since": start_time * 1000,  # En millisecondes
        "to": end_time * 1000
    }
    
    try:
        history_resp = requests.get(history_url, params=history_params)
        print(f"   Status: {history_resp.status_code}")
        
        if history_resp.status_code == 200:
            history_data = history_resp.json()
            print(f"   ✅ Endpoint accessible!")
            print(f"   Données: {json.dumps(history_data, indent=2)[:500]}...")
        else:
            print(f"   ❌ Endpoint non accessible: {history_resp.text}")
            
    except Exception as e:
        print(f"   ❌ Erreur endpoint history: {e}")
    
    print("\n" + "=" * 60)
    print("📋 RÉSUMÉ DE L'APPROCHE CHATGPT")
    print("=" * 60)
    
    print("✅ Ce qui fonctionne:")
    print("   - Endpoint /candles pour OHLCV")
    print("   - Endpoint /analytics/trade-volume pour volume USD")
    print("   - Calcul approximatif: Volume BTC = Volume USD / Prix de clôture")
    
    print("\n❌ Ce qui ne fonctionne pas:")
    print("   - Endpoint /history/v3/public/PI_XBTUSD (404)")
    print("   - Récupération des trades bruts pour calcul exact")
    
    print("\n💡 Solution pratique:")
    print("   Utiliser trade-volume USD + close price pour approximer le volume BTC")
    print("   Accepter une approximation plutôt qu'un calcul exact")

if __name__ == "__main__":
    test_volume_calculation() 