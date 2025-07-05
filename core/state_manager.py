"""
Module de gestion d'état pour BitSniper
Sauvegarde et restaure l'état du bot (RSI d'entrée, positions, etc.)
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class StateManager:
    def __init__(self, state_file="bot_state.json"):
        """
        Initialise le gestionnaire d'état.
        
        :param state_file: Chemin vers le fichier de sauvegarde d'état
        """
        self.state_file = state_file
        self.state = self.load_state()
        # S'assurer que la clé 'positions' existe toujours
        self._ensure_positions_key_exists()
    
    def load_state(self) -> Dict[str, Any]:
        """
        Charge l'état depuis le fichier de sauvegarde.
        
        :return: dict avec l'état du bot
        """
        if not os.path.exists(self.state_file):
            # État initial par défaut
            return {
                'created_at': datetime.utcnow().isoformat(),
                'last_updated': datetime.utcnow().isoformat(),
                'positions': {},
                'long2_entry_rsi': None,
                'long2_entry_time': None,
                'last_long2_time': None,
                'trading_stats': {
                    'total_trades': 0,
                    'successful_trades': 0,
                    'failed_trades': 0
                }
            }
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                print(f"✅ État chargé depuis {self.state_file}")
                return state
        except Exception as e:
            print(f"❌ Erreur lors du chargement de l'état: {e}")
            # Retourner un état par défaut en cas d'erreur
            return {
                'created_at': datetime.utcnow().isoformat(),
                'last_updated': datetime.utcnow().isoformat(),
                'positions': {},
                'long2_entry_rsi': None,
                'long2_entry_time': None,
                'last_long2_time': None,
                'trading_stats': {
                    'total_trades': 0,
                    'successful_trades': 0,
                    'failed_trades': 0
                }
            }
    
    def save_state(self):
        """
        Sauvegarde l'état actuel dans le fichier.
        """
        try:
            self.state['last_updated'] = datetime.utcnow().isoformat()
            
            # Créer le dossier si nécessaire
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            
            print(f"✅ État sauvegardé dans {self.state_file}")
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde de l'état: {e}")
    
    def get_long2_entry_rsi(self) -> Optional[float]:
        """
        Récupère le RSI d'entrée de la position long2 actuelle.
        
        :return: RSI d'entrée ou None si pas de position long2
        """
        return self.state.get('long2_entry_rsi')
    
    def set_long2_entry_rsi(self, rsi: float, entry_time: str = None):
        """
        Sauvegarde le RSI d'entrée pour une position long2.
        
        :param rsi: RSI d'entrée
        :param entry_time: Timestamp d'entrée (optionnel)
        """
        self.state['long2_entry_rsi'] = rsi
        self.state['long2_entry_time'] = entry_time or datetime.utcnow().isoformat()
        self.state['last_long2_time'] = datetime.utcnow().isoformat()
        self.save_state()
        print(f"💾 RSI d'entrée long2 sauvegardé: {rsi:.2f}")
    
    def clear_long2_entry_rsi(self):
        """
        Efface le RSI d'entrée long2 (quand la position est fermée).
        """
        self.state['long2_entry_rsi'] = None
        self.state['long2_entry_time'] = None
        self.save_state()
        print("🗑️ RSI d'entrée long2 effacé")
    
    def can_open_long2(self, current_rsi: float) -> bool:
        """
        Vérifie si on peut ouvrir une nouvelle position long2.
        
        :param current_rsi: RSI actuel
        :return: True si on peut ouvrir long2
        """
        last_long2_time = self.state.get('last_long2_time')
        
        if not last_long2_time:
            # Première position long2
            return True
        
        # Vérifier si le RSI est repassé sous 50 depuis la dernière position long2
        # Cette logique est dans le module de décision, mais on peut l'aider ici
        return True  # La vérification complète se fait dans decision.py
    
    def _ensure_positions_key_exists(self):
        """
        S'assure que la clé 'positions' existe dans l'état.
        Si elle n'existe pas, la crée avec un dictionnaire vide.
        """
        if 'positions' not in self.state:
            print("⚠️  Clé 'positions' manquante dans l'état, création...")
            self.state['positions'] = {}
            self.save_state()
            print("✅ Clé 'positions' créée dans l'état")

    def update_position(self, position_type: str, action: str, details: Dict[str, Any]):
        """
        Met à jour les informations de position.
        
        :param position_type: Type de position ('long1', 'long2', 'short')
        :param action: Action effectuée ('open', 'close')
        :param details: Détails de la position
        """
        # S'assurer que la clé 'positions' existe
        self._ensure_positions_key_exists()
        
        if action == 'open':
            self.state['positions'][position_type] = {
                'opened_at': datetime.utcnow().isoformat(),
                'entry_price': details.get('entry_price'),
                'entry_rsi': details.get('entry_rsi'),
                'size': details.get('size'),
                'status': 'open'
            }
            
            # Si c'est une position long2, sauvegarder le RSI d'entrée
            if position_type == 'long2':
                self.set_long2_entry_rsi(details.get('entry_rsi'))
        
        elif action == 'close':
            if position_type in self.state['positions']:
                self.state['positions'][position_type]['closed_at'] = datetime.utcnow().isoformat()
                self.state['positions'][position_type]['exit_price'] = details.get('exit_price')
                self.state['positions'][position_type]['exit_rsi'] = details.get('exit_rsi')
                self.state['positions'][position_type]['pnl'] = details.get('pnl')
                self.state['positions'][position_type]['status'] = 'closed'
                
                # Si c'est une position long2, effacer le RSI d'entrée
                if position_type == 'long2':
                    self.clear_long2_entry_rsi()
        
        self.save_state()
    
    def get_current_position(self) -> Optional[Dict[str, Any]]:
        """
        Récupère la position actuellement ouverte.
        
        :return: Détails de la position ouverte ou None
        """
        # S'assurer que la clé 'positions' existe
        self._ensure_positions_key_exists()
        
        for pos_type, pos_data in self.state['positions'].items():
            if pos_data.get('status') == 'open':
                return {
                    'type': pos_type,
                    **pos_data
                }
        return None
    
    def get_state_summary(self) -> str:
        """
        Génère un résumé de l'état actuel.
        
        :return: String avec le résumé
        """
        summary = []
        summary.append("📊 ÉTAT DU BOT:")
        summary.append(f"   Dernière mise à jour: {self.state.get('last_updated', 'N/A')}")
        
        # Position actuelle
        current_pos = self.get_current_position()
        if current_pos:
            summary.append(f"   Position ouverte: {current_pos['type'].upper()}")
            summary.append(f"     Prix d'entrée: ${current_pos.get('entry_price', 'N/A')}")
            summary.append(f"     RSI d'entrée: {current_pos.get('entry_rsi', 'N/A')}")
            summary.append(f"     Taille: {current_pos.get('size', 'N/A')} BTC")
        else:
            summary.append("   Aucune position ouverte")
        
        # RSI long2 si applicable
        long2_rsi = self.get_long2_entry_rsi()
        if long2_rsi:
            summary.append(f"   RSI d'entrée long2: {long2_rsi:.2f}")
        
        # Statistiques
        stats = self.state.get('trading_stats', {})
        summary.append(f"   Total trades: {stats.get('total_trades', 0)}")
        summary.append(f"   Trades réussis: {stats.get('successful_trades', 0)}")
        summary.append(f"   Trades échoués: {stats.get('failed_trades', 0)}")
        
        return "\n".join(summary)

# Test du module
if __name__ == "__main__":
    # Test avec un fichier temporaire
    sm = StateManager("test_state.json")
    
    # Test sauvegarde RSI long2
    sm.set_long2_entry_rsi(72.5)
    print(f"RSI récupéré: {sm.get_long2_entry_rsi()}")
    
    # Test position
    sm.update_position('long2', 'open', {
        'entry_price': 40000,
        'entry_rsi': 72.5,
        'size': 0.001
    })
    
    print(sm.get_state_summary())
    
    # Nettoyer le fichier de test
    if os.path.exists("test_state.json"):
        os.remove("test_state.json") 