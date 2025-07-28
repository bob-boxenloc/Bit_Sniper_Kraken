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
    
    def log_data_progression(self, data_progression):
        """
        Log la progression des données (transition historique → temps réel).
        
        :param data_progression: Informations de progression des données
        """
        try:
            kraken_count = data_progression.get('kraken_candles_count', 0)
            total_required = data_progression.get('total_required', 80)
            is_complete = data_progression.get('is_transition_complete', False)
            progress_percentage = (kraken_count / total_required) * 100 if total_required > 0 else 0
            
            progression_debug = {
                'timestamp': datetime.utcnow().isoformat(),
                'data_progression': {
                    'kraken_candles_count': kraken_count,
                    'total_required': total_required,
                    'is_transition_complete': is_complete,
                    'progress_percentage': progress_percentage,
                    'historical_candles_count': total_required - kraken_count
                },
                'transition_status': {
                    'phase': 'complete' if is_complete else 'in_progress',
                    'current_ratio': f"{kraken_count}/{total_required}",
                    'percentage': f"{progress_percentage:.1f}%"
                }
            }
            
            self.logger.info(f"DATA_PROGRESSION_JSON: {json.dumps(progression_debug, indent=2)}")
            
            # Log de base
            self.logger.info("Progression des données mise à jour", extra={
                'kraken_candles_count': kraken_count,
                'total_required': total_required,
                'is_transition_complete': is_complete,
                'progress_percentage': progress_percentage
            })
            
        except Exception as e:
            self.logger.error(f"Erreur lors du logging de la progression des données: {e}")

    def log_candle_analysis(self, candles, rsi_success, rsi_message, data_progression=None):
        """
        Log l'analyse des bougies avec validation RSI et progression des données.
        
        :param candles: Liste des bougies combinées
        :param rsi_success: Succès du calcul RSI
        :param rsi_message: Message RSI
        :param data_progression: Informations de progression (optionnel)
        """
        try:
            # Log des dernières bougies pour debug
            if len(candles) >= 2:
                last_candle = candles[-1]
                prev_candle = candles[-2]
                
                # Informations de progression si disponibles
                progression_info = {}
                if data_progression:
                    kraken_count = data_progression.get('kraken_candles_count', 0)
                    total_required = data_progression.get('total_required', 80)
                    is_complete = data_progression.get('is_transition_complete', False)
                    
                    progression_info = {
                        'kraken_candles_count': kraken_count,
                        'total_required': total_required,
                        'is_transition_complete': is_complete,
                        'progress_percentage': (kraken_count / total_required) * 100 if total_required > 0 else 0
                    }
                
                candle_debug = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'data_progression': progression_info,
                    'rsi_validation': {
                        'success': rsi_success,
                        'message': rsi_message
                    },
                    'decision_candles': {
                        'candle_n1': {
                            'time': last_candle['time'],
                            'datetime': last_candle['datetime'].isoformat() if hasattr(last_candle['datetime'], 'isoformat') else str(last_candle['datetime']),
                            'open': last_candle['open'],
                            'high': last_candle['high'],
                            'low': last_candle['low'],
                            'close': last_candle['close'],
                            'count': last_candle.get('count', None),
                            'source': 'kraken_realtime'
                        },
                        'candle_n2': {
                            'time': prev_candle['time'],
                            'datetime': prev_candle['datetime'].isoformat() if hasattr(prev_candle['datetime'], 'isoformat') else str(prev_candle['datetime']),
                            'open': prev_candle['open'],
                            'high': prev_candle['high'],
                            'low': prev_candle['low'],
                            'close': prev_candle['close'],
                            'count': prev_candle.get('count', None),
                            'source': 'kraken_realtime'
                        }
                    },
                    'total_candles': len(candles),
                    'data_sources': {
                        'kraken_realtime_count': progression_info.get('kraken_candles_count', 0),
                        'historical_count': len(candles) - progression_info.get('kraken_candles_count', 0),
                        'calculation_method': 'hybrid' if progression_info else 'realtime_only'
                    }
                }
                
                self.logger.info(f"CANDLES_DEBUG_JSON: {json.dumps(candle_debug, indent=2)}")
            
            # Log de base avec progression
            log_extra = {
                'rsi_success': rsi_success,
                'rsi_message': rsi_message,
                'candles_count': len(candles)
            }
            
            if data_progression:
                log_extra.update({
                    'kraken_candles_count': data_progression.get('kraken_candles_count', 0),
                    'total_required': data_progression.get('total_required', 80),
                    'is_transition_complete': data_progression.get('is_transition_complete', False)
                })
            
            self.logger.info("Analyse des bougies effectuée", extra=log_extra)
            
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
        Log l'analyse technique avec les conditions de trading pour la nouvelle stratégie.
        """
        try:
            # Log de base
            self.logger.info("Analyse technique effectuée (Nouvelle Stratégie)", extra={
                'rsi': analysis['rsi'],
                'vi1': analysis['vi1'],
                'vi2': analysis['vi2'],
                'vi3': analysis['vi3'],
                'vi1_above_close': analysis['vi1_above_close'],
                'vi2_above_close': analysis['vi2_above_close'],
                'vi3_above_close': analysis['vi3_above_close'],
                'trading_allowed': conditions_check['trading_allowed'],
                'short_ready': conditions_check['short_ready'],
                'long_vi1_ready': conditions_check['long_vi1_ready'],
                'long_vi2_ready': conditions_check['long_vi2_ready'],
                'long_reentry_ready': conditions_check['long_reentry_ready'],
                'vi1_protection_active': conditions_check.get('vi1_protection_active', False)
            })
            
            # Log JSON détaillé pour debug
            detailed_analysis = {
                'timestamp': datetime.utcnow().isoformat(),
                'current_candle': {
                    'time': analysis['current_candle']['time'],
                    'datetime': analysis['current_candle']['datetime'].isoformat() if hasattr(analysis['current_candle']['datetime'], 'isoformat') else str(analysis['current_candle']['datetime']),
                    'open': analysis['current_candle']['open'],
                    'high': analysis['current_candle']['high'],
                    'low': analysis['current_candle']['low'],
                    'close': analysis['current_candle']['close'],
                    'count': analysis['current_candle'].get('count', None)
                    },
                'indicators': {
                    'rsi': analysis['rsi'],
                    'vi1': analysis['vi1'],
                    'vi2': analysis['vi2'],
                    'vi3': analysis['vi3'],
                    'vi1_above_close': analysis['vi1_above_close'],
                    'vi2_above_close': analysis['vi2_above_close'],
                    'vi3_above_close': analysis['vi3_above_close']
                },
                'price_data': {
                    'current_close': analysis['current_close']
                },
                'conditions': {
                    'short': analysis['short_conditions'],
                    'long_vi1': analysis['long_vi1_conditions'],
                    'long_vi2': analysis['long_vi2_conditions'],
                    'long_reentry': analysis['long_reentry_conditions']
                },
                'trading_decision': {
                    'trading_allowed': conditions_check['trading_allowed'],
                    'reason': conditions_check.get('reason', 'N/A'),
                    'short_ready': conditions_check['short_ready'],
                    'long_vi1_ready': conditions_check['long_vi1_ready'],
                    'long_vi2_ready': conditions_check['long_vi2_ready'],
                    'long_reentry_ready': conditions_check['long_reentry_ready'],
                    'vi1_protection_active': conditions_check.get('vi1_protection_active', False)
                }
            }
            
            # Log en JSON pour debug
            self.logger.info(f"ANALYSE_DETAILLEE_JSON: {json.dumps(detailed_analysis, indent=2)}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du logging de l'analyse technique: {e}")
    
    def log_indicators_calculation(self, indicators):
        """
        Log le calcul des indicateurs pour la nouvelle stratégie.
        """
        try:
            self.logger.info("Calcul des indicateurs (Nouvelle Stratégie)", extra={
                'rsi': indicators.get('RSI'),
                'vi1': indicators.get('VI1'),
                'vi2': indicators.get('VI2'),
                'vi3': indicators.get('VI3')
            })
            
            # Log JSON détaillé
            indicators_debug = {
                'timestamp': datetime.utcnow().isoformat(),
                'indicators': {
                    'RSI': indicators.get('RSI'),
                    'VI1': indicators.get('VI1'),
                    'VI2': indicators.get('VI2'),
                    'VI3': indicators.get('VI3')
                }
            }
            
            self.logger.info(f"INDICATEURS_CALCULES_JSON: {json.dumps(indicators_debug, indent=2)}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du logging des indicateurs: {e}")
    
    def log_vi1_phase_change(self, old_phase, new_phase, timestamp):
        """
        Log le changement de phase VI1.
        """
        try:
            self.logger.info("Changement de phase VI1", extra={
                'old_phase': old_phase,
                'new_phase': new_phase,
                'timestamp': timestamp,
                'event': 'vi1_phase_change'
            })
            
        except Exception as e:
            self.logger.error(f"Erreur lors du logging du changement de phase VI1: {e}")
    
    def log_protection_activation(self, protection_type, details):
        """
        Log l'activation des protections temporelles.
        """
        try:
            self.logger.info(f"Protection {protection_type} activée", extra={
                'protection_type': protection_type,
                'details': details,
                'event': 'protection_activation'
            })
            
        except Exception as e:
            self.logger.error(f"Erreur lors du logging de la protection: {e}")
    
    def log_position_exit_conditions(self, position_type, current_rsi, entry_rsi, hours_elapsed, exit_reason):
        """
        Log les conditions de sortie de position.
        """
        try:
            self.logger.info("Vérification conditions de sortie", extra={
                'position_type': position_type,
                'current_rsi': current_rsi,
                'entry_rsi': entry_rsi,
                'hours_elapsed': hours_elapsed,
                'exit_reason': exit_reason,
                'event': 'position_exit_check'
            })
            
        except Exception as e:
            self.logger.error(f"Erreur lors du logging des conditions de sortie: {e}")
    
    def log_new_strategy_state(self, state_manager):
        """
        Log l'état de la nouvelle stratégie.
        """
        try:
            last_position_type = state_manager.get_last_position_type()
            vi1_phase = state_manager.get_vi1_current_phase()
            vi1_timestamp = state_manager.get_vi1_phase_timestamp()
            
            self.logger.info("État nouvelle stratégie", extra={
                'last_position_type': last_position_type,
                'vi1_current_phase': vi1_phase,
                'vi1_phase_timestamp': vi1_timestamp,
                'event': 'new_strategy_state'
            })
            
        except Exception as e:
            self.logger.error(f"Erreur lors du logging de l'état nouvelle stratégie: {e}")
    def log_trading_decision(self, decision):
        """Log la décision de trading pour la nouvelle stratégie."""
        try:
            # Log de base
            self.logger.info("Décision trading (Nouvelle Stratégie)", extra={
            'event': 'trading_decision',
            'action': decision['action'],
                'reason': decision['reason'],
                'position_type': decision.get('position_type'),
                'entry_rsi': decision.get('entry_rsi'),
                'entry_time': decision.get('entry_time')
            })
            
            # Log JSON détaillé
            decision_debug = {
                'timestamp': datetime.utcnow().isoformat(),
                'decision': {
                    'action': decision['action'],
                    'reason': decision['reason'],
                    'position_type': decision.get('position_type'),
                    'entry_price': decision.get('entry_price'),
                    'entry_rsi': decision.get('entry_rsi'),
                    'entry_time': decision.get('entry_time'),
                    'size': decision.get('size')
                }
            }
            
            self.logger.info(f"DECISION_TRADING_JSON: {json.dumps(decision_debug, indent=2)}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du logging de la décision: {e}")
    
    def log_order_execution(self, execution_result):
        """Log l'exécution d'un ordre pour la nouvelle stratégie."""
        try:
            if execution_result.get('success', False):
                self.logger.info("Ordre exécuté (Nouvelle Stratégie)", extra={
                    'event': 'order_execution',
                    'success': True,
                    'action': execution_result['decision']['action'],
                    'position_type': execution_result.get('position_type'),
                    'order_id': execution_result.get('order_id'),
                    'filled_size': execution_result.get('filled_size'),
                    'price': execution_result.get('price')
                })
                
                # Log JSON détaillé
                execution_debug = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'execution': {
                        'success': True,
                        'action': execution_result['decision']['action'],
                        'position_type': execution_result.get('position_type'),
                        'order_id': execution_result.get('order_id'),
                        'filled_size': execution_result.get('filled_size'),
                        'price': execution_result.get('price'),
                        'reason': execution_result['decision'].get('reason')
                    }
                }
                
                self.logger.info(f"EXECUTION_ORDRE_JSON: {json.dumps(execution_debug, indent=2)}")
                
            else:
                self.logger.error("Erreur exécution ordre", extra={
                    'event': 'order_execution',
                    'success': False,
                    'action': execution_result['decision']['action'],
                    'error': execution_result.get('error'),
                    'reason': execution_result.get('reason')
                })
                
        except Exception as e:
            self.logger.error(f"Erreur lors du logging de l'exécution: {e}")
    
    def log_state_update(self, state_manager):
        """Log la mise à jour de l'état pour la nouvelle stratégie."""
        try:
            current_pos = state_manager.get_current_position()
            last_position_type = state_manager.get_last_position_type()
            vi1_phase = state_manager.get_vi1_current_phase()
            vi1_timestamp = state_manager.get_vi1_phase_timestamp()
        
            self.logger.info("État mis à jour (Nouvelle Stratégie)", extra={
                'event': 'state_update',
                'has_open_position': current_pos is not None,
                'position_type': current_pos['type'] if current_pos else None,
                'last_position_type': last_position_type,
                'vi1_current_phase': vi1_phase,
                'vi1_phase_timestamp': vi1_timestamp
            })
            
        except Exception as e:
            self.logger.error(f"Erreur lors du logging de l'état: {e}")
    
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
    
    # Test avec données structurées pour nouvelle stratégie
    test_analysis = {
        'rsi': 55.0,
        'vi1': 40200.0,
        'vi2': 40150.0,
        'vi3': 40100.0,
        'vi1_above_close': False,
        'vi2_above_close': False,
        'vi3_above_close': False,
        'current_close': 40000.0,
        'current_candle': {
            'time': 1234567890,
            'datetime': '2025-07-25T10:00:00',
            'open': '40000',
            'high': '40100',
            'low': '39900',
            'close': '40000',
            'count': 100
        },
        'short_conditions': True,
        'long_vi1_conditions': True,
        'long_vi2_conditions': False,
        'long_reentry_conditions': False
    }
    
    test_conditions = {
        'trading_allowed': True,
        'short_ready': True,
        'long_vi1_ready': True,
        'long_vi2_ready': False,
        'long_reentry_ready': False,
        'vi1_protection_active': False
    }
    
    logger.log_technical_analysis(test_analysis, test_conditions)
    
    print("Logs créés dans le dossier 'logs/'") 