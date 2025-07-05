"""
Module d'initialisation pour BitSniper
Charge les données historiques pour initialiser RSI et volume normalisé
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd

class InitializationManager:
    """
    Gère le chargement et l'intégration des données d'initialisation.
    """
    
    def __init__(self, initial_data_file: str = "initial_data.json"):
        self.initial_data_file = initial_data_file
        self.logger = logging.getLogger(__name__)
        self.initial_data = None
        self.is_initialized = False
    
    def load_initial_data(self) -> bool:
        """
        Charge les données d'initialisation depuis le fichier JSON.
        
        :return: True si le chargement a réussi, False sinon
        """
        try:
            with open(self.initial_data_file, 'r') as f:
                self.initial_data = json.load(f)
            
            # Validation des données
            if not self._validate_initial_data():
                self.logger.error("Données d'initialisation invalides")
                return False
            
            self.logger.info(f"Données d'initialisation chargées: {len(self.initial_data['data'])} bougies")
            return True
            
        except FileNotFoundError:
            self.logger.warning(f"Fichier d'initialisation non trouvé: {self.initial_data_file}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"Erreur de décodage JSON: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des données d'initialisation: {e}")
            return False
    
    def _validate_initial_data(self) -> bool:
        """
        Valide la structure et le contenu des données d'initialisation.
        
        :return: True si les données sont valides
        """
        if not self.initial_data:
            return False
        
        # Vérifier la structure
        required_keys = ['description', 'instructions', 'required_periods', 'data']
        if not all(key in self.initial_data for key in required_keys):
            self.logger.error("Structure des données d'initialisation invalide")
            return False
        
        # Vérifier le nombre de périodes
        data = self.initial_data['data']
        required_periods = self.initial_data['required_periods']
        
        if len(data) != required_periods:
            self.logger.error(f"Nombre de bougies incorrect: {len(data)} au lieu de {required_periods}")
            return False
        
        # Vérifier chaque bougie
        for i, candle in enumerate(data):
            required_fields = ['datetime', 'close', 'rsi', 'volume_normalized']
            if not all(field in candle for field in required_fields):
                self.logger.error(f"Bougie {i} invalide: champs manquants")
                return False
            
            # Vérifier les types de données
            try:
                float(candle['close'])
                float(candle['rsi'])
                float(candle['volume_normalized'])
                datetime.fromisoformat(candle['datetime'])
            except (ValueError, TypeError) as e:
                self.logger.error(f"Bougie {i} invalide: données mal formatées - {e}")
                return False
        
        self.logger.info("Validation des données d'initialisation réussie")
        return True
    
    def get_initial_candles(self) -> List[Dict]:
        """
        Convertit les données d'initialisation en format compatible avec le bot.
        
        :return: Liste de bougies au format du bot
        """
        if not self.initial_data:
            self.logger.error("Données d'initialisation non chargées")
            return []
        
        candles = []
        for candle_data in self.initial_data['data']:
            # Convertir en format compatible avec le bot
            candle = {
                'time': int(datetime.fromisoformat(candle_data['datetime']).timestamp() * 1000),
                'datetime': datetime.fromisoformat(candle_data['datetime']),
                'open': float(candle_data['close']),  # On utilise close comme open pour simplifier
                'high': float(candle_data['close']),  # On utilise close comme high pour simplifier
                'low': float(candle_data['close']),   # On utilise close comme low pour simplifier
                'close': float(candle_data['close']),
                'volume': 1000.0  # Volume par défaut (ne sera pas utilisé pour le calcul)
            }
            candles.append(candle)
        
        self.logger.info(f"Converti {len(candles)} bougies d'initialisation")
        return candles
    
    def get_initial_rsi_series(self) -> pd.Series:
        """
        Extrait la série RSI des données d'initialisation.
        
        :return: Series pandas du RSI
        """
        if not self.initial_data:
            self.logger.error("Données d'initialisation non chargées")
            return pd.Series()
        
        rsi_values = [float(candle['rsi']) for candle in self.initial_data['data']]
        rsi_series = pd.Series(rsi_values)
        
        self.logger.info(f"Extrait série RSI d'initialisation: {len(rsi_series)} valeurs")
        return rsi_series
    
    def get_initial_volume_series(self) -> pd.Series:
        """
        Extrait la série volume normalisé des données d'initialisation.
        
        :return: Series pandas du volume normalisé
        """
        if not self.initial_data:
            self.logger.error("Données d'initialisation non chargées")
            return pd.Series()
        
        volume_values = [float(candle['volume_normalized']) for candle in self.initial_data['data']]
        volume_series = pd.Series(volume_values)
        
        self.logger.info(f"Extrait série volume d'initialisation: {len(volume_series)} valeurs")
        return volume_series
    
    def initialize_bot_data(self) -> Tuple[List[Dict], pd.Series, pd.Series]:
        """
        Initialise toutes les données nécessaires pour le bot.
        
        :return: (candles, rsi_series, volume_series)
        """
        if not self.load_initial_data():
            self.logger.error("Impossible de charger les données d'initialisation")
            return [], pd.Series(), pd.Series()
        
        candles = self.get_initial_candles()
        rsi_series = self.get_initial_rsi_series()
        volume_series = self.get_initial_volume_series()
        
        self.is_initialized = True
        self.logger.info("Initialisation du bot terminée avec succès")
        
        return candles, rsi_series, volume_series
    
    def is_ready(self) -> bool:
        """
        Vérifie si l'initialisation est prête.
        
        :return: True si l'initialisation est terminée
        """
        # Vérifier si le fichier existe
        if not os.path.exists(self.initial_data_file):
            return False
        return self.is_initialized and self.initial_data is not None

# Instance globale
initialization_manager = InitializationManager()

def initialize_bot():
    """
    Fonction principale d'initialisation du bot.
    
    :return: (candles, rsi_series, volume_series) ou (None, None, None) si échec
    """
    return initialization_manager.initialize_bot_data()

def is_initialization_ready() -> bool:
    """
    Vérifie si l'initialisation est prête.
    
    :return: True si l'initialisation est terminée
    """
    return initialization_manager.is_ready() 