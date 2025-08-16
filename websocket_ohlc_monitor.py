#!/usr/bin/env python3
"""
Module de monitoring WebSocket Kraken pour comparaison des données OHLC.
COMPLÈTEMENT ISOLÉ - AUCUN IMPACT SUR LA STRATÉGIE DE TRADING !
"""

import websocket
import json
import logging
import time
from datetime import datetime
import threading

class KrakenWebSocketMonitor:
    """
    Moniteur WebSocket Kraken pour observer les données OHLC en temps réel.
    Module 100% isolé - aucune modification des données de trading existantes.
    """
    
    def __init__(self):
        self.ws = None
        self.is_connected = False
        self.is_monitoring = False
        self.latest_candle = None
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Configuration WebSocket
        self.ws_url = "wss://ws.kraken.com/v2"
        self.symbol = "XBT/USD"  # CORRECTION : Futures Kraken, pas Spot !
        self.interval = 15  # 15 minutes
        
        # NOUVEAU : Mode ponctuel (pas de monitoring continu)
        self.connection_timeout = 60  # Augmenter le timeout à 60 secondes  # Timeout de connexion en secondes
        
    def start_monitoring(self):
        """Démarre le monitoring WebSocket en arrière-plan"""
        if self.is_monitoring:
            self.logger.warning("Monitoring déjà en cours")
            return
            
        self.logger.info("🚀 Démarrage du monitoring WebSocket Kraken OHLC")
        self.logger.info(f"   URL: {self.ws_url}")
        self.logger.info(f"   Symbol: {self.symbol}")
        self.logger.info(f"   Interval: {self.interval} minutes")
        
        # NOUVEAU : Mode ponctuel - pas de thread continu
        self.is_monitoring = True
        
    def stop_monitoring(self):
        """Arrête le monitoring WebSocket"""
        self.logger.info("🛑 Arrêt du monitoring WebSocket")
        self.is_monitoring = False
        
        if self.ws:
            self.ws.close()
            
    def get_ohlc_snapshot(self):
        """
        NOUVEAU : Récupère un snapshot OHLC ponctuel.
        À appeler au moment de la comparaison avec l'API REST.
        """
        try:
            self.logger.info("📡 Connexion WebSocket ponctuelle pour snapshot OHLC...")
            self.logger.info(f"🔍 DEBUG: État actuel - is_monitoring: {self.is_monitoring}, is_connected: {self.is_connected}")
            
            # Connexion ponctuelle
            self.logger.info("🔌 DEBUG: Tentative de connexion ponctuelle...")
            if self._connect_ponctual():
                self.logger.info("✅ DEBUG: Connexion ponctuelle réussie")
                
                # Attendre le snapshot
                timeout = self.connection_timeout
                self.logger.info(f"⏳ DEBUG: Attente snapshot (timeout: {timeout}s)...")
                start_time = time.time()
                while not self.latest_candle and timeout > 0:
                    time.sleep(0.1)
                    timeout -= 0.1
                    if int(time.time() - start_time) % 5 == 0 and int(time.time() - start_time) > 0:
                        self.logger.info(f"⏳ DEBUG: Attente snapshot... {int(time.time() - start_time)}s écoulées")
                
                if self.latest_candle:
                    self.logger.info("✅ Snapshot OHLC WebSocket reçu")
                    return self.latest_candle
                else:
                    self.logger.warning("⚠️ Timeout attente snapshot OHLC")
                    return None
            else:
                self.logger.error("❌ Impossible de se connecter au WebSocket")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Erreur snapshot OHLC: {e}")
            return None
        finally:
            # Fermer la connexion après utilisation
            self.logger.info("🔌 DEBUG: Fermeture connexion ponctuelle...")
            self._disconnect()
                
    def _connect_ponctual(self):
        """NOUVEAU : Connexion WebSocket ponctuelle pour snapshot"""
        try:
            self.logger.info("🔌 Connexion WebSocket ponctuelle...")
            
            # Créer la connexion WebSocket simple
            websocket.enableTrace(False)
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # Démarrer la connexion avec timeout court
            ws_thread = threading.Thread(
                target=lambda: self.ws.run_forever(
                    ping_interval=None,    # Pas de ping automatique
                    ping_timeout=None,     # Pas de timeout ping
                    sslopt={"cert_reqs": 0}
                ), 
                daemon=True
            )
            ws_thread.start()
            
            # Attendre la connexion avec timeout court
            timeout = 10  # Timeout court pour connexion ponctuelle
            while not self.is_connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
                
            if not self.is_connected:
                self.logger.error("❌ Timeout de connexion WebSocket ponctuelle")
                return False
                
            return True
                
        except Exception as e:
            self.logger.error(f"❌ Erreur de connexion WebSocket ponctuelle: {e}")
            self.is_connected = False
            return False
            
    def _disconnect(self):
        """NOUVEAU : Ferme la connexion WebSocket"""
        if self.ws:
            self.ws.close()
            self.ws = None
        self.is_connected = False
            
    def _on_open(self, ws):
        """Callback appelé quand la connexion WebSocket s'ouvre"""
        self.logger.info("✅ Connexion WebSocket établie")
        self.is_connected = True
        
        # Souscrire au channel OHLC
        self._subscribe_ohlc()
        
    def _on_message(self, ws, message):
        """Callback appelé quand un message WebSocket est reçu"""
        try:
            data = json.loads(message)
            
            # Traiter les messages OHLC
            if data.get('channel') == 'ohlc':
                self._process_ohlc_message(data)
                
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Erreur parsing JSON: {e}")
        except Exception as e:
            self.logger.error(f"❌ Erreur traitement message: {e}")
            
    def _on_error(self, ws, error):
        """Callback appelé en cas d'erreur WebSocket"""
        self.logger.error(f"❌ Erreur WebSocket: {error}")
        self.is_connected = False
        
    def _on_close(self, ws, close_status_code, close_msg):
        """Callback appelé quand la connexion WebSocket se ferme"""
        self.logger.warning(f"🔌 Connexion WebSocket fermée: {close_status_code} - {close_msg}")
        self.is_connected = False
        
    def _subscribe_ohlc(self):
        """Souscrit au channel OHLC"""
        try:
            subscribe_message = {
                "method": "subscribe",
                "params": {
                    "channel": "ohlc",
                    "symbol": [self.symbol],
                    "interval": self.interval,
                    "snapshot": True
                }
            }
            
            self.ws.send(json.dumps(subscribe_message))
            self.logger.info(f"📡 Souscription au channel OHLC: {self.symbol} @ {self.interval}m")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur souscription OHLC: {e}")
            
    def _process_ohlc_message(self, data):
        """Traite les messages OHLC reçus"""
        try:
            self.logger.info(f"🔍 DEBUG: Message WebSocket reçu: {data.get('channel', 'N/A')}")
            
            if data.get('channel') == 'ohlc':
                candle_data = data.get('data', [])
                self.logger.info(f"🔍 DEBUG: Données OHLC trouvées: {len(candle_data)} bougies")
                
                for candle in candle_data:
                    # Stocker la dernière bougie
                    self.latest_candle = candle
                    
                    # Log de la bougie reçue
                    self._log_ohlc_candle(candle)
                    
        except Exception as e:
            self.logger.error(f"❌ Erreur traitement bougie OHLC: {e}")
            
    def _log_ohlc_candle(self, candle):
        """Log détaillé d'une bougie OHLC WebSocket"""
        try:
            symbol = candle.get('symbol', 'N/A')
            interval_begin = candle.get('interval_begin', 'N/A')
            
            self.logger.info(f"🔍 WEBSOCKET OHLC - Nouvelle bougie reçue:")
            self.logger.info(f"   Symbol: {symbol}")
            self.logger.info(f"   Interval Begin: {interval_begin}")
            self.logger.info(f"   Open: {candle.get('open', 'N/A')}")
            self.logger.info(f"   High: {candle.get('high', 'N/A')}")
            self.logger.info(f"   Low: {candle.get('low', 'N/A')}")
            self.logger.info(f"   Close: {candle.get('close', 'N/A')}")
            self.logger.info(f"   Volume: {candle.get('volume', 'N/A')}")
            self.logger.info(f"   Trades: {candle.get('trades', 'N/A')}")
            self.logger.info(f"   VWAP: {candle.get('vwap', 'N/A')}")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log bougie OHLC: {e}")
            
    def get_latest_candle(self):
        """Retourne la dernière bougie WebSocket reçue"""
        return self.latest_candle
        
    def log_comparison(self, rest_api_candle):
        """
        NOUVEAU : Log de comparaison avec snapshot WebSocket ponctuel.
        À appeler depuis le code principal pour comparer les données.
        """
        self.logger.info(f"🔍 DEBUG: log_comparison appelé avec bougie REST API: {rest_api_candle.get('datetime', 'N/A')}")
        
        # Récupérer un snapshot WebSocket ponctuel
        self.logger.info("📡 DEBUG: Début get_ohlc_snapshot...")
        websocket_candle = self.get_ohlc_snapshot()
        
        if not websocket_candle:
            self.logger.warning("⚠️ Impossible de récupérer snapshot WebSocket pour comparaison")
            return
            
        try:
            self.logger.info(f"🔍 COMPARAISON OHLC - WebSocket vs REST API")
            self.logger.info(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"   Symbol: {self.symbol}")
            self.logger.info(f"   Interval: {self.interval} minutes")
            self.logger.info(f"")
            
            # Données WebSocket (snapshot ponctuel)
            ws_open = websocket_candle.get('open', 'N/A')
            ws_high = websocket_candle.get('high', 'N/A')
            ws_low = websocket_candle.get('low', 'N/A')
            ws_close = websocket_candle.get('close', 'N/A')
            ws_volume = websocket_candle.get('volume', 'N/A')
            ws_trades = websocket_candle.get('trades', 'N/A')
            
            # Données REST API
            rest_open = rest_api_candle.get('open', 'N/A')
            rest_high = rest_api_candle.get('high', 'N/A')
            rest_low = rest_api_candle.get('low', 'N/A')
            rest_close = rest_api_candle.get('close', 'N/A')
            rest_volume = rest_api_candle.get('volume', 'N/A')
            rest_count = rest_api_candle.get('count', 'N/A')
            
            # Affichage côte à côte
            self.logger.info(f"   {'WebSocket':<15} {'REST API':<20} {'Différence':<15}")
            self.logger.info(f"   {'-'*15} {'-'*20} {'-'*15}")
            
            # Open
            if ws_open != 'N/A' and rest_open != 'N/A':
                diff_open = abs(float(ws_open) - float(rest_open))
                self.logger.info(f"   {ws_open:<15} {rest_open:<20} {diff_open:<15.2f}")
            else:
                self.logger.info(f"   {ws_open:<15} {rest_open:<20} {'N/A':<15}")
                
            # High
            if ws_high != 'N/A' and rest_high != 'N/A':
                diff_high = abs(float(ws_high) - float(rest_high))
                self.logger.info(f"   {ws_high:<15} {rest_high:<20} {diff_high:<15.2f}")
            else:
                self.logger.info(f"   {ws_high:<15} {rest_high:<20} {'N/A':<15}")
                
            # Low
            if ws_low != 'N/A' and rest_low != 'N/A':
                diff_low = abs(float(ws_low) - float(rest_low))
                self.logger.info(f"   {ws_low:<15} {rest_low:<20} {diff_low:<15.2f}")
            else:
                self.logger.info(f"   {ws_low:<15} {rest_low:<20} {'N/A':<15}")
                
            # Close
            if ws_close != 'N/A' and rest_close != 'N/A':
                diff_close = abs(float(ws_close) - float(rest_close))
                self.logger.info(f"   {ws_close:<15} {rest_close:<20} {diff_close:<15.2f}")
            else:
                self.logger.info(f"   {ws_close:<15} {rest_close:<20} {'N/A':<15}")
                
            # Volume/Count
            self.logger.info(f"   {ws_volume:<15} {rest_volume:<20} {'N/A':<15}")
            self.logger.info(f"   {ws_trades:<15} {rest_count:<20} {'N/A':<15}")
            
            self.logger.info(f"")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur comparaison OHLC: {e}")


# Instance globale pour utilisation dans le code principal
websocket_monitor = None

def start_websocket_monitoring():
    """Fonction globale pour démarrer le monitoring WebSocket"""
    global websocket_monitor
    
    try:
        websocket_monitor = KrakenWebSocketMonitor()
        websocket_monitor.start_monitoring()
        return websocket_monitor
    except Exception as e:
        logging.error(f"❌ Erreur démarrage monitoring WebSocket: {e}")
        return None

def stop_websocket_monitoring():
    """Fonction globale pour arrêter le monitoring WebSocket"""
    global websocket_monitor
    
    if websocket_monitor:
        websocket_monitor.stop_monitoring()
        websocket_monitor = None


if __name__ == "__main__":
    # Test du module en standalone
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    monitor = start_websocket_monitoring()
    
    try:
        # Garder le programme en vie pour observer
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du monitoring...")
        stop_websocket_monitoring()
