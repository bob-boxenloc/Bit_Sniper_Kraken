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
        
        # Thread de monitoring
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Démarre le monitoring WebSocket en arrière-plan"""
        if self.is_monitoring:
            self.logger.warning("Monitoring déjà en cours")
            return
            
        self.logger.info("🚀 Démarrage du monitoring WebSocket Kraken OHLC")
        self.logger.info(f"   URL: {self.ws_url}")
        self.logger.info(f"   Symbol: {self.symbol}")
        self.logger.info(f"   Interval: {self.interval} minutes")
        
        # Démarrer le thread de monitoring
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Arrête le monitoring WebSocket"""
        self.logger.info("🛑 Arrêt du monitoring WebSocket")
        self.is_monitoring = False
        
        if self.ws:
            self.ws.close()
            
    def _monitor_loop(self):
        """Boucle principale de monitoring WebSocket"""
        self.is_monitoring = True
        reconnect_delay = 5  # Délai initial de reconnexion
        
        while self.is_monitoring:
            try:
                if not self.is_connected:
                    self.logger.info(f"🔄 Tentative de reconnexion WebSocket (délai: {reconnect_delay}s)")
                    self._connect()
                    
                if self.is_connected:
                    # Maintenir la connexion active
                    time.sleep(1)
                    reconnect_delay = 5  # Réinitialiser le délai si connecté
                    
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle de monitoring: {e}")
                self.is_connected = False
                
                # Délai de reconnexion progressif (max 60 secondes)
                reconnect_delay = min(reconnect_delay * 2, 60)
                self.logger.info(f"⏳ Attente de {reconnect_delay}s avant reconnexion...")
                time.sleep(reconnect_delay)
                
    def _connect(self):
        """Établit la connexion WebSocket"""
        try:
            self.logger.info("🔌 Connexion au WebSocket Kraken...")
            
            # Créer la connexion WebSocket avec options de robustesse
            websocket.enableTrace(False)  # Désactiver les traces pour la production
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # Démarrer la connexion avec options de robustesse
            ws_thread = threading.Thread(
                target=lambda: self.ws.run_forever(
                    ping_interval=30,      # Ping toutes les 30 secondes
                    ping_timeout=10,       # Timeout ping 10 secondes
                    ping_payload="ping",   # Payload ping
                    sslopt={"cert_reqs": 0}  # Ignorer les erreurs SSL
                ), 
                daemon=True
            )
            ws_thread.start()
            
            # Attendre la connexion avec timeout plus long
            timeout = 20  # Augmenté à 20 secondes
            while not self.is_connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
                
            if not self.is_connected:
                self.logger.error("❌ Timeout de connexion WebSocket")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur de connexion WebSocket: {e}")
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
            for candle in data.get('data', []):
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
        Log de comparaison entre WebSocket et REST API.
        À appeler depuis le code principal pour comparer les données.
        """
        if not self.latest_candle:
            self.logger.warning("⚠️ Aucune bougie WebSocket disponible pour comparaison")
            return
            
        try:
            self.logger.info(f"🔍 COMPARAISON OHLC - WebSocket vs REST API")
            self.logger.info(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"   Symbol: {self.symbol}")
            self.logger.info(f"   Interval: {self.interval} minutes")
            self.logger.info(f"")
            
            # Données WebSocket
            ws_open = self.latest_candle.get('open', 'N/A')
            ws_high = self.latest_candle.get('high', 'N/A')
            ws_low = self.latest_candle.get('low', 'N/A')
            ws_close = self.latest_candle.get('close', 'N/A')
            ws_volume = self.latest_candle.get('volume', 'N/A')
            ws_trades = self.latest_candle.get('trades', 'N/A')
            
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
