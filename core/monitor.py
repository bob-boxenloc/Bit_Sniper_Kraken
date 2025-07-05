"""
Module de monitoring pour BitSniper
Surveille la santé du système, les erreurs réseau et les performances
"""

import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from core.error_handler import error_handler
from core.state_manager import StateManager

@dataclass
class SystemHealth:
    """État de santé du système"""
    timestamp: datetime
    is_healthy: bool
    error_count: int
    consecutive_errors: int
    circuit_open: bool
    last_success: Optional[datetime]
    last_error: Optional[datetime]
    uptime_seconds: float
    memory_usage_mb: float
    cpu_usage_percent: float

@dataclass
class TradingMetrics:
    """Métriques de trading"""
    timestamp: datetime
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_pnl: float
    win_rate: float
    average_trade_duration: float
    positions_open: int
    total_volume_traded: float

class SystemMonitor:
    """
    Moniteur système pour BitSniper
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = datetime.now()
        self.health_history: List[SystemHealth] = []
        self.trading_history: List[TradingMetrics] = []
        self.state_manager = StateManager()
        
        # Configuration
        self.max_health_history = 1000  # Garder 1000 points de santé
        self.max_trading_history = 1000  # Garder 1000 métriques de trading
        self.alert_threshold_errors = 10  # Alerte si plus de 10 erreurs consécutives
        self.alert_threshold_circuit = True  # Alerte si circuit breaker ouvert
        
    def get_system_health(self) -> SystemHealth:
        """Récupère l'état de santé actuel du système"""
        try:
            # Récupérer les stats d'erreur
            error_summary = error_handler.get_error_summary()
            
            # Calculer l'uptime
            uptime = (datetime.now() - self.start_time).total_seconds()
            
            # Récupérer les métriques système (approximatif)
            import psutil
            memory_usage = psutil.virtual_memory().used / (1024 * 1024)  # MB
            cpu_usage = psutil.cpu_percent(interval=1)
            
            health = SystemHealth(
                timestamp=datetime.now(),
                is_healthy=error_handler.is_healthy(),
                error_count=error_summary['total_errors'],
                consecutive_errors=error_summary['consecutive_errors'],
                circuit_open=error_summary['circuit_open'],
                last_success=datetime.fromisoformat(error_summary['last_success_time']) if error_summary['last_success_time'] else None,
                last_error=datetime.fromisoformat(error_summary['last_error_time']) if error_summary['last_error_time'] else None,
                uptime_seconds=uptime,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage
            )
            
            # Ajouter à l'historique
            self.health_history.append(health)
            if len(self.health_history) > self.max_health_history:
                self.health_history = self.health_history[-self.max_health_history:]
            
            return health
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération de la santé système: {e}")
            # Retourner un état de santé par défaut en cas d'erreur
            return SystemHealth(
                timestamp=datetime.now(),
                is_healthy=False,
                error_count=0,
                consecutive_errors=0,
                circuit_open=False,
                last_success=None,
                last_error=None,
                uptime_seconds=(datetime.now() - self.start_time).total_seconds(),
                memory_usage_mb=0,
                cpu_usage_percent=0
            )
    
    def get_trading_metrics(self) -> TradingMetrics:
        """Récupère les métriques de trading actuelles"""
        try:
            # Récupérer l'état du trading depuis le state manager
            state = self.state_manager.state
            
            # Calculer les métriques basées sur l'état
            total_trades = len(state.get('trade_history', []))
            successful_trades = len([t for t in state.get('trade_history', []) if t.get('success', False)])
            failed_trades = total_trades - successful_trades
            win_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Calculer le PnL total
            total_pnl = sum(t.get('pnl', 0) for t in state.get('trade_history', []))
            
            # Calculer la durée moyenne des trades
            trade_durations = []
            for trade in state.get('trade_history', []):
                if 'entry_time' in trade and 'exit_time' in trade:
                    duration = (trade['exit_time'] - trade['entry_time']).total_seconds()
                    trade_durations.append(duration)
            
            avg_duration = sum(trade_durations) / len(trade_durations) if trade_durations else 0
            
            # Compter les positions ouvertes
            positions_open = len(state.get('open_positions', []))
            
            # Calculer le volume total échangé
            total_volume = sum(t.get('size', 0) for t in state.get('trade_history', []))
            
            metrics = TradingMetrics(
                timestamp=datetime.now(),
                total_trades=total_trades,
                successful_trades=successful_trades,
                failed_trades=failed_trades,
                total_pnl=total_pnl,
                win_rate=win_rate,
                average_trade_duration=avg_duration,
                positions_open=positions_open,
                total_volume_traded=total_volume
            )
            
            # Ajouter à l'historique
            self.trading_history.append(metrics)
            if len(self.trading_history) > self.max_trading_history:
                self.trading_history = self.trading_history[-self.max_trading_history:]
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des métriques trading: {e}")
            # Retourner des métriques par défaut en cas d'erreur
            return TradingMetrics(
                timestamp=datetime.now(),
                total_trades=0,
                successful_trades=0,
                failed_trades=0,
                total_pnl=0.0,
                win_rate=0.0,
                average_trade_duration=0.0,
                positions_open=0,
                total_volume_traded=0.0
            )
    
    def check_alerts(self) -> List[str]:
        """Vérifie s'il y a des alertes à déclencher"""
        alerts = []
        
        try:
            health = self.get_system_health()
            
            # Alerte si trop d'erreurs consécutives
            if health.consecutive_errors >= self.alert_threshold_errors:
                alerts.append(f"ALERTE: {health.consecutive_errors} erreurs consécutives")
            
            # Alerte si circuit breaker ouvert
            if health.circuit_open and self.alert_threshold_circuit:
                alerts.append("ALERTE: Circuit breaker ouvert")
            
            # Alerte si utilisation mémoire élevée (>80%)
            if health.memory_usage_mb > 1000:  # Plus de 1GB
                alerts.append(f"ALERTE: Utilisation mémoire élevée ({health.memory_usage_mb:.1f} MB)")
            
            # Alerte si utilisation CPU élevée (>90%)
            if health.cpu_usage_percent > 90:
                alerts.append(f"ALERTE: Utilisation CPU élevée ({health.cpu_usage_percent:.1f}%)")
            
            # Alerte si pas de succès depuis trop longtemps
            if health.last_success:
                time_since_success = (datetime.now() - health.last_success).total_seconds()
                if time_since_success > 3600:  # Plus d'1 heure
                    alerts.append(f"ALERTE: Aucun succès depuis {time_since_success/3600:.1f} heures")
            
            # Log des alertes
            for alert in alerts:
                self.logger.warning(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification des alertes: {e}")
            return ["ALERTE: Erreur lors de la vérification des alertes"]
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Retourne un résumé complet du système"""
        try:
            health = self.get_system_health()
            trading = self.get_trading_metrics()
            alerts = self.check_alerts()
            
            summary = {
                'timestamp': datetime.now().isoformat(),
                'system_health': asdict(health),
                'trading_metrics': asdict(trading),
                'alerts': alerts,
                'error_summary': error_handler.get_error_summary()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération du résumé système: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'system_health': None,
                'trading_metrics': None,
                'alerts': ["Erreur lors de la génération du résumé"],
                'error_summary': {}
            }
    
    def save_monitoring_data(self, filename: str = "monitoring_data.json"):
        """Sauvegarde les données de monitoring dans un fichier JSON"""
        try:
            summary = self.get_system_summary()
            
            # Ajouter l'historique des dernières données
            summary['health_history'] = [asdict(h) for h in self.health_history[-100:]]
            summary['trading_history'] = [asdict(t) for t in self.trading_history[-100:]]
            
            with open(filename, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            self.logger.info(f"Données de monitoring sauvegardées dans {filename}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde des données de monitoring: {e}")
    
    def print_status(self):
        """Affiche le statut actuel du système"""
        try:
            summary = self.get_system_summary()
            
            print("\n" + "="*60)
            print("STATUT SYSTÈME BITSNIPER")
            print("="*60)
            
            # Santé système
            health = summary['system_health']
            print(f"🔄 Santé: {'✅ OK' if health['is_healthy'] else '❌ PROBLÈME'}")
            print(f"⏱️  Uptime: {health['uptime_seconds']/3600:.1f} heures")
            print(f"💾 Mémoire: {health['memory_usage_mb']:.1f} MB")
            print(f"🖥️  CPU: {health['cpu_usage_percent']:.1f}%")
            
            # Erreurs
            print(f"❌ Erreurs totales: {health['error_count']}")
            print(f"⚠️  Erreurs consécutives: {health['consecutive_errors']}")
            print(f"🔌 Circuit breaker: {'OUVERT' if health['circuit_open'] else 'FERMÉ'}")
            
            # Trading
            trading = summary['trading_metrics']
            print(f"📊 Trades totaux: {trading['total_trades']}")
            print(f"✅ Trades réussis: {trading['successful_trades']}")
            print(f"❌ Trades échoués: {trading['failed_trades']}")
            print(f"📈 Win rate: {trading['win_rate']:.1f}%")
            print(f"💰 PnL total: ${trading['total_pnl']:.2f}")
            print(f"📦 Positions ouvertes: {trading['positions_open']}")
            
            # Alertes
            if summary['alerts']:
                print("\n🚨 ALERTES:")
                for alert in summary['alerts']:
                    print(f"   • {alert}")
            
            print("="*60)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'affichage du statut: {e}")
            print(f"❌ Erreur lors de l'affichage du statut: {e}")

# Instance globale pour être utilisée dans tout le projet
system_monitor = SystemMonitor() 