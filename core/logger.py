"""
Module de logging pour BitSniper
Gère les logs avec rotation automatique et niveaux de log
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import json

class BitSniperLogger:
    def __init__(self, log_dir="logs", max_file_size=10*1024*1024, backup_count=5):
        """
        Initialise le système de logging.
        
        :param log_dir: Dossier pour les logs
        :param max_file_size: Taille max du fichier de log (10MB par défaut)
        :param backup_count: Nombre de fichiers de backup à garder
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Créer le logger principal
        self.logger = logging.getLogger('bitsniper')
        self.logger.setLevel(logging.DEBUG)
        
        # Éviter les logs dupliqués
        if not self.logger.handlers:
            self._setup_handlers(max_file_size, backup_count)
    
    def _setup_handlers(self, max_file_size, backup_count):
        """Configure les handlers de logging."""
        
        # Handler pour fichier principal (tous les niveaux)
        main_log_file = os.path.join(self.log_dir, "bitsniper.log")
        file_handler = RotatingFileHandler(
            main_log_file, 
            maxBytes=max_file_size, 
            backupCount=backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Format pour fichier
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Handler pour console (INFO et plus)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Format pour console
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # Ajouter les handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_candle_analysis(self, candles, rsi_success, rsi_message):
        """
        Log l'analyse des bougies avec validation RSI.
        """
        try:
            # Log des dernières bougies pour debug
            if len(candles) >= 2:
                last_candle = candles[-1]
                prev_candle = candles[-2]
                
                candle_debug = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'rsi_validation': {
                        'success': rsi_success,
                        'message': rsi_message
                    },
                    'last_candles': {
                        'candle_n1': {
                            'time': last_candle['time'],
                            'datetime': last_candle['datetime'].isoformat() if hasattr(last_candle['datetime'], 'isoformat') else str(last_candle['datetime']),
                            'open': last_candle['open'],
                            'high': last_candle['high'],
                            'low': last_candle['low'],
                            'close': last_candle['close'],
                            'volume': last_candle['volume']
                        },
                        'candle_n2': {
                            'time': prev_candle['time'],
                            'datetime': prev_candle['datetime'].isoformat() if hasattr(prev_candle['datetime'], 'isoformat') else str(prev_candle['datetime']),
                            'open': prev_candle['open'],
                            'high': prev_candle['high'],
                            'low': prev_candle['low'],
                            'close': prev_candle['close'],
                            'volume': prev_candle['volume']
                        }
                    },
                    'total_candles': len(candles)
                }
                
                self.logger.info(f"CANDLES_DEBUG_JSON: {json.dumps(candle_debug, indent=2)}")
            
            self.logger.info("Analyse des bougies effectuée", extra={
                'rsi_success': rsi_success,
                'rsi_message': rsi_message,
                'candles_count': len(candles)
            })
            
        except Exception as e:
            self.logger.error(f"Erreur lors du logging de l'analyse des bougies: {e}")
    
    def log_account_status(self, account_summary):
        """Log le statut du compte."""
        if account_summary:
            self.logger.info("Statut compte", extra={
                'event': 'account_status',
                'usd_balance': account_summary['wallet']['usd_balance'],
                'current_btc_price': account_summary['current_btc_price'],
                'max_position_size': account_summary['max_position_size']['max_btc_size'],
                'has_open_position': account_summary['has_open_position'],
                'open_positions_count': len(account_summary['positions'])
            })
        else:
            self.logger.error("Impossible de récupérer le statut du compte")
    
    def log_technical_analysis(self, analysis, conditions_check):
        """
        Log l'analyse technique avec les conditions de trading.
        """
        try:
            # Log de base
            self.logger.info("Analyse technique effectuée", extra={
                'rsi_n1': analysis['rsi_n1'],
                'rsi_n2': analysis['rsi_n2'],
                'rsi_change': analysis['rsi_change'],
                'volume_n1': analysis['volume_n1'],
                'volume_n2': analysis['volume_n2'],
                'delta_volume': analysis['delta_volume'],
                'trading_allowed': conditions_check['trading_allowed'],
                'long1_ready': conditions_check['long1_ready'],
                'long2_ready': conditions_check['long2_ready'],
                'short_ready': conditions_check['short_ready']
            })
            
            # Log JSON détaillé pour debug
            detailed_analysis = {
                'timestamp': datetime.utcnow().isoformat(),
                'candles_data': {
                    'candle_n1': {
                        'time': analysis['candle_n1']['time'],
                        'datetime': analysis['candle_n1']['datetime'].isoformat() if hasattr(analysis['candle_n1']['datetime'], 'isoformat') else str(analysis['candle_n1']['datetime']),
                        'open': analysis['candle_n1']['open'],
                        'high': analysis['candle_n1']['high'],
                        'low': analysis['candle_n1']['low'],
                        'close': analysis['candle_n1']['close'],
                        'volume': analysis['candle_n1']['volume']
                    },
                    'candle_n2': {
                        'time': analysis['candle_n2']['time'],
                        'datetime': analysis['candle_n2']['datetime'].isoformat() if hasattr(analysis['candle_n2']['datetime'], 'isoformat') else str(analysis['candle_n2']['datetime']),
                        'open': analysis['candle_n2']['open'],
                        'high': analysis['candle_n2']['high'],
                        'low': analysis['candle_n2']['low'],
                        'close': analysis['candle_n2']['close'],
                        'volume': analysis['candle_n2']['volume']
                    }
                },
                'rsi_data': {
                    'rsi_n1': analysis['rsi_n1'],
                    'rsi_n2': analysis['rsi_n2'],
                    'rsi_change': analysis['rsi_change']
                },
                'volume_data': {
                    'volume_n1': analysis['volume_n1'],
                    'volume_n2': analysis['volume_n2'],
                    'delta_volume': analysis['delta_volume']
                },
                'price_data': {
                    'close_n1': analysis['close_n1'],
                    'close_n2': analysis['close_n2']
                },
                'conditions': {
                    'long1': analysis['long1_conditions'],
                    'long2': analysis['long2_conditions'],
                    'short': analysis['short_conditions'],
                    'safety': analysis['safety_rule']
                },
                'trading_decision': {
                    'trading_allowed': conditions_check['trading_allowed'],
                    'reason': conditions_check.get('reason', 'N/A'),
                    'long1_ready': conditions_check['long1_ready'],
                    'long2_ready': conditions_check['long2_ready'],
                    'short_ready': conditions_check['short_ready']
                }
            }
            
            # Log en JSON pour debug
            self.logger.info(f"ANALYSE_DETAILLEE_JSON: {json.dumps(detailed_analysis, indent=2)}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du logging de l'analyse technique: {e}")
    def log_trading_decision(self, decision):
        """Log la décision de trading."""
        self.logger.info("Décision trading", extra={
            'event': 'trading_decision',
            'action': decision['action'],
            'reason': decision['reason']
        })
    
    def log_order_execution(self, execution_result):
        """Log l'exécution d'un ordre."""
        if execution_result.get('success', False):
            self.logger.info("Ordre exécuté", extra={
                'event': 'order_execution',
                'success': True,
                'action': execution_result['decision']['action'],
                'order_id': execution_result.get('order_id'),
                'filled_size': execution_result.get('filled_size'),
                'price': execution_result.get('price')
            })
        else:
            self.logger.error("Échec exécution ordre", extra={
                'event': 'order_execution',
                'success': False,
                'action': execution_result.get('action', 'unknown'),
                'error': execution_result.get('error', 'unknown error')
            })
    
    def log_state_update(self, state_manager):
        """Log la mise à jour de l'état."""
        current_pos = state_manager.get_current_position()
        long2_rsi = state_manager.get_long2_entry_rsi()
        
        self.logger.info("État mis à jour", extra={
            'event': 'state_update',
            'has_open_position': current_pos is not None,
            'position_type': current_pos['type'] if current_pos else None,
            'long2_entry_rsi': long2_rsi
        })
    
    def log_error(self, error_msg, error_details=None):
        """Log une erreur."""
        extra_data = {'event': 'error', 'error_message': error_msg}
        if error_details:
            extra_data['error_details'] = error_details
        
        self.logger.error(f"ERREUR: {error_msg}", extra=extra_data)
    
    def log_warning(self, warning_msg, warning_details=None):
        """Log un avertissement."""
        extra_data = {'event': 'warning', 'warning_message': warning_msg}
        if warning_details:
            extra_data['warning_details'] = warning_details
        
        self.logger.warning(f"ATTENTION: {warning_msg}", extra=extra_data)
    
    def log_trade_summary(self, trade_data):
        """Log un résumé de trade."""
        self.logger.info("Résumé trade", extra={
            'event': 'trade_summary',
            'position_type': trade_data.get('type'),
            'entry_price': trade_data.get('entry_price'),
            'exit_price': trade_data.get('exit_price'),
            'entry_rsi': trade_data.get('entry_rsi'),
            'exit_rsi': trade_data.get('exit_rsi'),
            'pnl': trade_data.get('pnl'),
            'duration': trade_data.get('duration')
        })
    
    def log_bot_start(self):
        """Log le démarrage du bot."""
        self.logger.info("Bot démarré", extra={
            'event': 'bot_start',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def log_bot_stop(self):
        """Log l'arrêt du bot."""
        self.logger.info("Bot arrêté", extra={
            'event': 'bot_stop',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def log_scheduler_tick(self):
        """Log chaque tick du scheduler."""
        self.logger.debug("Tick scheduler", extra={
            'event': 'scheduler_tick',
            'timestamp': datetime.utcnow().isoformat()
        })

# Instance globale du logger
logger = BitSniperLogger()

# Test du module
if __name__ == "__main__":
    # Test des différents niveaux de log
    logger.log_bot_start()
    logger.log_warning("Test d'avertissement")
    logger.log_error("Test d'erreur")
    
    # Test avec données structurées
    test_analysis = {
        'rsi_n1': 35.0,
        'rsi_n2': 30.0,
        'volume_n1': 95.0
    }
    
    test_conditions = {
        'trading_allowed': True,
        'long1_ready': True
    }
    
    logger.log_technical_analysis(test_analysis, test_conditions)
    
    print("Logs créés dans le dossier 'logs/'") 

def get_logger(name):
    """
    Retourne le logger global BitSniper, compatible avec l'import get_logger partout dans le projet.
    """
    return logging.getLogger('bitsniper') 