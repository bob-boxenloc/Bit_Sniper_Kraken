# BitSniper

Bot de trading automatique pour BTC/USD sur Kraken Futures, basé sur l'analyse technique pure avec gestion avancée des erreurs réseau.

## Fonctionnalités principales
- Analyse technique avancée (RSI, MACD, moyennes mobiles, etc.)
- Prise de position automatique sur Kraken Futures
- Stratégie de gestion du risque optimisée
- Gestion automatique des TP, SL, et clôture des positions
- **Gestion avancée des erreurs réseau** (retry, backoff, circuit breaker)
- **Monitoring système en temps réel** avec alertes
- **Robustesse 24/7** pour déploiement VPS
- Backend only, déployable sur VPS, persistance cloud

## Stratégie de trading

### Configuration générale
- **Timeframe** : Bougies de 15 minutes
- **Indicateurs** : RSI(12), Volume SMA (fourni par Kraken)
- **Position sizing** : Maximum possible (soit "MAX" soit calculé selon le portefeuille disponible)
- **Unité minimum** : 0.0001 BTC (≈ 10,74€ actuellement)
- **Décision** : Toutes les décisions (entrée, sortie, SL) sont basées sur le closing de la bougie précédente (N-1).
- **Exécution** : L'action (prise ou sortie de position) est réalisée au tout début de la bougie suivante (N), au prix d'ouverture de N.

### Précisions importantes
- **Volume SMA** : On utilise la valeur affichée par Kraken (ex : 55 sur le graphique), qui semble être en BTC. On prend ce chiffre tel quel, sans conversion.
- **Conditions d'entrée** : Toutes les conditions d'entrée listées pour chaque position doivent être réunies simultanément (logique ET stricte) pour autoriser une prise de position.

### Règles d'exécution
- **Timing** : Toutes les logiques (entrée, sortie, SL) sont basées sur les valeurs de clôture de la bougie N-1. L'action (prise ou sortie de position) est exécutée immédiatement après la clôture, au tout début de la bougie N (au prix d'ouverture de N).
- **Données utilisées** : Bougie N-1 (qui vient de se fermer) et Bougie N-2 (celle d'avant)
- **SL personnalisé** : Pas de SL Kraken, mais logique d'exit programmée quand position perdante

### Règle générale de sécurité

- **Blocage après extrême RSI** :
  - Si le RSI passe au-dessus de 86 ou en dessous de 10, il est interdit de prendre une position (long1, long2 ou short) tant que le RSI n'est pas repassé par 50 (même brièvement).

### Position "long1" (pari à la hausse)

#### Conditions d'entrée (au closing de Bougie N-1)
- **Pas de position en cours**
- **Volume** : Volume Bougie N-1 ≥ 90
- **Bougie N-2** : 26 ≥ RSI Bougie N-2 ≥ 10
- **Bougie N-1** : RSI Bougie N-1 - RSI Bougie N-2 ≥ 4
- **Bougie N-1** : RSI Bougie N-1 < 40 (ne pas ouvrir si le RSI est déjà supérieur ou égal à 40)

#### Conditions de sortie
- **Exit** : RSI dernière bougie clôturée ≥ 40
- **SL** : Si le cours de clôture de la dernière bougie clôturée a baissé d'au moins 0,7% par rapport au cours d'entrée (Bougie N-1), la position est clôturée.

### Position "long2" (pari à la hausse)

#### Conditions d'entrée (au closing de Bougie N-1)
- **Pas de position en cours**
- **Volume** : Volume Bougie N-1 ≥ 90
- **Volume** : Volume Bougie N-1 > Volume Bougie N-2
- **Delta Volume** : 1 < (Volume Bougie N-1 / Volume Bougie N-2) ≤ 1,8
- **Bougie N-2** : 72 ≤ RSI Bougie N-2 ≤ 86
- **Bougie N-1** : RSI Bougie N-2 - RSI Bougie N-1 ≥ 2,5 (baisse du RSI)

#### Conditions de sortie
- **Enregistrer** le RSI de la Bougie N-1 à l'entrée
- **Exit** : RSI dernière bougie clôturée ≥ (RSI Bougie N-1 + 1,5)
- **SL** : Si le cours de clôture de la dernière bougie clôturée a baissé d'au moins 1,1% par rapport au cours d'entrée (Bougie N-1), la position est clôturée.

#### Règle supplémentaire
- **Ne jamais enchaîner 2 positions "long2" d'affilée** si le RSI n'est pas repassé sous 50 entre les deux (même brièvement).

### Position "short" (pari à la baisse)

#### Conditions d'entrée (au closing de Bougie N-1)
- **Pas de position en cours**
- **Volume** : Volume Bougie N-1 ≥ 90
- **Volume** : Volume Bougie N-1 < Volume Bougie N-2
- **Delta Volume** : 0,7 ≤ (Volume Bougie N-1 / Volume Bougie N-2) < 1
- **Bougie N-2** : 72 ≤ RSI Bougie N-2 ≤ 83
- **Bougie N-1** : RSI Bougie N-2 - RSI Bougie N-1 ≥ 3,5 (baisse du RSI)
- **Bougie N-1** : RSI Bougie N-1 > 60 (ne pas ouvrir si le RSI est déjà inférieur ou égal à 60)

#### Conditions de sortie
- **Exit** : RSI dernière bougie clôturée ≤ 60
- **SL** : Si le cours de clôture de la dernière bougie clôturée est monté d'au moins 0,8% par rapport au cours d'entrée (Bougie N-1), la position est clôturée.

## Workflow métier
1. **Analyse et décision** :
    - Vérifier l'état de la position précédente
    - Analyser les indicateurs techniques actuels
    - Prendre une décision de trading basée sur l'analyse technique
    - Gérer les positions selon la stratégie définie
2. **Gestion des positions** :
    - Ouverture de nouvelles positions selon les signaux
    - Gestion des TP/SL automatiques
    - Clôture des positions selon la stratégie

## Arborescence du projet (proposée)

```
bit_sniper/
│   README.md
│   requirements.txt
│   config.py
│
├── core/
│   ├── __init__.py
│   ├── scheduler.py           # Orchestration des tâches
│   ├── state_manager.py       # Gestion de l'état et de la persistance
│   ├── logger.py              # Logging et reporting
│   ├── error_handler.py       # Gestion avancée des erreurs réseau
│   └── monitor.py             # Monitoring système et alertes
│
├── data/
│   ├── __init__.py
│   ├── market_data.py         # Récupération des données de marché
│   └── indicators.py          # Calcul des indicateurs techniques
│
├── signals/
│   ├── __init__.py
│   ├── technical_analysis.py  # Analyse technique complète
│   ├── aggregation.py         # Agrégation des signaux techniques
│   └── decision.py            # Prise de décision (long/short)
│
├── trading/
│   ├── __init__.py
│   ├── kraken_client.py       # Connexion à l'API Kraken Futures
│   ├── trade_manager.py       # Ouverture, gestion, clôture des positions
│   └── risk_manager.py        # Gestion du risque et position sizing
│
└── tests/
    ├── test_error_handling.py  # Tests de gestion d'erreurs
    └── ...                    # Tests unitaires et d'intégration
```

## Configuration
- Les clés API Kraken et les paramètres sensibles sont à stocker dans les variables d'environnement.
- Les paramètres de trading, TP/SL, etc. sont à définir dans `config.py`.

## Gestion avancée des erreurs réseau

### Fonctionnalités implémentées
- **Retry automatique** avec backoff exponentiel
- **Circuit breaker** pour éviter les surcharges
- **Timeout configurable** pour chaque requête
- **Monitoring en temps réel** de la santé du système
- **Système d'alertes** intelligent
- **Sauvegarde automatique** des données de monitoring

### Configuration des erreurs
```python
# Exemple d'utilisation du décorateur de retry
@handle_network_errors(
    max_retries=3,        # Nombre maximum de tentatives
    base_delay=1.0,       # Délai de base en secondes
    max_delay=60.0,       # Délai maximum en secondes
    timeout=30.0,         # Timeout par tentative
    jitter=True           # Ajouter du jitter pour éviter les thundering herds
)
def api_call():
    # Votre appel API ici
    pass
```

### Monitoring système
Le bot surveille automatiquement :
- **Erreurs réseau** et leur fréquence
- **Utilisation des ressources** (CPU, mémoire)
- **Performance du trading** (win rate, PnL)
- **État du circuit breaker**
- **Uptime du système**

### Alertes automatiques
Le système déclenche des alertes pour :
- Plus de 10 erreurs consécutives
- Circuit breaker ouvert
- Utilisation mémoire > 1GB
- Utilisation CPU > 90%
- Aucun succès depuis plus d'1 heure

## Déploiement

### Hébergement VPS recommandé
Le bot nécessite un VPS pour une exécution continue et fiable. **À évaluer selon les besoins en RAM** :

#### Options recommandées :
- **OVH VPS SSD 1** : 3,50€/mois - 2 GB RAM - 1 vCore - 20 GB SSD
- **Hostinger VPS** : 3,95€/mois - 1 GB RAM - 1 vCore - 20 GB SSD (interface user-friendly)
- **Scaleway Stardust** : 3,99€/mois - 1 GB RAM - 1 vCore ARM - 10 GB SSD

#### Critères de choix :
- **RAM minimale** : À déterminer selon la complexité du bot
- **Fiabilité** : OVH recommandé pour les applications critiques
- **Interface** : Hostinger plus user-friendly
- **Performance** : OVH et Scaleway plus performants

**Note** : Le choix final sera fait après développement, en fonction des besoins réels en ressources.

### Configuration VPS
- Ubuntu 22.04 LTS
- Python 3.9+
- Base de données SQLite (intégrée) ou MongoDB/Supabase
- Processus continu avec systemd ou PM2
- **Variables d'environnement** pour les clés API (plus sécurisé que .env)

### Installation et test
```bash
# Installation des dépendances
pip install -r requirements.txt

# Test de la configuration des variables d'environnement
python test_config.py

# Test de la gestion d'erreurs
python tests/test_error_handling.py

# Démonstration des fonctionnalités
python demo_error_handling.py

# Lancement du bot
python main.py
```

### 🚀 Installation complète sur VPS
Pour une installation complète et sécurisée sur VPS avec gestion automatique des variables d'environnement, consultez le guide détaillé :

**[📖 Guide d'installation VPS complet](INSTALL_VPS.md)**

Ce guide inclut :
- Configuration sécurisée des variables d'environnement via systemd
- Création d'un utilisateur dédié
- Service systemd avec redémarrage automatique
- Scripts de sauvegarde et monitoring
- Résolution des problèmes courants

## Intégration Kraken Futures API

- [Documentation officielle Kraken Futures REST](https://docs.kraken.com/api/docs/guides/futures-rest/)
- [Documentation SDK Python Kraken](https://python-kraken-sdk.readthedocs.io/en/v2.0.0/src/futures/rest.html)

### Endpoints et fonctionnalités clés

- **Récupération des bougies (OHLCV)**
  - Endpoint : `/charts/:tick_type/:symbol/:resolution` (REST)
  - Résolutions disponibles : 1m, 5m, 15m, 1h, 4h, etc. (15m OK)
  - Volume fourni dans chaque bougie (en BTC pour XBTUSD)
  - Utiliser `tick_type=trade` pour le volume réel
  - Exemple (SDK Python) :
    ```python
    market.get_ohlc(tick_type="trade", symbol="PI_XBTUSD", resolution="15m")
    ```

- **Passage d'ordres**
  - Endpoint : `/sendorder` ou SDK `Trade.create_order()`
  - Types d'ordres : `mkt` (market), `lmt` (limit), etc.
  - Taille minimale : 0.0001 BTC (à confirmer avec `get_instruments()`)
  - Calcul du "MAX" : récupérer le solde avec `get_wallets()` et calculer la taille max selon la marge requise
  - Exemple (SDK Python) :
    ```python
    trade.create_order(orderType="mkt", size=0.0001, side="buy", symbol="PI_XBTUSD")
    ```

- **Gestion des positions**
  - Endpoint : `/get_open_positions` ou SDK `Trade.get_open_positions()`
  - Infos récupérables : sens (long/short), taille, prix d'entrée, PnL
  - Clôture : passer un ordre opposé de même taille ou utiliser `reduceOnly`
  - Exemple :
    ```python
    trade.get_open_positions()
    ```

- **Gestion du portefeuille**
  - Endpoint : `/get_wallets` ou SDK `User.get_wallets()`
  - Permet de récupérer le solde disponible pour calculer le sizing

- **SL/TP programmés côté bot**
  - Surveillance continue de la position via l'API
  - Déclenchement d'un ordre de clôture si la condition de SL/TP est atteinte
  - Pas d'utilisation des SL/TP natifs Kraken (logique gérée dans le bot)

- **Granularité et historique**
  - Profondeur historique paramétrable via `from` et `to` (epoch)
  - Résolutions supportées : 1m, 5m, 15m, etc.

- **Limitations**
  - Rate limits à respecter (mais suffisant pour une exécution toutes les 15 min)
  - Latence faible, mais prévoir gestion des erreurs réseau

### Points d'attention pour la stratégie
- **Bougies 15m** : bien utiliser la résolution 15m pour toutes les analyses
- **Volume** : utiliser le champ `volume` de la bougie (en BTC)
- **Sizing MAX** : calculer la taille max possible avant chaque prise de position (prendre en compte la marge, les frais, etc.)
- **SL/TP** : surveiller la position en continu et déclencher la sortie selon la logique du bot
- **Pas de SL natif** : toute la gestion du risque est programmée côté bot
- **Gestion du portefeuille** : toujours vérifier le solde avant de prendre position

## Mode opératoire : installation et lancement du bot

### 1. Pré-requis
- Un VPS (ex : OVH VPS SSD 1 recommandé)
- Ubuntu 22.04 LTS (ou équivalent Linux)
- Python 3.9+ installé (`python3 --version`)
- Accès SSH au VPS
- Clés API Kraken Futures (avec droits trading et lecture portefeuille)

### 2. Installation des dépendances
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip git -y
# (optionnel) Installer virtualenv pour isoler l'environnement Python
pip3 install virtualenv
virtualenv venv
source venv/bin/activate
```

### 3. Récupération du code
```bash
git clone <URL_DU_REPO_GITHUB>
cd bitsniper
pip install -r requirements.txt
```

### 4. Configuration
- Copier le fichier d'exemple `config.example.py` en `config.py` (ou créer `config.py` si absent)
- Renseigner les paramètres de trading, seuils, etc. dans `config.py`
- Exporter les variables d'environnement pour les clés API Kraken :
```bash
export KRAKEN_API_KEY="votre_api_key"
export KRAKEN_API_SECRET="votre_api_secret"
```
- (Optionnel) Ajouter ces lignes à votre `.bashrc` ou `.profile` pour automatiser à chaque connexion

### 5. Lancement manuel du bot
```bash
python main.py
```

### 6. Lancement automatique (service)
- Utiliser `systemd` pour lancer le bot en tâche de fond et le relancer automatiquement en cas de crash.
- Exemple de fichier de service systemd (`/etc/systemd/system/bitsniper.service`) :
```
[Unit]
Description=BitSniper Trading Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/chemin/vers/bitsniper
ExecStart=/chemin/vers/bitsniper/venv/bin/python main.py
Restart=always
Environment=KRAKEN_API_KEY=xxx
Environment=KRAKEN_API_SECRET=yyy

[Install]
WantedBy=multi-user.target
```
- Activer et démarrer le service :
```bash
sudo systemctl daemon-reload
sudo systemctl enable bitsniper
sudo systemctl start bitsniper
```

### 7. Conseils de sécurité
- Ne jamais partager vos clés API Kraken
- Utiliser un utilisateur Linux dédié (pas root)
- Mettre à jour régulièrement le système et les dépendances Python
- Sauvegarder régulièrement la base de données et les logs

---

## À venir
- Définition des positions "long2" et "long3"
- Implémentation des modules
- Documentation détaillée de chaque module 

### Sizing maximal et gestion du levier

- Le bot utilise le levier maximal autorisé par Kraken Futures (x10 pour le contrat BTC Perp).
- La taille maximale de la position est donc :
  **taille_max = marge_disponible × 10**
- Le bot utilise toujours le maximum de marge disponible pour ouvrir une position, car les exits d'urgence (stop loss programmés à -0.7 %, -0.8 % et -1.1 %) sont bien avant le niveau de liquidation. Il n'y a donc pas de risque de margin call dans la pratique.
- Exemple : si la marge disponible est de 20 $, la taille max de la position sera 200 $. 