#!/usr/bin/env python3
"""
Script de test pour vérifier la configuration des variables d'environnement
"""

import os
import sys

def test_environment_variables():
    """Teste la présence des variables d'environnement requises"""
    
    required_vars = [
        'KRAKEN_API_KEY',
        'KRAKEN_API_SECRET'
    ]
    
    missing_vars = []
    
    print("🔍 Vérification des variables d'environnement...")
    print("=" * 50)
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Masquer la valeur pour la sécurité
            masked_value = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '****'
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"❌ {var}: MANQUANTE")
            missing_vars.append(var)
    
    print("=" * 50)
    
    if missing_vars:
        print(f"❌ ERREUR: Variables manquantes: {', '.join(missing_vars)}")
        print("\n📋 Solutions:")
        print("1. Vérifiez que les variables sont définies dans le service systemd")
        print("2. Ou définissez-les dans /etc/environment")
        print("3. Ou exportez-les manuellement: export KRAKEN_API_KEY='votre_clé'")
        return False
    else:
        print("✅ Toutes les variables d'environnement sont configurées correctement!")
        return True

def test_kraken_connection():
    """Teste la connexion à l'API Kraken"""
    
    try:
        from trading.kraken_client import KrakenFuturesClient
        
        print("\n🔗 Test de connexion à Kraken Futures...")
        print("=" * 50)
        
        client = KrakenFuturesClient()
        
        if client.test_connection():
            print("✅ Connexion à Kraken Futures réussie!")
            
            from data.market_data import MarketData

            # Récupérer la dernière bougie 15m
            md = MarketData()
            candles = md.get_ohlcv_15m(limit=2)
            last_candle = candles[-1]
            current_price = float(last_candle['close'])
            
            # Test de récupération du compte
            account = client.get_account_summary(current_price)
            if account:
                print("✅ Récupération du compte réussie!")
                print(f"   Solde USD: ${account['wallet']['usd_balance']:.2f}")
                print(f"   Prix BTC: ${account['current_btc_price']:.2f}")
                return True
            else:
                print("❌ Échec de récupération du compte")
                return False
        else:
            print("❌ Échec de connexion à Kraken Futures")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test de connexion: {e}")
        return False

def test_error_handling():
    """Teste la gestion d'erreurs"""
    
    try:
        from core.error_handler import error_handler
        from core.monitor import system_monitor
        
        print("\n🛡️ Test de la gestion d'erreurs...")
        print("=" * 50)
        
        # Test du gestionnaire d'erreurs
        error_summary = error_handler.get_error_summary()
        print(f"✅ Gestionnaire d'erreurs: OK")
        print(f"   Erreurs totales: {error_summary['total_errors']}")
        print(f"   Circuit breaker: {'OUVERT' if error_summary['circuit_open'] else 'FERMÉ'}")
        
        # Test du monitoring
        health = system_monitor.get_system_health()
        print(f"✅ Monitoring système: OK")
        print(f"   Santé: {'OK' if health.is_healthy else 'PROBLÈME'}")
        print(f"   Uptime: {health.uptime_seconds:.1f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test de gestion d'erreurs: {e}")
        return False

def test_file_permissions():
    """Teste les permissions des fichiers"""
    
    print("\n📁 Test des permissions de fichiers...")
    print("=" * 50)
    
    required_dirs = [
        'logs',
        'data'
    ]
    
    required_files = [
        'main.py',
        'requirements.txt'
    ]
    
    all_ok = True
    
    # Vérifier les dossiers
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            if os.access(dir_name, os.W_OK):
                print(f"✅ Dossier {dir_name}: accessible en écriture")
            else:
                print(f"❌ Dossier {dir_name}: pas accessible en écriture")
                all_ok = False
        else:
            print(f"⚠️  Dossier {dir_name}: n'existe pas (sera créé automatiquement)")
    
    # Vérifier les fichiers
    for file_name in required_files:
        if os.path.exists(file_name):
            if os.access(file_name, os.R_OK):
                print(f"✅ Fichier {file_name}: accessible en lecture")
            else:
                print(f"❌ Fichier {file_name}: pas accessible en lecture")
                all_ok = False
        else:
            print(f"❌ Fichier {file_name}: n'existe pas")
            all_ok = False
    
    return all_ok

def main():
    """Fonction principale de test"""
    
    print("🚀 TEST DE CONFIGURATION BITSNIPER")
    print("=" * 60)
    
    # Test des variables d'environnement
    env_ok = test_environment_variables()
    
    if not env_ok:
        print("\n❌ Configuration incomplète. Corrigez les variables d'environnement.")
        sys.exit(1)
    
    # Test des permissions
    perm_ok = test_file_permissions()
    
    if not perm_ok:
        print("\n⚠️  Problèmes de permissions détectés.")
        print("   Le bot peut fonctionner mais certains logs peuvent échouer.")
    
    # Test de la gestion d'erreurs
    error_ok = test_error_handling()
    
    if not error_ok:
        print("\n⚠️  Problèmes avec la gestion d'erreurs.")
        print("   Le bot peut fonctionner mais sera moins robuste.")
    
    # Test de connexion Kraken (optionnel)
    print("\n🔗 Test de connexion à Kraken (optionnel)...")
    print("   Ce test nécessite une connexion internet et des clés API valides.")
    
    try:
        kraken_ok = test_kraken_connection()
        
        if not kraken_ok:
            print("\n⚠️  Problème de connexion à Kraken.")
            print("   Vérifiez vos clés API et votre connexion internet.")
        else:
            print("\n✅ Connexion Kraken réussie!")
            
    except ImportError:
        print("   ⚠️  Modules Kraken non disponibles (normal en développement)")
    except Exception as e:
        print(f"   ⚠️  Erreur lors du test Kraken: {e}")
    
    print("\n" + "=" * 60)
    
    if env_ok:
        print("✅ CONFIGURATION DE BASE CORRECTE!")
        print("✅ Le bot peut être lancé avec: python main.py")
        
        if kraken_ok:
            print("✅ Connexion API fonctionnelle!")
        else:
            print("⚠️  Vérifiez la connexion API avant de lancer le bot.")
    else:
        print("❌ Configuration incomplète.")
        print("   Corrigez les problèmes avant de lancer le bot.")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 