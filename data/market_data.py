import os
import logging
import requests
from kraken.futures import Market
from datetime import datetime
from core.error_handler import handle_network_errors

class MarketData:
    def __init__(self):
        self.api_key = os.getenv("KRAKEN_API_KEY")
        self.api_secret = os.getenv("KRAKEN_API_SECRET")
        self.client = Market(key=self.api_key, secret=self.api_secret)
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://futures.kraken.com/api/charts/v1"

    @handle_network_errors(max_retries=3, timeout=20.0)
    def get_trade_count_15m(self, symbol="PI_XBTUSD", limit=12):
        """Récupère le trade-count via l'endpoint Analytics"""
        try:
            # Calculer les timestamps from/to
            import time
            end_time = int(time.time())
            start_time = end_time - (limit * 15 * 60)  # limit * 15 minutes
            
            url = f"{self.base_url}/analytics/{symbol}/trade-count"
            params = {
                "since": start_time,
                "to": end_time,
                "interval": 900  # 15 minutes = 900 secondes
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # data['data'] contient les données analytics
            trade_counts = {}
            if 'data' in data and isinstance(data['data'], list):
                for item in data['data']:
                    if isinstance(item, list) and len(item) >= 2:
                        timestamp, count = item[0], item[1]
                        trade_counts[timestamp * 1000] = count  # Convertir en millisecondes
            
            self.logger.debug(f"Récupéré {len(trade_counts)} trade-counts pour {symbol}")
            return trade_counts
            
        except Exception as e:
            self.logger.error(f"Erreur récupération trade-count pour {symbol}: {e}")
            return {}

    @handle_network_errors(max_retries=3, timeout=20.0)
    def get_ohlcv_15m(self, symbol="PI_XBTUSD", limit=12):
        # Récupère les dernières bougies 15m (OHLCV) pour le symbole donné
        try:
            self.logger.debug(f"Récupération {limit} bougies 15m pour {symbol}")
            
            # Récupérer les bougies OHLCV
            candles = self.client.get_ohlc(
                tick_type="trade", 
                symbol=symbol, 
                resolution="15m"
            )
            
            # candles['candles'] est une liste de dicts avec time, open, high, low, close, volume
            # On trie par timestamp croissant (du plus ancien au plus récent)
            ohlcv = sorted(candles['candles'], key=lambda x: x['time'])
            
            # FILTRER LES BOUGIES FERMÉES (volume > 0)
            closed_candles = [c for c in ohlcv if float(c['volume']) > 0]
            
            if not closed_candles:
                self.logger.warning("Aucune bougie fermée trouvée")
                return []
            
            # On ne garde que les 'limit' dernières bougies fermées
            ohlcv = closed_candles[-limit:]
            
            # Récupérer le trade-count via l'endpoint Analytics
            try:
                trade_counts = self.get_trade_count_15m(symbol, limit)
            except Exception as e:
                self.logger.warning(f"Impossible de récupérer trade-count: {e}")
                trade_counts = {}
            
            # Fusionner les données OHLCV avec le trade-count
            for c in ohlcv:
                c['datetime'] = datetime.utcfromtimestamp(c['time']/1000)
                # Ajouter le trade-count depuis les analytics
                if c['time'] in trade_counts:
                    c['count'] = trade_counts[c['time']]
                else:
                    c['count'] = 0
            
            self.logger.debug(f"Récupéré {len(ohlcv)} bougies 15m fermées pour {symbol}")
            return ohlcv
            
        except Exception as e:
            self.logger.error(f"Erreur récupération bougies 15m pour {symbol}: {e}")
            raise

class CandleBuffer:
    """
    Gère un buffer de 12 bougies maximum pour les calculs.
    Ajoute les nouvelles bougies et supprime les plus anciennes automatiquement.
    """
    
    def __init__(self, max_candles=12):
        self.candles = []
        self.max_candles = max_candles
        self.logger = logging.getLogger(__name__)
    
    def initialize_with_historical(self, historical_candles):
        """Initialise le buffer avec les données historiques"""
        self.candles = historical_candles[-self.max_candles:]  # Garder les 40 plus récentes
        self.logger.info(f"Buffer initialisé avec {len(self.candles)} bougies historiques")
    
    def add_candle(self, new_candle):
        """Ajoute une nouvelle bougie et supprime la plus ancienne si nécessaire"""
        self.candles.append(new_candle)
        if len(self.candles) > self.max_candles:
            removed_candle = self.candles.pop(0)  # Supprime la plus ancienne
            self.logger.debug(f"Bougie supprimée: {removed_candle['datetime']}")
        
        self.logger.debug(f"Buffer: {len(self.candles)} bougies (max: {self.max_candles})")
    
    def get_candles(self):
        """Retourne la liste des bougies pour les calculs"""
        return self.candles
    
    def get_latest_candles(self, count=2):
        """Retourne les N dernières bougies pour les décisions"""
        return self.candles[-count:] if len(self.candles) >= count else []
    
    def get_status(self):
        """Retourne le statut du buffer"""
        return {
            'total_candles': len(self.candles),
            'max_candles': self.max_candles,
            'is_full': len(self.candles) >= self.max_candles,
            'latest_candle': self.candles[-1]['datetime'] if self.candles else None
        }

if __name__ == "__main__":
    md = MarketData()
    candles = md.get_ohlcv_15m(limit=5)
    print("5 dernières bougies 15m (UTC) :")
    for c in candles:
        print(f"{c['datetime']} | O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']} V:{c['volume']}") 