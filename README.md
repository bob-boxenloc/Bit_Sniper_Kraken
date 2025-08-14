# BitSniper

Bot de trading automatique pour BTC/USD sur Kraken Futures, basé sur l'analyse technique avec RSI et Volatility Indexes avec gestion avancée des erreurs réseau.

## Fonctionnalités principales
- Analyse technique avancée (RSI 40, 3 Volatility Indexes Wilder)
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
- **Indicateurs** : RSI(40), 3 Volatility Indexes Wilder
- **Position sizing** : Maximum possible (soit "MAX" soit calculé selon le portefeuille disponible)
- **Unité minimum** : 0.0001 BTC (≈ 10,74€ actuellement)
- **Décision** : Toutes les décisions (entrée, sortie, SL) sont basées sur le closing de la bougie précédente (N-1).
- **Exécution** : L'action (prise ou sortie de position) est réalisée au tout début de la bougie suivante (N), au prix d'ouverture de N.

### Indicateurs techniques

#### RSI(40)
- **Période** : 40
- **Utilisation** : Conditions d'entrée et calcul des exits
- **Conditions d'entrée** :
  - **LONGS** : RSI ≥ 45
  - **SHORTS** : RSI ≤ 50

#### Volatility Indexes (3)
- **Période** : 28 pour tous
- **Méthode** : Wilder Smoothing
- **Multiplicateurs ATR** :
  - **VI1** : ATR Mult 19
  - **VI2** : ATR Mult 10
  - **VI3** : ATR Mult 6

#### Règle de protection temporelle VI1
- **Délai minimum** : 72 heures minimum entre deux changements de phase VI1 - close
- **Logique** : Éviter les faux signaux trop rapprochés
- **Application** : Interdiction des positions inverses pendant 72h
- **Phase "SHORT"** (VI1 au-dessus du close) : Interdire tous les LONGS
- **Phase "LONG"** (VI1 en-dessous du close) : Interdire SHORT

### Types de positions

#### SHORT
**Conditions d'entrée** :
- VI1 passe **au-dessus** du prix de clôture
- VI2 et VI3 déjà **au-dessus** du prix de clôture
- RSI ≤ 50

**Conditions de sortie** :
- **Exit principal** : Basé sur la différence RSI (entrée vs sortie)
  - RSI entrée 45-50 : -10
  - RSI entrée 40-45 : -7.5
  - RSI entrée 35-40 : -3.5
  - RSI entrée 30-35 : -1.75
  - RSI entrée < 30 : -1
- **Exit de dernier recours** : VI1 repasse en-dessous du prix de clôture

#### LONG_VI1
**Conditions d'entrée** :
- VI1 passe **en-dessous** du prix de clôture
- VI2 et VI3 déjà **en-dessous** du prix de clôture
- RSI ≥ 45

**Conditions de sortie** :
- **Exit principal** : Basé sur la différence RSI (entrée vs sortie)
  - RSI entrée 45-50 : +20
  - RSI entrée 50-55 : +15
  - RSI entrée 55-60 : +9
  - RSI entrée 60-65 : +4.5
  - RSI entrée 65-70 : +3
  - RSI entrée > 70 : +1
- **Exit de dernier recours** : VI1 repasse au-dessus du prix de clôture

#### LONG_VI2
**Conditions d'entrée** :
- VI1 déjà **en-dessous** du prix de clôture
- VI2 et/ou VI3 étaient au-dessus, puis passent **en-dessous**
- **Déclencheur** : VI2 crossing-under (jamais VI1)
- RSI ≥ 45

**Conditions de sortie** :
- **Exit principal** : Basé sur la différence RSI (entrée vs sortie)
  - RSI entrée 45-50 : +9
  - RSI entrée 50-55 : +6.5
  - RSI entrée 55-60 : +3.5
  - RSI entrée 60-65 : +1.25
  - RSI entrée 65-70 : +0.5
  - RSI entrée > 70 : +0.5
- **Exit de dernier recours** : VI1 repasse au-dessus du prix de clôture

#### LONG_REENTRY
**Conditions d'entrée** :
- Après sortie d'une position LONG
- VI1 pas encore repassé au-dessus du prix de clôture
- VI3 sous le prix de clôture
- VI2 au-dessus du prix de clôture
- **Déclencheur** : VI2 crossing-under
- RSI ≥ 45
- **Protection** : Pas de LONG_REENTRY consécutif (interdit après exit d'un LONG_REENTRY)
- **Ré-autorisation** : Après prise d'un autre type de position (LONG_VI1, LONG_VI2, SHORT)

**Conditions de sortie** :
- **Exit principal** : Basé sur la différence RSI (entrée vs sortie)
  - RSI entrée 45-50 : +18
  - RSI entrée 50-55 : +13
  - RSI entrée 55-60 : +7
  - RSI entrée 60-65 : +2.5
  - RSI entrée 65-70 : +1
  - RSI entrée > 70 : +1
- **Exit de dernier recours** : VI1 repasse au-dessus du prix de clôture

### Règles d'exécution
- **Timing** : Toutes les logiques (entrée, sortie, SL) sont basées sur les valeurs de clôture de la bougie N-1. L'action (prise ou sortie de position) est exécutée immédiatement après la clôture, au tout début de la bougie N (au prix d'ouverture de N).
- **Données utilisées** : Bougie N-1 (qui vient de se fermer) et Bougie N-2 (celle d'avant)
- **Enregistrement** : RSI d'entrée doit être enregistré pour calculer les exits

### Règles de protection et gestion du risque

#### Protection temporelle générale
- **Délai minimum** : Aucun exit autorisé pendant les 7 premières heures après l'entrée en position
- **Conservation** : Le RSI de sortie attendu est conservé et appliqué après les 7 heures
- **Exception LONG_VI2** : Aucun délai de 7 heures, sortie immédiate si RSI de sortie atteint

#### Règles spéciales pour SHORTS

**Contrôle à 3 heures** :
- **Timing** : 3 heures après l'entrée (depuis la bougie d'entrée)
- **Calcul** : Écart = (Close actuel - Close entrée) / Close entrée
- **Condition de sortie** : Si écart ≥ 1%, sortie immédiate
- **Logique** : Si le RSI monte de 1% en 3h, c'est généralement mauvais signe

**Emergency exit** :
- **Condition** : RSI monté de plus de 18 points (après les délais de 3h et 7h)
- **Action** : Sortie immédiate de la position
- **Logique** : Protection contre les mouvements défavorables majeurs

#### Règles pour LONGS
- **Aucun stop loss** : Basé sur l'historique des 9 derniers mois (seulement 3 erreurs)
- **Logique** : Éviter de passer à côté de gros upsides

#### Gestion des transitions de positions
- **Sortie de dernier recours** : Si RSI de sortie non atteint, sortie quand VI1 change de côté
- **Transition immédiate** : Si les conditions d'entrée pour la position inverse sont réunies au moment de la sortie de dernier recours, prise immédiate de la nouvelle position
- **Logique** : Éviter de rester en cash quand une opportunité se présente

#### Suivi des positions pour règles de protection
- **Variable d'état** : `last_position_type` (None, "SHORT", "LONG_VI1", "LONG_VI2", "LONG_REENTRY")
- **Mise à jour** : À chaque exit de position
- **Utilisation** : Vérification des règles de protection (LONG_REENTRY consécutif, etc.)
- **Stockage** : Dans le state_manager pour persistance

### Règle générale de sécurité

- **Blocage après extrême RSI** :
  - Si le RSI passe au-dessus de 86 ou en dessous de 10, il est interdit de prendre une position (long1, long2 ou short) tant que le RSI n'est pas repassé par 50 (même brièvement).

### Position "long1" (pari à la hausse)

#### Conditions d'entrée (au closing de Bougie N-1)
- **Pas de position en cours**
- **Volume** : Volume Bougie N-1 ≥ 90
- **Ratio Volume** : 0,3 ≤ (Volume Bougie N-1 / Volume Bougie N-2) ≤ 1,8
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
- **Ratio Volume** : (Volume Bougie N-1 / Volume Bougie N-2) > 1
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
- **Ratio Volume** : 0,7 ≤ (Volume Bougie N-1 / Volume Bougie N-2) < 1
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

## 🔄 PROCÉDURE DE MISE À JOUR DES VI

**⚠️ ATTENTION :** Cette procédure est **OBLIGATOIRE** chaque fois que vous modifiez les valeurs ou états des Volatility Indexes !

### Pourquoi cette procédure ?
Le bot utilise des fichiers de cache Python (`__pycache__`) pour aller plus vite. **Sans cette procédure**, le bot continuera d'utiliser les anciennes valeurs même après modification du code !

### 📍 LISTE EXACTE DES ENDROITS À MODIFIER

**⚠️ ATTENTION : Vous DEVEZ modifier TOUS ces endroits pour éviter les erreurs !**

#### **main.py (4 endroits)**
```python
# Ligne 102-104 : Initialisation des phases VI
vi1_n1 = 117298  # BULLISH
vi2_n1 = 120957  # BEARISH
vi3_n1 = 118685  # BULLISH

# Ligne 109 : Phases VI hardcodées
'VI3_phases': ['BEARISH'],  # ⚠️ CRITIQUE : Éviter les erreurs d'état !

# Ligne 147 : Print d'affichage
print(f"   VI3: {vi3_n1:.2f} (BEARISH) - VALEUR DE DÉPART UTILISATEUR")

# Ligne 261-263 : Valeurs de départ utilisateur
vi1_n1 = 117298  # Valeur de départ fournie par l'utilisateur
vi2_n1 = 120957  # Valeur de départ fournie par l'utilisateur
vi3_n1 = 118685  # Valeur de départ fournie par l'utilisateur

# Ligne 273 : Valeur par défaut previous_vi3_state
previous_vi3_state = indicator_history.get('vi3_state', "BEARISH")
```

#### **data/indicators.py (4 endroits)**
```python
# Ligne 479-481 : Fonction initialize_vi_history_from_user_values
vi1_n1 = 117298  # BULLISH
vi2_n1 = 120957  # BEARISH
vi3_n1 = 118685  # BULLISH

# Ligne 485-487 : États initiaux
vi1_state = "BULLISH"
vi2_state = "BEARISH"
vi3_state = "BEARISH"

# Ligne 845-847 : Fonction calculate_volatility_indexes_corrected
vi1_n1 = 117298  # BULLISH
vi2_n1 = 120957  # BEARISH
vi3_n1 = 118685  # BULLISH

# Ligne 851-853 : États initiaux (utilisés seulement si pas d'états précédents)
vi1_state_initial = "BULLISH"
vi2_state_initial = "BEARISH"
vi3_state_initial = "BEARISH"
```

**⚠️ TOTAL : 8 endroits à modifier (pas 6 !)**

### 🚨 AVERTISSEMENTS CRITIQUES

#### **1. ÉVITER LES ERREURS D'ÉTATS :**
- **VI1** : Toujours BULLISH (en-dessous du close)
- **VI2** : Toujours BEARISH (au-dessus du close)  
- **VI3** : Toujours BEARISH (au-dessus du close)

#### **2. VÉRIFIER LES HARCODÉS :**
- **Ligne 109** : `'VI3_phases': ['BEARISH']` (pas BULLISH !)
- **Ligne 147** : Print avec le bon état (BEARISH pour VI3)
- **Ligne 273** : Valeur par défaut BEARISH pour VI3

#### **3. ERREURS FRÉQUENTES À ÉVITER :**
- ❌ Oublier les hardcodés dans main.py
- ❌ Mélanger BULLISH/BEARISH selon les valeurs
- ❌ Oublier les valeurs par défaut et phases
- ❌ Se contenter de modifier seulement les valeurs numériques

**💡 CONSEIL : Utilisez la commande grep pour vérifier TOUS les endroits !**

###  PROCÉDURE COMPLÈTE (5 minutes)

#### 1️⃣ Mise à jour du code local
```bash
# Modifier TOUS les endroits listés ci-dessus
# Vérifier que les états correspondent :
# - VI1 : BULLISH (en-dessous du close)
# - VI2 : BEARISH (au-dessus du close)  
# - VI3 : BULLISH (en-dessous du close)
```

#### 2️⃣ Vérification locale COMPLÈTE
```bash
# Vérifier que TOUTES les anciennes valeurs ont été remplacées
grep -r "116196\|121537\|120234" .                    # Aucun résultat = OK
grep -r "117498\|121107\|120078" .                    # Aucun résultat = OK

# Vérifier que les nouvelles valeurs sont partout
grep -r "117298\|120957\|118685" .                    # 8 résultats = OK
grep -r "vi1_n1.*=.*117298" .                        # 4 résultats = OK
grep -r "vi2_n1.*=.*120957" .                        # 4 résultats = OK  
grep -r "vi3_n1.*=.*118685" .                        # 4 résultats = OK

# ⚠️ VÉRIFICATION CRITIQUE DES HARCODÉS ET ÉTATS
grep -r "VI3.*BULLISH" .                              # Aucun résultat = OK (sauf dans README)
grep -r "vi3_state.*BULLISH" .                        # Aucun résultat = OK
grep -r "vi3_phase.*BULLISH" .                        # Aucun résultat = OK
grep -r "VI3_phases.*BULLISH" .                       # Aucun résultat = OK

# Vérifier que les états sont corrects
grep -r "vi1_state.*=.*BULLISH" .                     # 2 résultats = OK
grep -r "vi2_state.*=.*BEARISH" .                     # 2 résultats = OK
grep -r "vi3_state.*=.*BEARISH" .                     # 2 résultats = OK
```

#### 3️⃣ Envoi sur le serveur
```bash
git add .
git commit -m "Mise à jour VI: VI1=117298(BULLISH), VI2=120957(BEARISH), VI3=118685(BULLISH)"
git push
```

#### 4️⃣ Nettoyage et mise à jour sur le serveur
```bash
# Se connecter au serveur
ssh bitsniper@149.202.40.139
cd Bit_Sniper_Kraken
source venv/bin/activate

# NETTOYAGE COMPLET DU CACHE PYTHON (OBLIGATOIRE !)
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Récupérer les changements
git pull
```

#### 5️⃣ Redémarrage du bot
```bash
sudo systemctl restart bitsniper
sudo systemctl status bitsniper
sudo journalctl -u bitsniper -f
```

### 🎯 VÉRIFICATIONS FINALES COMPLÈTES

#### **Vérification 1 : Logs du bot**
Dans les logs, vous devez voir :
```
VI1: 117298 (BULLISH) - VALEUR DE DÉPART UTILISATEUR
VI2: 120957 (BEARISH) - VALEUR DE DÉPART UTILISATEUR  
VI3: 118685 (BULLISH) - VALEUR DE DÉPART UTILISATEUR
```

#### **Vérification 2 : Code source sur le serveur**
```bash
# Vérifier que le serveur a les bonnes valeurs
grep -n "vi1_n1.*=" main.py data/indicators.py
grep -n "vi2_n1.*=" main.py data/indicators.py  
grep -n "vi3_n1.*=" main.py data/indicators.py

# Résultat attendu : 4 lignes pour chaque VI avec les bonnes valeurs
```

#### **Vérification 3 : Cache Python supprimé**
```bash
# Vérifier qu'il n'y a plus de cache
find . -name "*.pyc" | wc -l                    # Résultat = 0
find . -name "__pycache__" | wc -l              # Résultat = 0
```

### ❌ SIGNAUX D'ALERTE
**Si vous voyez :**
- D'autres valeurs que `117298`, `120957`, `118685` → **Procédure incomplète !**
- Messages d'erreur Git → **Cache Python non supprimé !**
- Anciennes valeurs dans les logs → **Redémarrage manqué !**

### 🔧 EN CAS DE PROBLÈME
```bash
# Nettoyage d'urgence
sudo systemctl stop bitsniper
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
git reset --hard HEAD
git pull
sudo systemctl start bitsniper
```

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