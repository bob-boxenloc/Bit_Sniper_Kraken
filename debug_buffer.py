#!/usr/bin/env python3
"""
Script de debug pour accéder aux données du buffer
Usage: python3 debug_buffer.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.market_data import CandleBuffer

def main():
    # Créer une instance du buffer
    buffer = CandleBuffer(max_candles=1920)
    
    print("📊 ACCÈS AUX DONNÉES DU BUFFER")
    print("=" * 50)
    
    # Récupérer les bougies
    candles = buffer.get_candles()
    
    if not candles:
        print("❌ Buffer vide")
        return
    
    print(f"✅ Buffer contient {len(candles)} bougies")
    print()
    
    # Afficher le statut
    status = buffer.get_status()
    print(f"📊 STATUT:")
    print(f"   Total: {status['total_candles']}/{status['max_candles']} bougies")
    print(f"   Plein: {status['is_full']}")
    print(f"   Dernière bougie: {status['latest_candle']}")
    print()
    
    # Afficher le résumé
    summary = buffer.get_buffer_summary()
    print(f"📋 RÉSUMÉ:")
    print(summary)
    print()
    
    # Afficher les 5 dernières bougies
    print("🕐 5 DERNIÈRES BOUGIES:")
    latest = buffer.get_latest_candles(5)
    for i, candle in enumerate(latest):
        print(f"   {i+1}. {candle['datetime']} - Close: {candle['close']} - Volume: {candle.get('volume', 'N/A')}")
    print()
    
    # Afficher les 5 premières bougies
    print("🕐 5 PREMIÈRES BOUGIES:")
    for i, candle in enumerate(candles[:5]):
        print(f"   {i+1}. {candle['datetime']} - Close: {candle['close']} - Volume: {candle.get('volume', 'N/A')}")
    print()
    
    # Statistiques des prix
    closes = [float(c['close']) for c in candles]
    highs = [float(c['high']) for c in candles]
    lows = [float(c['low']) for c in candles]
    
    print("📈 STATISTIQUES:")
    print(f"   Close min: ${min(closes):.2f}")
    print(f"   Close max: ${max(closes):.2f}")
    print(f"   High max: ${max(highs):.2f}")
    print(f"   Low min: ${min(lows):.2f}")
    print(f"   Close actuel: ${closes[-1]:.2f}")

if __name__ == "__main__":
    main() 