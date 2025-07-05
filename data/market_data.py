import os
import logging
from kraken.futures import Market
from datetime import datetime
from core.error_handler import handle_network_errors

class MarketData:
    def __init__(self):
        self.api_key = os.getenv("KRAKEN_API_KEY")
        self.api_secret = os.getenv("KRAKEN_API_SECRET")
        self.client = Market(key=self.api_key, secret=self.api_secret)
        self.logger = logging.getLogger(__name__)

    @handle_network_errors(max_retries=3, timeout=20.0)
    def get_ohlcv_15m(self, symbol="PI_XBTUSD", limit=100):
        # Récupère les dernières bougies 15m (OHLCV) pour le symbole donné
        try:
            self.logger.debug(f"Récupération {limit} bougies 15m pour {symbol}")
            
            # LOG DÉTAILLÉ DE L'APPEL API
            print(f"🔍 APPEL API KRAKEN: get_ohlc(tick_type='trade', symbol='{symbol}', resolution='15m')")
            
            candles = self.client.get_ohlc(tick_type="trade", symbol=symbol, resolution="15m")
            
            # LOG DE LA RÉPONSE BRUTE
            print(f"📡 RÉPONSE API KRAKEN: {candles}")
            
            # Log de la réponse brute pour debug
            self.logger.debug(f"Réponse brute API: {candles}")
            
            # candles['candles'] est une liste de dicts avec time, open, high, low, close, volume
            # On trie par timestamp croissant (du plus ancien au plus récent)
            ohlcv = sorted(candles['candles'], key=lambda x: x['time'])
            
            # IMPORTANT: La dernière bougie est la bougie en cours (non fermée)
            # On exclut cette bougie et on ne garde que les bougies fermées
            if len(ohlcv) > 1:
                ohlcv = ohlcv[:-1]  # Exclure la dernière bougie (en cours)
                self.logger.debug(f"Bougie en cours exclue. Bougies fermées restantes: {len(ohlcv)}")
            
            # On ne garde que les 'limit' dernières bougies fermées
            ohlcv = ohlcv[-limit:]
            
            # On convertit le timestamp en datetime lisible
            for c in ohlcv:
                c['datetime'] = datetime.utcfromtimestamp(c['time']/1000)
            
            self.logger.debug(f"Récupéré {len(ohlcv)} bougies 15m fermées pour {symbol}")
            
            # LOG DÉTAILLÉ DES BOUGIES RÉCUPÉRÉES
            print(f"✅ BOUGIES KRAKEN RÉCUPÉRÉES: {len(ohlcv)} bougies")
            for i, c in enumerate(ohlcv[-5:]):  # Afficher les 5 dernières
                print(f"   {i+1}: {c['datetime']} | Close: {c['close']} | Volume: {c['volume']}")
            
            # Log des 2 dernières bougies pour debug
            if len(ohlcv) >= 2:
                last_candle = ohlcv[-1]
                prev_candle = ohlcv[-2]
                self.logger.debug(f"Bougie N-1 (dernière fermée): {last_candle['datetime']} | O:{last_candle['open']} H:{last_candle['high']} L:{last_candle['low']} C:{last_candle['close']} V:{last_candle['volume']}")
                self.logger.debug(f"Bougie N-2 (avant-dernière): {prev_candle['datetime']} | O:{prev_candle['open']} H:{prev_candle['high']} L:{prev_candle['low']} C:{prev_candle['close']} V:{prev_candle['volume']}")
            
            return ohlcv
            
        except Exception as e:
            self.logger.error(f"Erreur récupération bougies 15m pour {symbol}: {e}")
            print(f"❌ ERREUR API KRAKEN: {e}")
            raise

if __name__ == "__main__":
    md = MarketData()
    candles = md.get_ohlcv_15m(limit=5)
    print("5 dernières bougies 15m (UTC) :")
    for c in candles:
        print(f"{c['datetime']} | O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']} V:{c['volume']}") 