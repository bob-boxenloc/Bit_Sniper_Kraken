"""
Module d'initialisation pour BitSniper
Démarre avec un buffer vide et attend les données Kraken
"""

import logging
from typing import List, Dict, Tuple
import pandas as pd

class InitializationManager:
    """
    Gère l'initialisation du bot avec un buffer vide.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
    
    def initialize_bot_data(self) -> Tuple[List[Dict], pd.Series, pd.Series]:
        """
        Initialise le bot avec un buffer vide.
        Le bot attendra que l'API Kraken fournisse assez de données.
        
        :return: (candles_vides, rsi_series_vide, volume_series_vide)
        """
        self.logger.info("Initialisation avec buffer vide - attente des données Kraken")
        
        # Buffer vide - le bot attendra les données Kraken
        candles = []
        rsi_series = pd.Series()
        
        self.is_initialized = True
        self.logger.info("Initialisation terminée - buffer vide prêt pour les données Kraken")
        
        return candles, rsi_series, pd.Series()
    
    def is_ready(self) -> bool:
        """
        L'initialisation est toujours prête (buffer vide).
        
        :return: True (toujours prêt)
        """
        return True

def initialize_bot():
    """
    Fonction d'initialisation simplifiée.
    
    :return: (candles_vides, rsi_series_vide, volume_series_vide)
    """
    manager = InitializationManager()
    return manager.initialize_bot_data()

def is_initialization_ready() -> bool:
    """
    Vérifie si l'initialisation est prête.
    
    :return: True (toujours prêt avec buffer vide)
    """
    return True 