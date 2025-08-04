import os
import logging
import requests
import time
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
            
            # data['result']['data'] contient les données analytics
            trade_counts = {}
            if 'result' in data and 'data' in data['result'] and 'timestamp' in data['result']:
                timestamps = data['result']['timestamp']
                counts = data['result']['data']
                for i, timestamp in enumerate(timestamps):
                    if i < len(counts):
                        trade_counts[timestamp * 1000] = counts[i]  # Convertir en millisecondes
            
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
            
            # Utiliser le SDK avec tick_type="trade" pour avoir le volume
            ohlc_data = self.client.get_ohlc(tick_type="trade", symbol=symbol, resolution="15m")
            
            # data['candles'] est une liste de dicts avec time, open, high, low, close, volume
            ohlcv = ohlc_data.get('candles', [])
            
            # On trie par timestamp croissant (du plus ancien au plus récent)
            ohlcv = sorted(ohlcv, key=lambda x: x['time'])
            
            # FILTRER LES BOUGIES FERMÉES (volume > 0)
            closed_candles = [c for c in ohlcv if float(c.get('volume', 0)) > 0]
            
            if not closed_candles:
                self.logger.warning("Aucune bougie fermée trouvée")
                return []
            
            # CORRECTION CRITIQUE : Récupérer la bougie qui vient de se fermer
            # Au lieu de la dernière bougie fermée
            if limit == 1:
                # Pour une seule bougie : récupérer la bougie qui vient de se fermer
                # Calculer le timestamp de la bougie actuelle (15 minutes alignées)
                current_time = int(time.time())
                current_candle_start = (current_time // 900) * 900  # Aligner sur 15 minutes
                
                # La bougie qui vient de se fermer est celle qui s'est terminée juste avant la bougie actuelle
                # (soit 15 minutes avant le début de la bougie actuelle)
                recently_closed_candle_start = current_candle_start - 900  # 15 minutes = 900 secondes
                recently_closed_candle_end = current_candle_start
                
                # Trouver la bougie qui correspond à cette période
                target_candle = None
                for candle in closed_candles:
                    candle_start = (candle['time'] // 1000) // 900 * 900  # Convertir en secondes et aligner
                    if candle_start == recently_closed_candle_start:
                        target_candle = candle
                        break
                
                if target_candle:
                    ohlcv = [target_candle]
                    target_datetime = datetime.utcfromtimestamp(target_candle['time']/1000)
                    self.logger.info(f"✅ Récupéré la bougie qui vient de se fermer: {target_datetime} (période {recently_closed_candle_start}-{recently_closed_candle_end})")
                else:
                    self.logger.warning(f"Aucune bougie qui vient de se fermer trouvée pour la période {recently_closed_candle_start}-{recently_closed_candle_end}")
                    return []
            else:
                # Pour plusieurs bougies : garder les 'limit' dernières bougies fermées
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
        self.logger.info(f"Buffer initialisé avec capacité max: {max_candles} bougies")
    
    def initialize_with_historical(self, historical_candles):
        """Initialise le buffer avec les données historiques"""
        self.candles = historical_candles[-self.max_candles:]  # Garder les 40 plus récentes
        self.logger.info(f"Buffer initialisé avec {len(self.candles)} bougies historiques")
        
        # Log détaillé du contenu du buffer
        if self.candles:
            self.logger.info("Contenu du buffer après initialisation:")
            for i, candle in enumerate(self.candles):
                self.logger.info(f"  [{i+1}] {candle['datetime']} - Close: {candle['close']} - Volume: {candle.get('volume', 'N/A')} - Count: {candle.get('count', 'N/A')}")
        else:
            self.logger.info("Buffer vide après initialisation")
    
    def add_candle(self, new_candle):
        """Ajoute une nouvelle bougie et supprime la plus ancienne si nécessaire. Retourne True si ajoutée, False si déjà présente."""
        # Log avant ajout
        self.logger.info(f"Ajout bougie: {new_candle['datetime']} - Close: {new_candle['close']} - Volume: {new_candle.get('volume', 'N/A')} - Count: {new_candle.get('count', 'N/A')}")
        
        # Vérifier si la bougie est déjà dans le buffer
        existing_times = [c['time'] for c in self.candles]
        if new_candle['time'] in existing_times:
            self.logger.warning(f"Bougie déjà présente dans le buffer: {new_candle['datetime']}")
            return False
        
        self.candles.append(new_candle)
        
        # Log si une bougie est supprimée
        if len(self.candles) > self.max_candles:
            removed_candle = self.candles.pop(0)  # Supprime la plus ancienne
            self.logger.info(f"Bougie supprimée (buffer plein): {removed_candle['datetime']} - Close: {removed_candle['close']}")
        
        # Log du statut du buffer après ajout
        self.logger.info(f"Buffer après ajout: {len(self.candles)}/{self.max_candles} bougies")
        
        # Log détaillé du contenu actuel
        if self.candles:
            self.logger.info("Contenu actuel du buffer:")
            for i, candle in enumerate(self.candles):
                self.logger.info(f"  [{i+1}] {candle['datetime']} - Close: {candle['close']} - Volume: {candle.get('volume', 'N/A')} - Count: {candle.get('count', 'N/A')}")
        
        return True
    
    def get_candles(self):
        """Retourne la liste des bougies pour les calculs"""
        self.logger.debug(f"Récupération de {len(self.candles)} bougies du buffer")
        return self.candles
    
    def get_latest_candles(self, count=2):
        """Retourne les N dernières bougies pour les décisions"""
        latest = self.candles[-count:] if len(self.candles) >= count else []
        self.logger.debug(f"Récupération des {len(latest)} dernières bougies pour décisions")
        
        if latest:
            self.logger.info("Dernières bougies pour décisions:")
            for i, candle in enumerate(latest):
                self.logger.info(f"  N-{len(latest)-i}: {candle['datetime']} - Close: {candle['close']} - Volume: {candle.get('volume', 'N/A')} - Count: {candle.get('count', 'N/A')}")
        
        return latest
    
    def get_status(self):
        """Retourne le statut du buffer"""
        status = {
            'total_candles': len(self.candles),
            'max_candles': self.max_candles,
            'is_full': len(self.candles) >= self.max_candles,
            'latest_candle': self.candles[-1]['datetime'] if self.candles else None
        }
        
        # Log du statut
        self.logger.info(f"Statut buffer: {status['total_candles']}/{status['max_candles']} bougies - Plein: {status['is_full']}")
        if status['latest_candle']:
            self.logger.info(f"Dernière bougie: {status['latest_candle']}")
        
        return status
    
    def get_buffer_summary(self):
        """Retourne un résumé détaillé du buffer pour debug"""
        if not self.candles:
            return "Buffer vide"
        
        summary = []
        summary.append(f"Buffer: {len(self.candles)}/{self.max_candles} bougies")
        
        # Informations sur les bougies
        if self.candles:
            oldest = self.candles[0]
            newest = self.candles[-1]
            summary.append(f"Période: {oldest['datetime']} → {newest['datetime']}")
            
            # Convertir les prix en float avant le formatage
            lows = [float(c['low']) for c in self.candles]
            highs = [float(c['high']) for c in self.candles]
            summary.append(f"Prix range: ${min(lows):.2f} - ${max(highs):.2f}")
            
            # Count range si disponible
            counts = [c.get('count', 0) for c in self.candles if c.get('count') is not None]
            if counts:
                summary.append(f"Count range: {min(counts)} - {max(counts)}")
        
        return "\n".join(summary)

if __name__ == "__main__":
    md = MarketData()
    candles = md.get_ohlcv_15m(limit=5)
    print("5 dernières bougies 15m (UTC) :")
    for c in candles:
        print(f"{c['datetime']} | O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']} V:{c['volume']}") 