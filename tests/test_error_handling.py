"""
Tests pour la gestion avancée des erreurs réseau
"""

import time
import logging
import unittest
from unittest.mock import Mock, patch
from core.error_handler import NetworkErrorHandler, handle_network_errors, error_handler
from core.monitor import SystemMonitor, system_monitor

class TestErrorHandling(unittest.TestCase):
    """Tests pour la gestion d'erreurs"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        self.error_handler = NetworkErrorHandler()
        self.monitor = SystemMonitor()
        
    def test_retry_with_backoff(self):
        """Test du retry avec backoff exponentiel"""
        
        # Fonction qui échoue 2 fois puis réussit
        call_count = 0
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Erreur test {call_count}")
            return "succès"
        
        # Appliquer le décorateur de retry
        decorated_func = self.error_handler.retry_with_backoff(
            max_retries=3, base_delay=0.1, max_delay=1.0
        )(failing_function)
        
        # Exécuter la fonction
        start_time = time.time()
        result = decorated_func()
        end_time = time.time()
        
        # Vérifications
        self.assertEqual(result, "succès")
        self.assertEqual(call_count, 3)
        self.assertGreater(end_time - start_time, 0.2)  # Au moins 2 délais
        
    def test_circuit_breaker(self):
        """Test du circuit breaker"""
        
        # Fonction qui échoue toujours
        def always_failing():
            raise Exception("Erreur permanente")
        
        decorated_func = self.error_handler.retry_with_backoff(
            max_retries=2, base_delay=0.01
        )(always_failing)
        
        # Exécuter plusieurs fois pour déclencher le circuit breaker
        for _ in range(6):
            try:
                decorated_func()
            except:
                pass
        
        # Vérifier que le circuit breaker est ouvert
        self.assertTrue(self.error_handler.error_stats.is_circuit_open())
        
    def test_error_stats(self):
        """Test des statistiques d'erreur"""
        
        # Ajouter quelques erreurs
        test_error = Exception("Test error")
        self.error_handler.error_stats.add_error(test_error, "test_context")
        self.error_handler.error_stats.add_error(test_error, "test_context2")
        
        # Vérifier les stats
        self.assertEqual(self.error_handler.error_stats.total_errors, 2)
        self.assertEqual(self.error_handler.error_stats.consecutive_errors, 2)
        self.assertIsNotNone(self.error_handler.error_stats.last_error_time)
        
        # Ajouter un succès
        self.error_handler.error_stats.add_success()
        self.assertEqual(self.error_handler.error_stats.consecutive_errors, 0)
        self.assertIsNotNone(self.error_handler.error_stats.last_success_time)
        
    def test_system_monitor(self):
        """Test du monitoring système"""
        
        # Récupérer la santé du système
        health = self.monitor.get_system_health()
        
        # Vérifications de base
        self.assertIsInstance(health.timestamp, type(time.time()))
        self.assertIsInstance(health.is_healthy, bool)
        self.assertIsInstance(health.error_count, int)
        self.assertIsInstance(health.uptime_seconds, float)
        
        # Récupérer les métriques de trading
        metrics = self.monitor.get_trading_metrics()
        
        # Vérifications de base
        self.assertIsInstance(metrics.timestamp, type(time.time()))
        self.assertIsInstance(metrics.total_trades, int)
        self.assertIsInstance(metrics.win_rate, float)
        
    def test_alert_system(self):
        """Test du système d'alertes"""
        
        # Simuler des erreurs pour déclencher des alertes
        for _ in range(12):
            self.error_handler.error_stats.add_error(Exception("Test alert"))
        
        # Vérifier les alertes
        alerts = self.monitor.check_alerts()
        self.assertGreater(len(alerts), 0)
        
        # Vérifier qu'il y a une alerte pour les erreurs consécutives
        error_alerts = [a for a in alerts if "erreurs consécutives" in a]
        self.assertGreater(len(error_alerts), 0)
        
    def test_decorator_simplified(self):
        """Test du décorateur simplifié"""
        
        call_count = 0
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Test")
            return "OK"
        
        # Utiliser le décorateur simplifié
        decorated = handle_network_errors(max_retries=2, base_delay=0.01)(test_func)
        result = decorated()
        
        self.assertEqual(result, "OK")
        self.assertEqual(call_count, 2)

class TestIntegration(unittest.TestCase):
    """Tests d'intégration"""
    
    def test_error_handler_global(self):
        """Test de l'instance globale du gestionnaire d'erreurs"""
        
        # Vérifier que l'instance globale existe
        self.assertIsNotNone(error_handler)
        self.assertIsInstance(error_handler, NetworkErrorHandler)
        
        # Vérifier que l'instance globale du monitor existe
        self.assertIsNotNone(system_monitor)
        self.assertIsInstance(system_monitor, SystemMonitor)
        
    def test_monitoring_data_save(self):
        """Test de la sauvegarde des données de monitoring"""
        
        # Générer des données de monitoring
        summary = system_monitor.get_system_summary()
        
        # Vérifier la structure des données
        self.assertIn('timestamp', summary)
        self.assertIn('system_health', summary)
        self.assertIn('trading_metrics', summary)
        self.assertIn('alerts', summary)
        self.assertIn('error_summary', summary)
        
        # Test de sauvegarde (avec un nom de fichier temporaire)
        test_filename = "test_monitoring_data.json"
        try:
            system_monitor.save_monitoring_data(test_filename)
            
            # Vérifier que le fichier a été créé
            import os
            self.assertTrue(os.path.exists(test_filename))
            
        finally:
            # Nettoyer
            import os
            if os.path.exists(test_filename):
                os.remove(test_filename)

if __name__ == "__main__":
    # Configuration du logging pour les tests
    logging.basicConfig(level=logging.INFO)
    
    # Exécuter les tests
    unittest.main(verbosity=2) 