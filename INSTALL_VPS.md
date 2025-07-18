# 🚀 Guide d'installation complet de BitSniper sur VPS OVH

**Guide ultra-détaillé pour débutants - De l'achat du VPS à la mise en production**

---

## 📋 Table des matières

1. [Achat et configuration du VPS OVH](#1-achat-et-configuration-du-vps-ovh)
2. [Première connexion au VPS](#2-première-connexion-au-vps)
3. [Configuration de base du serveur](#3-configuration-de-base-du-serveur)
4. [Installation de Python et des outils](#4-installation-de-python-et-des-outils)
5. [Création de l'utilisateur dédié](#5-création-de-lutilisateur-dédié)
6. [Installation de BitSniper](#6-installation-de-bitsniper)
7. [Configuration des clés API Kraken](#7-configuration-des-clés-api-kraken)
8. [Test de la configuration](#8-test-de-la-configuration)
9. [Configuration du service systemd](#9-configuration-du-service-systemd)
10. [Lancement et monitoring](#10-lancement-et-monitoring)
11. [Sécurité et maintenance](#11-sécurité-et-maintenance)
12. [Résolution des problèmes](#12-résolution-des-problèmes)

---

## 1. Achat et configuration du VPS OVH

### 1.1 Création du compte OVH

1. **Aller sur OVH.com**
   - Ouvrez votre navigateur et allez sur [www.ovh.com](https://www.ovh.com)
   - Cliquez sur "Se connecter" en haut à droite

2. **Créer un compte**
   - Cliquez sur "Créer un compte"
   - Remplissez le formulaire avec vos informations
   - Validez votre email

### 1.2 Achat du VPS

1. **Choisir le VPS**
   - Dans votre espace client OVH, allez dans "Bare Metal Cloud" → "VPS"
   - Cliquez sur "Commander un VPS"

2. **Configuration recommandée**
   - **VPS SSD 1** : 3,50€/mois
   - **RAM** : 2 GB (suffisant pour BitSniper)
   - **CPU** : 1 vCore
   - **Stockage** : 20 GB SSD
   - **Bande passante** : Illimitée

3. **Options supplémentaires**
   - **Système d'exploitation** : Ubuntu 22.04 LTS
   - **Localisation** : France (Roubaix ou Strasbourg)
   - **Backup** : Optionnel (1€/mois supplémentaire)

4. **Finaliser la commande**
   - Vérifiez votre panier
   - Payez par carte bancaire
   - Notez votre **adresse IP** et vos **identifiants de connexion**

### 1.3 Récupération des informations de connexion

Après l'achat, OVH vous envoie un email avec :
- **Adresse IP du VPS** (ex: 51.68.123.45)
- **Nom d'utilisateur** (généralement `ubuntu` ou `root`)
- **Mot de passe** (si vous en avez défini un)
- **Clé SSH** (si vous en avez configuré une)

⚠️ **IMPORTANT** : Gardez ces informations précieusement !

---

## 2. Première connexion au VPS

### 2.1 Connexion SSH (Windows)

1. **Installer PuTTY** (si pas déjà fait)
   - Téléchargez PuTTY depuis [putty.org](https://www.putty.org/)
   - Installez-le sur votre ordinateur

2. **Configurer la connexion**
   - Ouvrez PuTTY
   - Dans "Host Name", entrez l'IP de votre VPS
   - Dans "Port", laissez 22
   - Cliquez sur "Open"

3. **Première connexion**
   - Acceptez l'avertissement de sécurité (cliquez "Oui")
   - Entrez votre nom d'utilisateur (généralement `ubuntu`)
   - Entrez votre mot de passe (les caractères ne s'affichent pas, c'est normal)

### 2.2 Connexion SSH (Mac/Linux)

1. **Ouvrir le Terminal**
   - Sur Mac : Applications → Utilitaires → Terminal
   - Sur Linux : Ctrl+Alt+T

2. **Se connecter**
   ```bash
   ssh ubuntu@VOTRE_IP_VPS
   ```
   - Remplacez `VOTRE_IP_VPS` par l'adresse IP de votre VPS
   - Entrez votre mot de passe quand demandé

### 2.3 Vérification de la connexion

Une fois connecté, vous devriez voir quelque chose comme :
```bash
Welcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-88-generic x86_64)
ubuntu@vps-123456:~$
```

---

## 3. Configuration de base du serveur

### 3.1 Mise à jour du système

```bash
# Mettre à jour la liste des paquets
sudo apt update

# Mettre à jour tous les paquets installés
sudo apt upgrade -y

# Redémarrer si nécessaire (vous serez déconnecté)
sudo reboot
```

⚠️ **Après le reboot, reconnectez-vous au VPS**

### 3.2 Installation des outils de base

```bash
# Installer les outils essentiels
sudo apt install -y \
    curl \
    wget \
    git \
    htop \
    nano \
    ufw \
    fail2ban \
    unzip \
    software-properties-common
```

### 3.3 Configuration du firewall

```bash
# Activer le firewall
sudo ufw enable

# Autoriser SSH (IMPORTANT pour ne pas perdre l'accès)
sudo ufw allow ssh

# Autoriser les connexions sortantes pour les mises à jour
sudo ufw allow out 80/tcp
sudo ufw allow out 443/tcp
sudo ufw allow out 53/udp

# Vérifier le statut
sudo ufw status
```

---

## 4. Installation de Python et des outils

### 4.1 Installation de Python 3

```bash
# Vérifier la version de Python installée
python3 --version

# Installer pip (gestionnaire de paquets Python)
sudo apt install python3-pip -y

# Mettre à jour pip
python3 -m pip install --upgrade pip

# Installer venv (environnements virtuels)
sudo apt install python3-venv -y
```

### 4.2 Vérification de l'installation

```bash
# Vérifier Python
python3 --version
# Doit afficher : Python 3.10.x ou plus récent

# Vérifier pip
pip3 --version
# Doit afficher : pip 23.x.x ou plus récent
```

---

## 5. Création de l'utilisateur dédié

### 5.1 Créer l'utilisateur bitsniper

```bash
# Créer un utilisateur dédié pour le bot
sudo useradd -m -s /bin/bash bitsniper

# Ajouter l'utilisateur au groupe sudo (pour les commandes admin)
sudo usermod -aG sudo bitsniper

# Définir un mot de passe pour bitsniper
sudo passwd bitsniper
# Entrez un mot de passe sécurisé quand demandé
```

### 5.2 Passer à l'utilisateur bitsniper

```bash
# Changer d'utilisateur
sudo su - bitsniper

# Vérifier que vous êtes bien bitsniper
whoami
# Doit afficher : bitsniper

# Vérifier le répertoire
pwd
# Doit afficher : /home/bitsniper
```

---

## 6. Installation de BitSniper

### 6.1 Cloner le repository

```bash
# Cloner le projet BitSniper
git clone https://github.com/VOTRE_USERNAME/Bit_Sniper_Kraken.git

# Aller dans le dossier du projet
cd Bit_Sniper_Kraken

# Vérifier le contenu
ls -la
```

### 6.2 Créer l'environnement virtuel

```bash
# Créer un environnement virtuel Python
python3 -m venv venv

# Activer l'environnement virtuel
source venv/bin/activate

# Vérifier que l'environnement est activé
which python
# Doit afficher : /home/bitsniper/Bit_Sniper_Kraken/venv/bin/python
```

### 6.3 Installer les dépendances

```bash
# Installer les paquets requis
pip install -r requirements.txt

# Vérifier l'installation
pip list
```

---

## 7. Configuration des clés API Kraken

### 7.1 Créer les clés API sur Kraken

1. **Aller sur Kraken.com**
   - Connectez-vous à votre compte Kraken
   - Allez dans "Sécurité" → "Clés API"

2. **Créer une nouvelle clé**
   - Cliquez sur "Ajouter une clé API"
   - **Nom** : BitSniper-Bot
   - **Permissions** :
     - ✅ Lire les informations du compte
     - ✅ Lire les positions ouvertes
     - ✅ Lire les ordres
     - ✅ Créer et modifier des ordres
     - ✅ Lire les données de marché
   - **Adresses IP autorisées** : Laissez vide (ou ajoutez l'IP de votre VPS)

3. **Récupérer les clés**
   - **Clé API** : Copiez cette longue chaîne de caractères
   - **Clé secrète** : Copiez cette autre longue chaîne de caractères

⚠️ **IMPORTANT** : Gardez ces clés précieusement et ne les partagez jamais !

### 7.2 Configurer les variables d'environnement

```bash
# Revenir à l'utilisateur root pour configurer systemd
exit
# Vous êtes maintenant root

# Créer le fichier de service systemd
sudo nano /etc/systemd/system/bitsniper.service
```

### 7.3 Contenu du fichier systemd

Copiez exactement ce contenu dans le fichier :

```ini
[Unit]
Description=BitSniper Trading Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=bitsniper
Group=bitsniper
WorkingDirectory=/home/bitsniper/Bit_Sniper_Kraken
ExecStart=/home/bitsniper/Bit_Sniper_Kraken/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Variables d'environnement sécurisées
Environment=KRAKEN_API_KEY=VOTRE_CLE_API_ICI
Environment=KRAKEN_API_SECRET=VOTRE_CLE_SECRETE_ICI

# Variables d'environnement système
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=/home/bitsniper/Bit_Sniper_Kraken

# Sécurité
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/bitsniper/Bit_Sniper_Kraken/logs /home/bitsniper/Bit_Sniper_Kraken/data

[Install]
WantedBy=multi-user.target
```

⚠️ **IMPORTANT** : Remplacez `VOTRE_CLE_API_ICI` et `VOTRE_CLE_SECRETE_ICI` par vos vraies clés !

### 7.4 Sauvegarder et quitter

Dans nano :
- Appuyez sur `Ctrl + X`
- Appuyez sur `Y` pour confirmer
- Appuyez sur `Entrée` pour sauvegarder

---

## 8. Test de la configuration

### 8.1 Créer le script de test

```bash
# Aller dans le dossier du projet
cd /home/bitsniper/Bit_Sniper_Kraken

# Créer le script de test
nano test_config.py
```

### 8.2 Contenu du script de test

Copiez exactement ce contenu :

```python
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
            
            # Test de récupération du compte
            account = client.get_account_summary()
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

def main():
    """Fonction principale de test"""
    
    print("🚀 TEST DE CONFIGURATION BITSNIPER")
    print("=" * 60)
    
    # Test des variables d'environnement
    env_ok = test_environment_variables()
    
    if not env_ok:
        print("\n❌ Configuration incomplète. Corrigez les variables d'environnement.")
        sys.exit(1)
    
    # Test de connexion Kraken
    kraken_ok = test_kraken_connection()
    
    if not kraken_ok:
        print("\n❌ Problème de connexion à Kraken. Vérifiez vos clés API.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ CONFIGURATION COMPLÈTE ET FONCTIONNELLE!")
    print("✅ Le bot est prêt à être lancé avec systemd.")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

### 8.3 Exécuter le test

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Exécuter le test
python test_config.py
```

Si tout fonctionne, vous devriez voir :
```
🚀 TEST DE CONFIGURATION BITSNIPER
============================================================
🔍 Vérification des variables d'environnement...
==================================================
✅ KRAKEN_API_KEY: KRAK****SECRET
✅ KRAKEN_API_SECRET: SECR****KEY
==================================================
✅ Toutes les variables d'environnement sont configurées correctement!

🔗 Test de connexion à Kraken Futures...
==================================================
✅ Connexion à Kraken Futures réussie!
✅ Récupération du compte réussie!
   Solde USD: $1000.00
   Prix BTC: $45000.00

============================================================
✅ CONFIGURATION COMPLÈTE ET FONCTIONNELLE!
✅ Le bot est prêt à être lancé avec systemd.
============================================================
```

---

## 9. Configuration du service systemd

### 9.1 Configurer les permissions

```bash
# Donner les bonnes permissions au dossier
sudo chown -R bitsniper:bitsniper /home/bitsniper/Bit_Sniper_Kraken
sudo chmod -R 750 /home/bitsniper/Bit_Sniper_Kraken

# Créer les dossiers nécessaires
sudo mkdir -p /home/bitsniper/Bit_Sniper_Kraken/logs
sudo mkdir -p /home/bitsniper/Bit_Sniper_Kraken/data
sudo chown -R bitsniper:bitsniper /home/bitsniper/Bit_Sniper_Kraken/logs
sudo chown -R bitsniper:bitsniper /home/bitsniper/Bit_Sniper_Kraken/data
sudo chmod 755 /home/bitsniper/Bit_Sniper_Kraken/logs
sudo chmod 755 /home/bitsniper/Bit_Sniper_Kraken/data
```

### 9.2 Activer le service

```bash
# Recharger les services systemd
sudo systemctl daemon-reload

# Activer le service (démarrage automatique au boot)
sudo systemctl enable bitsniper

# Vérifier que le service est bien configuré
sudo systemctl status bitsniper
```

---

## 10. Lancement et monitoring

### 10.1 Démarrer le bot

```bash
# Démarrer le service
sudo systemctl start bitsniper

# Vérifier le statut
sudo systemctl status bitsniper
```

### 10.2 Surveiller les logs

```bash
# Voir les logs en temps réel
sudo journalctl -u bitsniper -f

# Pour quitter la surveillance des logs : Ctrl+C
```

### 10.3 Vérifier que tout fonctionne

Vous devriez voir dans les logs quelque chose comme :
```
BitSniper - Bot de trading BTC/USD sur Kraken Futures
✅ Configuration chargée avec succès
✅ Connexion à Kraken Futures établie
📊 État du compte:
   Solde USD: $1000.00
   Prix BTC: $45000.00
   Taille max position: 0.0020 BTC ($90.00)
[Scheduler] Attente jusqu'à la prochaine clôture de bougie 15m
```

---

## 11. Sécurité et maintenance

### 11.1 Configuration du firewall avancé

```bash
# Installer fail2ban pour protéger contre les attaques
sudo apt install fail2ban -y

# Configurer fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Vérifier le statut
sudo systemctl status fail2ban
```

### 11.2 Mise à jour automatique

```bash
# Installer les mises à jour automatiques
sudo apt install unattended-upgrades -y

# Configurer les mises à jour automatiques
sudo dpkg-reconfigure -plow unattended-upgrades

# Vérifier la configuration
sudo unattended-upgrade --dry-run --debug
```

### 11.3 Script de sauvegarde

```bash
# Créer un script de sauvegarde
sudo nano /home/bitsniper/backup.sh
```

Contenu du script :
```bash
#!/bin/bash
# Script de sauvegarde quotidienne

BACKUP_DIR="/home/bitsniper/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Sauvegarder les logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /home/bitsniper/Bit_Sniper_Kraken/logs/

# Sauvegarder les données de monitoring
if [ -f /home/bitsniper/Bit_Sniper_Kraken/monitoring_data.json ]; then
    cp /home/bitsniper/Bit_Sniper_Kraken/monitoring_data.json $BACKUP_DIR/monitoring_$DATE.json
fi

# Nettoyer les anciennes sauvegardes (garder 7 jours)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.json" -mtime +7 -delete

echo "Sauvegarde terminée: $DATE"
```

```bash
# Rendre le script exécutable
sudo chmod +x /home/bitsniper/backup.sh

# Créer une tâche cron pour la sauvegarde automatique
sudo crontab -e

# Ajouter cette ligne pour une sauvegarde quotidienne à 2h du matin
0 2 * * * /home/bitsniper/backup.sh >> /home/bitsniper/backup.log 2>&1
```

---

## 12. Résolution des problèmes

### 12.1 Le service ne démarre pas

```bash
# Vérifier le statut détaillé
sudo systemctl status bitsniper -l

# Voir les logs d'erreur
sudo journalctl -u bitsniper -p err

# Vérifier les permissions
ls -la /home/bitsniper/Bit_Sniper_Kraken/
```

### 12.2 Variables d'environnement non trouvées

```bash
# Vérifier que les variables sont bien définies
sudo systemctl show bitsniper --property=Environment

# Recharger le service après modification
sudo systemctl daemon-reload
sudo systemctl restart bitsniper
```

### 12.3 Problèmes de connexion API

```bash
# Tester manuellement la connexion
cd /home/bitsniper/Bit_Sniper_Kraken
source venv/bin/activate
python test_config.py
```

### 12.4 Logs détaillés

```bash
# Voir tous les logs du service
sudo journalctl -u bitsniper --no-pager

# Voir les logs d'une période spécifique
sudo journalctl -u bitsniper --since "2024-01-01 00:00:00"

# Voir les logs en temps réel
sudo journalctl -u bitsniper -f
```

### 12.5 Redémarrer le bot

```bash
# Arrêter le bot
sudo systemctl stop bitsniper

# Redémarrer le bot
sudo systemctl restart bitsniper

# Vérifier le statut
sudo systemctl status bitsniper
```

---

## 🎉 Félicitations !

Votre bot BitSniper est maintenant installé et configuré sur votre VPS OVH ! 

### ✅ Ce qui est maintenant opérationnel :

1. **Bot de trading automatique** fonctionnant 24/7
2. **Redémarrage automatique** en cas de problème
3. **Logs centralisés** pour le monitoring
4. **Sauvegarde automatique** des données
5. **Sécurité renforcée** avec firewall et fail2ban
6. **Mises à jour automatiques** du système

### 📊 Monitoring quotidien recommandé :

```bash
# Vérifier le statut du service
sudo systemctl status bitsniper

# Voir les logs récents
sudo journalctl -u bitsniper --since "1 hour ago"

# Vérifier l'utilisation des ressources
htop
df -h
```

### 🔧 Maintenance mensuelle :

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Redémarrer le bot
sudo systemctl restart bitsniper

# Vérifier les sauvegardes
ls -la /home/bitsniper/backups/
```

**Votre bot est maintenant prêt à trader automatiquement sur Kraken Futures !** 🚀

---

## 📞 Support

Si vous rencontrez des problèmes :

1. **Vérifiez les logs** : `sudo journalctl -u bitsniper -f`
2. **Testez la configuration** : `python test_config.py`
3. **Vérifiez les permissions** : `ls -la /home/bitsniper/Bit_Sniper_Kraken/`
4. **Redémarrez le service** : `sudo systemctl restart bitsniper`

**N'oubliez pas** : Le trading comporte des risques. Surveillez régulièrement votre bot et vos positions !
