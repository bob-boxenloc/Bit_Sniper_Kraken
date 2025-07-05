"""
Module de gestion d'état pour BitSniper
Sauvegarde et restaure l'état du bot (RSI d'entrée, positions, etc.)
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from core.logger import get_logger

logger = get_logger(__name__)

class StateManager:
    def __init__(self, state_file: str = "bot_state.json"):
        self.state_file = state_file
        self.state = self.load_state()
        
    def load_state(self) -> dict:
        """Charge l'état du bot depuis le fichier JSON"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"État chargé depuis {self.state_file}")
                return state
            except Exception as e:
                logger.error(f"Erreur lors du chargement de l'état: {e}")
                return self.get_default_state()
        else:
            logger.info("Aucun fichier d'état trouvé, utilisation de l'état par défaut")
            return self.get_default_state()
    
    def get_default_state(self) -> dict:
        """Retourne l'état par défaut du bot"""
        return {
            "last_action": "hold",
            "last_long1_entry_rsi": None,
            "last_long2_entry_rsi": None,
            "last_short1_entry_rsi": None,
            "last_short2_entry_rsi": None,
            "initialized": False,
            "initial_data_loaded": False
        }
    
    def save_state(self):
        """Sauvegarde l'état du bot dans le fichier JSON"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug("État sauvegardé")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'état: {e}")
    
    def update_state(self, key: str, value):
        """Met à jour une valeur dans l'état et sauvegarde"""
        self.state[key] = value
        self.save_state()
    
    def get_state(self, key: str, default=None):
        """Récupère une valeur de l'état"""
        return self.state.get(key, default)
    
    def load_initial_data(self, data_file: str = "initial_data_template.json") -> Optional[List[Dict]]:
        """Charge les données d'initialisation depuis le fichier JSON"""
        if not os.path.exists(data_file):
            logger.warning(f"Fichier de données d'initialisation non trouvé: {data_file}")
            return None
            
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, dict) or 'data' not in data:
                logger.error("Format de fichier invalide: 'data' manquant")
                return None
                
            initial_data = data['data']
            
            if not isinstance(initial_data, list):
                logger.error("Format de fichier invalide: 'data' doit être une liste")
                return None
                
            # Vérifier qu'on a au moins 27 bougies (minimum requis)
            if len(initial_data) < 27:
                logger.error(f"Données insuffisantes: {len(initial_data)} bougies (minimum 27 requis)")
                return None
                
            # Vérifier le format des données
            for i, candle in enumerate(initial_data):
                required_fields = ['datetime', 'close', 'rsi', 'volume_normalized']
                missing_fields = [field for field in required_fields if field not in candle]
                if missing_fields:
                    logger.error(f"Bougie {i} manque les champs: {missing_fields}")
                    return None
                    
                # Convertir les valeurs en float
                try:
                    candle['close'] = float(candle['close'])
                    candle['rsi'] = float(candle['rsi'])
                    candle['volume_normalized'] = float(candle['volume_normalized'])
                except (ValueError, TypeError) as e:
                    logger.error(f"Erreur de conversion des valeurs pour la bougie {i}: {e}")
                    return None
            
            logger.info(f"Données d'initialisation chargées: {len(initial_data)} bougies")
            return initial_data
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données d'initialisation: {e}")
            return None
    
    def is_initialized(self) -> bool:
        """Vérifie si le bot a été initialisé avec des données historiques"""
        return self.get_state("initialized", False)
    
    def mark_initialized(self):
        """Marque le bot comme initialisé"""
        self.update_state("initialized", True)
        logger.info("Bot marqué comme initialisé avec données historiques") 