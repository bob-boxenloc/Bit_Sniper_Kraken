"""
Démonstration de la gestion avancée des erreurs réseau pour BitSniper
"""

import time
import logging
from core.error_handler import NetworkErrorHandler, handle_network_errors, error_handler
from core.monitor import SystemMonitor, system_monitor

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def demo_retry_with_backoff():
    """Démonstration du retry avec backoff exponentiel"""
    print("\n" + "="*60)
    print("DÉMONSTRATION: RETRY AVEC BACKOFF EXPONENTIEL")
    print("="*60)
    
    # Fonction qui simule des erreurs réseau temporaires
    call_count = 0
    def simulate_network_error():
        nonlocal call_count
        call_count += 1
        print(f"  Tentative {call_count}...")
        
        if call_count < 4:
            raise ConnectionError(f"Erreur réseau temporaire #{call_count}")
        else:
            print("  ✅ Connexion réussie!")
            return "Données récupérées avec succès"
    
    # Appliquer le décorateur de retry
    robust_function = handle_network_errors(
        max_retries=5,
        base_delay=1.0,
        max_delay=10.0,
        timeout=30.0
    )(simulate_network_error)
    
    print("Exécution d'une fonction avec retry automatique...")
    start_time = time.time()
    
    try:
        result = robust_function()
        end_time = time.time()
        print(f"✅ Résultat: {result}")
        print(f"⏱️  Temps total: {end_time - start_time:.2f} secondes")
        
    except Exception as e:
        print(f"❌ Échec final après tous les retry: {e}")

def demo_circuit_breaker():
    """Démonstration du circuit breaker"""
    print("\n" + "="*60)
    print("DÉMONSTRATION: CIRCUIT BREAKER")
    print("="*60)
    
    # Fonction qui échoue toujours (simule un service en panne)
    def failing_service():
        raise Exception("Service temporairement indisponible")
    
    robust_service = handle_network_errors(
        max_retries=2,
        base_delay=0.5
    )(failing_service)
    
    print("Test du circuit breaker avec un service en panne...")
    
    # Exécuter plusieurs fois pour déclencher le circuit breaker
    for i in range(8):
        try:
            print(f"  Tentative {i+1}...")
            robust_service()
        except Exception as e:
            print(f"    ❌ Échec: {e}")
        
        # Vérifier l'état du circuit breaker
        if error_handler.error_stats.is_circuit_open():
            print("    🔌 Circuit breaker OUVERT - Arrêt des tentatives")
            break
    
    print(f"📊 Statistiques d'erreur:")
    print(f"   - Erreurs totales: {error_handler.error_stats.total_errors}")
    print(f"   - Erreurs consécutives: {error_handler.error_stats.consecutive_errors}")
    print(f"   - Circuit ouvert: {error_handler.error_stats.is_circuit_open()}")

def demo_system_monitoring():
    """Démonstration du monitoring système"""
    print("\n" + "="*60)
    print("DÉMONSTRATION: MONITORING SYSTÈME")
    print("="*60)
    
    # Afficher le statut système actuel
    print("📊 Statut système actuel:")
    system_monitor.print_status()
    
    # Simuler quelques erreurs pour voir les alertes
    print("\n🔍 Simulation d'erreurs pour tester les alertes...")
    for i in range(3):
        error_handler.error_stats.add_error(
            Exception(f"Erreur de test #{i+1}"),
            f"test_context_{i+1}"
        )
        time.sleep(0.1)
    
    # Vérifier les alertes
    alerts = system_monitor.check_alerts()
    if alerts:
        print("\n🚨 Alertes détectées:")
        for alert in alerts:
            print(f"   • {alert}")
    else:
        print("\n✅ Aucune alerte détectée")
    
    # Afficher un résumé des erreurs
    error_summary = error_handler.get_error_summary()
    print(f"\n📈 Résumé des erreurs:")
    print(f"   - Erreurs totales: {error_summary['total_errors']}")
    print(f"   - Erreurs consécutives: {error_summary['consecutive_errors']}")
    print(f"   - Circuit ouvert: {error_summary['circuit_open']}")
    
    if error_summary['recent_errors']:
        print(f"   - Dernières erreurs:")
        for error in error_summary['recent_errors'][-3:]:  # 3 dernières
            print(f"     • {error['timestamp']}: {error['error_message']}")

def demo_error_recovery():
    """Démonstration de la récupération d'erreurs"""
    print("\n" + "="*60)
    print("DÉMONSTRATION: RÉCUPÉRATION D'ERREURS")
    print("="*60)
    
    # Simuler une récupération après des erreurs
    print("Simulation d'une récupération après des erreurs...")
    
    # Ajouter quelques erreurs
    for i in range(5):
        error_handler.error_stats.add_error(
            Exception(f"Erreur avant récupération #{i+1}"),
            "recovery_test"
        )
    
    print(f"État après erreurs:")
    print(f"  - Erreurs consécutives: {error_handler.error_stats.consecutive_errors}")
    print(f"  - Circuit ouvert: {error_handler.error_stats.is_circuit_open()}")
    
    # Simuler des succès pour récupérer
    print("\nSimulation de succès pour récupérer...")
    for i in range(3):
        error_handler.error_stats.add_success()
        print(f"  Succès #{i+1} - Erreurs consécutives: {error_handler.error_stats.consecutive_errors}")
    
    print(f"\nÉtat après récupération:")
    print(f"  - Erreurs consécutives: {error_handler.error_stats.consecutive_errors}")
    print(f"  - Circuit ouvert: {error_handler.error_stats.is_circuit_open()}")
    print(f"  - Système sain: {error_handler.is_healthy()}")

def demo_monitoring_data_save():
    """Démonstration de la sauvegarde des données de monitoring"""
    print("\n" + "="*60)
    print("DÉMONSTRATION: SAUVEGARDE DES DONNÉES")
    print("="*60)
    
    # Générer et sauvegarder les données de monitoring
    filename = "demo_monitoring_data.json"
    
    try:
        system_monitor.save_monitoring_data(filename)
        print(f"✅ Données de monitoring sauvegardées dans {filename}")
        
        # Afficher un aperçu des données sauvegardées
        import json
        with open(filename, 'r') as f:
            data = json.load(f)
        
        print(f"\n📄 Aperçu des données sauvegardées:")
        print(f"   - Timestamp: {data['timestamp']}")
        print(f"   - Santé système: {'OK' if data['system_health']['is_healthy'] else 'PROBLÈME'}")
        print(f"   - Erreurs totales: {data['system_health']['error_count']}")
        print(f"   - Trades totaux: {data['trading_metrics']['total_trades']}")
        print(f"   - Alertes: {len(data['alerts'])}")
        
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")

def main():
    """Fonction principale de démonstration"""
    print("🚀 DÉMONSTRATION DE LA GESTION AVANCÉE DES ERREURS RÉSEAU")
    print("="*60)
    print("Ce script démontre les fonctionnalités de robustesse du bot BitSniper:")
    print("• Retry automatique avec backoff exponentiel")
    print("• Circuit breaker pour éviter les surcharges")
    print("• Monitoring système en temps réel")
    print("• Système d'alertes intelligent")
    print("• Sauvegarde des données de monitoring")
    print("="*60)
    
    try:
        # Exécuter les démonstrations
        demo_retry_with_backoff()
        demo_circuit_breaker()
        demo_system_monitoring()
        demo_error_recovery()
        demo_monitoring_data_save()
        
        print("\n" + "="*60)
        print("✅ DÉMONSTRATION TERMINÉE AVEC SUCCÈS")
        print("="*60)
        print("Le bot BitSniper est maintenant équipé d'une gestion d'erreurs")
        print("robuste pour fonctionner de manière fiable 24/7 sur un VPS.")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la démonstration: {e}")
        logger.error(f"Erreur dans la démonstration: {e}")

if __name__ == "__main__":
    main() 