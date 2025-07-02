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
            
            candles = self.client.get_ohlc(tick_type="trade", symbol=symbol, resolution="15m")
            # candles['candles'] est une liste de dicts avec time, open, high, low, close, volume
            # On trie par timestamp croissant (du plus ancien au plus récent)
            ohlcv = sorted(candles['candles'], key=lambda x: x['time'])
            # On ne garde que les 'limit' dernières bougies
            ohlcv = ohlcv[-limit:]
            # On convertit le timestamp en datetime lisible
            for c in ohlcv:
                c['datetime'] = datetime.utcfromtimestamp(c['time']/1000)
            
            self.logger.debug(f"Récupéré {len(ohlcv)} bougies 15m pour {symbol}")
            return ohlcv
            
        except Exception as e:
            self.logger.error(f"Erreur récupération bougies 15m pour {symbol}: {e}")
            raise

if __name__ == "__main__":
    md = MarketData()
    candles = md.get_ohlcv_15m(limit=5)
    print("5 dernières bougies 15m (UTC) :")
    for c in candles:
        print(f"{c['datetime']} | O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']} V:{c['volume']}") 