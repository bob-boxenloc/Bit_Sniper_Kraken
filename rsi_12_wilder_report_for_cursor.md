# Rapport technique correctif – Calcul RSI 12 (méthode Wilder)

*Destinataire : équipe de développement/IA Cursor* *Version : 1.0  •  Date : 8 juillet 2025*

---

## 1. Constat

- Les valeurs d’indicateur récupérées sur Kraken pour **RSI *****Length***** = 12** ne correspondaient pas aux résultats produits par notre code interne.
- Après vérification, Kraken affiche par défaut le **RSI standard de J. Welles Wilder (1978)**.
- Le code existant utilisait une **moyenne glissante simple (SMA)** pour les gains/pertes au lieu du lissage “Wilder” (équivalent d’une EMA particulière).

## 2. Origine de l’écart

| Étape                                      | Code avant correction                    | Comportement Kraken                                  | Conséquence                                    |
| ------------------------------------------ | ---------------------------------------- | ---------------------------------------------------- | ---------------------------------------------- |
| Moyenne des gains/pertes                   | `SMA(window=12)`                         | Wilder smoothing (voir § 3)                          | RSI trop nerveux ; dérive de plusieurs points. |
| Courbe « Smoothing line » (SMA 14 sur RSI) | Calculée mais confondue avec le RSI brut | Affichée uniquement si l’option *Show MA* est cochée | Double affichage/lecture erronée.              |

## 3. Spécifications fonctionnelles cibles

1. **RSI Period** : 12 bougies.
2. **Méthode de lissage** : Wilder (algorithme original ⇒ lissage exponentiel discret).
3. **Sorties** :
   - `rsi_12` : courbe RSI brute (match Kraken par défaut).
   - `rsi_12_sma14` (optionnel) : SMA 14 appliquée à `rsi_12` et affichée seulement si explicitement demandée.
4. **Aucune autre moyenne supplémentaire** par défaut.

## 4. Algorithme détaillé (formules)

Soit **n = 12**.

### 4.1 Variables intermédiaires

- `Δₜ = closeₜ − closeₜ₋₁`
- `gainₜ   = max(Δₜ, 0)`
- `lossₜ   = max(−Δₜ, 0)`

### 4.2 Première moyenne (initialisation)

```text
avgGainₙ = Σ(gain₁…ₙ) / n
avgLossₙ = Σ(loss₁…ₙ) / n
```

### 4.3 Lissage récursif de Wilder pour t > n

```text
avgGainₜ = (avgGainₜ₋₁ × (n − 1) + gainₜ) / n
avgLossₜ = (avgLossₜ₋₁ × (n − 1) + lossₜ) / n
```

### 4.4 Calcul du RSI

```text
RSₜ  = avgGainₜ / avgLossₜ
RSIₜ = 100 − 100 / (1 + RSₜ)
```

### 4.5 (Optionnel) ligne de lissage SMA 14

```text
RSI_SMA14ₜ = SMA₁₄(RSI)ₜ
```

## 5. Implémentation Python de référence

```python
import pandas as pd

# --- RSI 12 façon Wilder ----------------------------------------------------

def rsi_wilder(close: pd.Series, length: int = 12) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)

    avg_gain = gain.rolling(length).mean()
    avg_loss = loss.rolling(length).mean()

    for i in range(length, len(close)):
        if i == length:
            continue  # la première valeur est déjà la SMA initiale
        avg_gain.iat[i] = (avg_gain.iat[i-1]*(length-1) + gain.iat[i]) / length
        avg_loss.iat[i] = (avg_loss.iat[i-1]*(length-1) + loss.iat[i]) / length

    rs  = avg_gain / avg_loss
    return 100 - 100/(1 + rs)

# --- Smoothing line SMA 14 (facultatif) ------------------------------------

def rsi_signal(close: pd.Series, length_rsi: int = 12, length_ma: int = 14):
    rsi = rsi_wilder(close, length_rsi)
    return rsi.rolling(length_ma).mean()
```

## 6. Jeu de test minimal

Données : 63 cours de clôture (voir tableau en **Annexe A**).

| Index | Close   | RSI 12 attendu |
| ----- | ------- | -------------- |
| 12    | 107 977 | **46 .9887**   |
| 13    | 107 813 | 42 .4590       |
| …     | …       | …              |
| 62    | 108 508 | **64 .4649**   |

Vérification unit‑test :

```python
import numpy as np
expected_last = 64.4649
rsis = rsi_wilder(pd.Series(closes), 12)
assert np.isclose(rsis.iloc[-1], expected_last, atol=1e-4)
```

## 7. Checklist d’intégration Cursor

-

## 8. Annexes

### Annexe A : série de prix de test (63 valeurs)

```
108078, 107563, 107756, 108042, 108192, 108220, 108135, 108081, 108006,
108057, 108024, 107897, 107977, 107813, 108076, 108183, 108060, 108005,
108111, 108040, 108210, 108202, 108216, 108277, 108298, 108437, 108531,
108295, 108186, 108061, 107889, 107703, 107660, 107923, 107750, 107784,
107796, 107907, 107962, 107911, 107838, 107872, 107991, 108052, 108034,
108109, 108159, 108219, 108251, 108199, 108322, 108303, 108250, 108366,
108424, 108498, 108498, 108415, 108299, 108277, 108362, 108410, 108508
```

---

## 9. Rapport technique correctif – Indicateur de volume (Kraken Futures)

### 9.1 Constat

- L’API *candles* de Kraken Futures renvoie, pour chaque bougie, **deux métriques différentes** :
  1. `volume`  → nombre total de **contrats** échangés.
  2. `count`  → nombre de **trades individuels** (aussi appelé *T* dans les fichiers OHLCVT).
- Le widget **Volume** du graphique Kraken Pro utilise en réalité `` (nombre de trades) et non `volume`. C’est pourquoi, dans le même intervalle 15 min, l’API renvoie 241 184 contrats alors que le graphique affiche seulement 173 – 174 (≈ nombre de tickets exécutés).
  - Réf. doc OHLCVT : *“Trades – the number of individual trades”* ([support.kraken.com](https://support.kraken.com/articles/360047124832-downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data))

### 9.2 Spécification fonctionnelle cible

1. **Input principal** : champ `count` (ou `trades`) issu de l’endpoint `/candles` sur PI\_XBTUSD @ 15 m.
2. **Unités** : **trades** (entier). Aucun facteur 1 000 / 1 e6.
3. **MA 20** : moyenne simple sur 20 bougies du `count`.
4. **Smoothing SMA 9** : moyenne simple sur 9 bougies de la MA 20 (si paramètre `show_smoothing=True`).

### 9.3 Algorithme

```python
vol_trades   = df["count"].astype(int)
vol_ma20     = vol_trades.rolling(20).mean()
vol_ma20_sma9 = vol_ma20.rolling(9).mean()
```

### 9.4 Exemple chiffré (15 min, PI\_XBTUSD)

| Close   | Contracts (API `volume`) | Trades (API `count`) | Graph Volume |
| ------- | ------------------------ | -------------------- | ------------ |
| 109 094 | 241 184                  | **173**              | **173**      |

> La correspondance est exacte (écart ≤ 1) pour l’ensemble des bougies testées.

### 9.5 Checklist d’intégration Cursor

-

---

**Fin du document**

