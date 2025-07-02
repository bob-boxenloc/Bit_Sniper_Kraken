"""
Module de gestion avancée des erreurs réseau pour BitSniper
Implémente retry automatique, backoff exponentiel, timeout, circuit breaker et monitoring
"""

import time
import random
import logging
from functools import wraps
from typing import Callable, Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading

@dataclass
class ErrorStats:
    """Statistiques des erreurs pour le circuit breaker"""
    total_errors: int = 0
    consecutive_errors: int = 0
    last_error_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    error_history: List[Dict] = field(default_factory=list)
    
    def add_error(self, error: Exception, context: str = ""):
        """Ajoute une erreur aux statistiques"""
        self.total_errors += 1
        self.consecutive_errors += 1
        self.last_error_time = datetime.now()
        
        error_info = {
            'timestamp': self.last_error_time,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context
        }
        self.error_history.append(error_info)
        
        # Garder seulement les 100 dernières erreurs
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]
    
    def add_success(self):
        """Enregistre un succès"""
        self.consecutive_errors = 0
        self.last_success_time = datetime.now()
    
    def is_circuit_open(self, threshold: int = 5, timeout_seconds: int = 60) -> bool:
        """Vérifie si le circuit breaker doit être ouvert"""
        if self.consecutive_errors >= threshold:
            if self.last_error_time:
                time_since_last_error = (datetime.now() - self.last_error_time).total_seconds()
                return time_since_last_error < timeout_seconds
        return False

class NetworkErrorHandler:
    """
    Gestionnaire avancé des erreurs réseau avec retry, backoff, timeout et circuit breaker
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_stats = ErrorStats()
        self.circuit_breaker_enabled = True
        self.lock = threading.Lock()
        
        # Configuration par défaut
        self.default_max_retries = 3
        self.default_base_delay = 1.0  # secondes
        self.default_max_delay = 60.0  # secondes
        self.default_timeout = 30.0  # secondes
        self.default_circuit_threshold = 5
        self.default_circuit_timeout = 60  # secondes
        
    def retry_with_backoff(
        self,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        timeout: Optional[float] = None,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on_exceptions: tuple = (Exception,)
    ):
        """
        Décorateur pour retry avec backoff exponentiel
        
        :param max_retries: Nombre maximum de tentatives
        :param base_delay: Délai de base en secondes
        :param max_delay: Délai maximum en secondes
        :param timeout: Timeout par tentative en secondes
        :param exponential_base: Base pour le backoff exponentiel
        :param jitter: Ajouter du jitter pour éviter les thundering herds
        :param retry_on_exceptions: Types d'exceptions à retry
        """
        max_retries = max_retries or self.default_max_retries
        base_delay = base_delay or self.default_base_delay
        max_delay = max_delay or self.default_max_delay
        timeout = timeout or self.default_timeout
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        # Vérifier le circuit breaker
                        if self.circuit_breaker_enabled and self.error_stats.is_circuit_open(
                            self.default_circuit_threshold, self.default_circuit_timeout
                        ):
                            raise Exception("Circuit breaker ouvert - trop d'erreurs récentes")
                        
                        # Exécuter la fonction avec timeout
                        if timeout:
                            import signal
                            
                            def timeout_handler(signum, frame):
                                raise TimeoutError(f"Timeout après {timeout} secondes")
                            
                            # Installer le handler de timeout
                            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                            signal.alarm(int(timeout))
                            
                            try:
                                result = func(*args, **kwargs)
                                signal.alarm(0)  # Désactiver l'alarme
                                signal.signal(signal.SIGALRM, old_handler)  # Restaurer l'ancien handler
                                
                                # Succès - réinitialiser les stats d'erreur
                                with self.lock:
                                    self.error_stats.add_success()
                                
                                return result
                            except TimeoutError:
                                signal.alarm(0)
                                signal.signal(signal.SIGALRM, old_handler)
                                raise
                        else:
                            result = func(*args, **kwargs)
                            
                            # Succès - réinitialiser les stats d'erreur
                            with self.lock:
                                self.error_stats.add_success()
                            
                            return result
                            
                    except retry_on_exceptions as e:
                        last_exception = e
                        
                        # Enregistrer l'erreur
                        with self.lock:
                            self.error_stats.add_error(e, f"{func.__name__} (tentative {attempt + 1})")
                        
                        # Si c'est la dernière tentative, lever l'exception
                        if attempt == max_retries:
                            self.logger.error(
                                f"Échec après {max_retries + 1} tentatives pour {func.__name__}: {e}"
                            )
                            raise
                        
                        # Calculer le délai avec backoff exponentiel
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        
                        # Ajouter du jitter si activé
                        if jitter:
                            delay *= (0.5 + random.random() * 0.5)
                        
                        self.logger.warning(
                            f"Tentative {attempt + 1}/{max_retries + 1} échouée pour {func.__name__}: {e}. "
                            f"Réessai dans {delay:.2f}s..."
                        )
                        
                        time.sleep(delay)
                
                # Ne devrait jamais arriver
                raise last_exception
            
            return wrapper
        return decorator
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Retourne un résumé des erreurs pour le monitoring"""
        with self.lock:
            return {
                'total_errors': self.error_stats.total_errors,
                'consecutive_errors': self.error_stats.consecutive_errors,
                'last_error_time': self.error_stats.last_error_time.isoformat() if self.error_stats.last_error_time else None,
                'last_success_time': self.error_stats.last_success_time.isoformat() if self.error_stats.last_success_time else None,
                'circuit_open': self.error_stats.is_circuit_open(self.default_circuit_threshold, self.default_circuit_timeout),
                'recent_errors': self.error_stats.error_history[-10:] if self.error_stats.error_history else []
            }
    
    def reset_error_stats(self):
        """Réinitialise les statistiques d'erreur"""
        with self.lock:
            self.error_stats = ErrorStats()
    
    def set_circuit_breaker(self, enabled: bool):
        """Active/désactive le circuit breaker"""
        self.circuit_breaker_enabled = enabled
        self.logger.info(f"Circuit breaker {'activé' if enabled else 'désactivé'}")
    
    def is_healthy(self) -> bool:
        """Vérifie si le système est en bonne santé"""
        with self.lock:
            return (
                self.error_stats.consecutive_errors < self.default_circuit_threshold and
                not self.error_stats.is_circuit_open(self.default_circuit_threshold, self.default_circuit_timeout)
            )

# Instance globale pour être utilisée dans tout le projet
error_handler = NetworkErrorHandler()

def handle_network_errors(
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    timeout: Optional[float] = None,
    retry_on_exceptions: tuple = (Exception,)
):
    """
    Décorateur simplifié pour utiliser le gestionnaire d'erreurs global
    """
    return error_handler.retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        timeout=timeout,
        retry_on_exceptions=retry_on_exceptions
    ) 