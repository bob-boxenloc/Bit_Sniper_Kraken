#!/usr/bin/env python3
"""
Script de test pour les notifications email BitSniper
Teste l'envoi d'emails pour les entrées et sorties de positions
"""

import os
from core.notifications import BrevoNotifier

def test_notifications():
    """Teste l'envoi des notifications email."""
    print("🧪 TEST DES NOTIFICATIONS EMAIL BITSNIPER")
    print("=" * 50)
    
    # Vérifier les variables d'environnement
    api_key = os.getenv('BREVO_API_KEY')
    sender_email = os.getenv('BREVO_SENDER_EMAIL')
    receiver_email = os.getenv('BREVO_RECEIVER_EMAIL')
    
    if not all([api_key, sender_email, receiver_email]):
        print("❌ Variables d'environnement manquantes:")
        print(f"   BREVO_API_KEY: {'✅' if api_key else '❌'}")
        print(f"   BREVO_SENDER_EMAIL: {'✅' if sender_email else '❌'}")
        print(f"   BREVO_RECEIVER_EMAIL: {'✅' if receiver_email else '❌'}")
        print("\n🔧 Configuration requise dans .env:")
        print("   BREVO_API_KEY=votre_clé_api_brevo")
        print("   BREVO_SENDER_EMAIL=bot@votre_domaine.com")
        print("   BREVO_RECEIVER_EMAIL=votre_email@gmail.com")
        return False
    
    print("✅ Variables d'environnement configurées")
    print(f"   Expéditeur: {sender_email}")
    print(f"   Destinataire: {receiver_email}")
    
    # Initialiser le notificateur
    notifier = BrevoNotifier()
    
    if not notifier.enabled:
        print("❌ Notifications désactivées")
        return False
    
    print("✅ Notificateur Brevo initialisé")
    
    # Test 1: Entrée en position SHORT
    print("\n📧 Test 1: Notification d'entrée en position SHORT")
    success1 = notifier.send_trade_notification(
        action="ENTRÉE",
        position_type="SHORT",
        price="$45,250.00",
        size=0.0035
    )
    print(f"   Résultat: {'✅ Succès' if success1 else '❌ Échec'}")
    
    # Test 2: Sortie de position LONG_VI1
    print("\n📧 Test 2: Notification de sortie de position LONG_VI1")
    success2 = notifier.send_trade_notification(
        action="SORTIE",
        position_type="LONG_VI1",
        price="$46,100.00",
        pnl=125.50
    )
    print(f"   Résultat: {'✅ Succès' if success2 else '❌ Échec'}")
    
    # Test 3: Sortie d'urgence
    print("\n📧 Test 3: Notification de sortie d'urgence")
    success3 = notifier.send_trade_notification(
        action="SORTIE D'URGENCE",
        position_type="LONG_VI2",
        price="$44,800.00",
        pnl=-85.25
    )
    print(f"   Résultat: {'✅ Succès' if success3 else '❌ Échec'}")
    
    # Test 4: Sortie contrôle 3H
    print("\n📧 Test 4: Notification de sortie contrôle 3H")
    success4 = notifier.send_trade_notification(
        action="SORTIE CONTRÔLE 3H",
        position_type="SHORT",
        price="$45,500.00",
        pnl=45.75
    )
    print(f"   Résultat: {'✅ Succès' if success4 else '❌ Échec'}")
    
    # Test 5: Croisement VI1 BEARISH
    print("\n📧 Test 5: Notification de croisement VI1 BEARISH")
    success5 = notifier.send_trade_notification(
        action="CROISEMENT VI1",
        position_type="BEARISH (au-dessus)",
        price="$45,250.00"
    )
    print(f"   Résultat: {'✅ Succès' if success5 else '❌ Échec'}")
    
    # Test 6: Croisement VI1 BULLISH
    print("\n📧 Test 6: Notification de croisement VI1 BULLISH")
    success6 = notifier.send_trade_notification(
        action="CROISEMENT VI1",
        position_type="BULLISH (en-dessous)",
        price="$44,800.00"
    )
    print(f"   Résultat: {'✅ Succès' if success6 else '❌ Échec'}")
    
    # Test 7: Notification de crash TRADING
    print("\n📧 Test 7: Notification de crash TRADING")
    success7 = notifier.send_crash_notification(
        error_type="CRASH TRADING",
        error_message="Erreur de connexion à l'API Kraken",
        stack_trace="Traceback (most recent call last):\n  File 'main.py', line 340, in trading_loop\n    md = MarketData()\nConnectionError: [Errno 111] Connection refused",
        context="Test de notification de crash"
    )
    print(f"   Résultat: {'✅ Succès' if success7 else '❌ Échec'}")
    
    # Test 8: Notification de crash FATAL
    print("\n📧 Test 8: Notification de crash FATAL")
    success8 = notifier.send_crash_notification(
        error_type="CRASH FATAL",
        error_message="Erreur critique dans le système de monitoring",
        stack_trace="Traceback (most recent call last):\n  File 'main.py', line 900, in main\n    run_every_15min(trading_loop)\nSystemError: Critical system failure",
        context="Test de notification de crash fatal"
    )
    print(f"   Résultat: {'✅ Succès' if success8 else '❌ Échec'}")
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES TESTS")
    tests = [success1, success2, success3, success4, success5, success6, success7, success8]
    successful = sum(tests)
    total = len(tests)
    
    print(f"   Tests réussis: {successful}/{total}")
    print(f"   Taux de succès: {(successful/total)*100:.1f}%")
    
    if successful == total:
        print("🎉 Toutes les notifications fonctionnent parfaitement !")
        return True
    else:
        print("⚠️  Certaines notifications ont échoué")
        return False

if __name__ == "__main__":
    test_notifications()
