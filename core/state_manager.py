"""
Module de gestion de l'état pour BitSniper
Gère la persistance des données et l'état du bot
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

class StateManager:
    """
    Gère l'état du bot et la persistance des données.
    """
    
    def __init__(self, state_file: str = "bot_state.json"):
        self.state_file = state_file
        self.logger = logging.getLogger(__name__)
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Charge l'état depuis le fichier JSON."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                self.logger.info(f"État chargé depuis {self.state_file}")
                return state
            else:
                # État initial
                initial_state = {
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'current_position': None,
                    'position_history': [],
                    'data_progression': {
                        'kraken_candles_count': 0,  # Nombre de bougies Kraken récupérées
                        'total_required': 80,        # Total requis pour la transition complète
                        'last_transition_date': None,
                        'is_transition_complete': False
                    },
                    'trading_stats': {
                        'total_trades': 0,
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'total_pnl': 0.0
                    }
                }
                self._save_state(initial_state)
                return initial_state
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de l'état: {e}")
            return {}
    
    def _save_state(self, state: Dict[str, Any]) -> None:
        """Sauvegarde l'état dans le fichier JSON."""
        try:
            state['last_updated'] = datetime.now().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            self.logger.debug(f"État sauvegardé dans {self.state_file}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de l'état: {e}")
    
    def update_data_progression(self, kraken_candles_count: int) -> None:
        """
        Met à jour la progression des données.
        
        :param kraken_candles_count: Nombre de bougies Kraken récupérées
        """
        self.state['data_progression']['kraken_candles_count'] = kraken_candles_count
        self.state['data_progression']['last_transition_date'] = datetime.now().isoformat()
        
        # Vérifier si la transition est complète
        if kraken_candles_count >= self.state['data_progression']['total_required']:
            self.state['data_progression']['is_transition_complete'] = True
        
        self._save_state(self.state)
        self.logger.info(f"Progression mise à jour: {kraken_candles_count}/{self.state['data_progression']['total_required']} bougies Kraken")
    
    def get_data_progression(self) -> Dict[str, Any]:
        """Récupère les informations de progression des données."""
        return self.state.get('data_progression', {})
    
    def is_transition_complete(self) -> bool:
        """Vérifie si la transition vers les données temps réel est complète."""
        return self.state.get('data_progression', {}).get('is_transition_complete', False)
    
    def get_kraken_candles_count(self) -> int:
        """Récupère le nombre de bougies Kraken récupérées."""
        return self.state.get('data_progression', {}).get('kraken_candles_count', 0)
    
    def update_position(self, position_type: str, action: str, data: Dict[str, Any]) -> None:
        """
        Met à jour la position actuelle.
        
        :param position_type: Type de position (long1, long2, short)
        :param action: Action (open, close)
        :param data: Données de la position
        """
        if action == 'open':
            self.state['current_position'] = {
                'type': position_type,
                'entry_time': datetime.now().isoformat(),
                'entry_data': data
            }
        elif action == 'close':
            if self.state['current_position']:
                # Ajouter à l'historique
                closed_position = {
                    **self.state['current_position'],
                    'exit_time': datetime.now().isoformat(),
                    'exit_data': data
                }
                self.state['position_history'].append(closed_position)
                
                # Mettre à jour les stats
                if 'pnl' in data:
                    self.state['trading_stats']['total_trades'] += 1
                    if data['pnl'] > 0:
                        self.state['trading_stats']['winning_trades'] += 1
                    else:
                        self.state['trading_stats']['losing_trades'] += 1
                    self.state['trading_stats']['total_pnl'] += data['pnl']
            
            self.state['current_position'] = None
        
        self._save_state(self.state)
    
    def get_current_position(self) -> Optional[Dict[str, Any]]:
        """Récupère la position actuelle."""
        return self.state.get('current_position')
    
    def get_long2_entry_rsi(self) -> Optional[float]:
        """Récupère le RSI d'entrée pour une position long2."""
        current_pos = self.get_current_position()
        if current_pos and current_pos['type'] == 'long2':
            return current_pos['entry_data'].get('entry_rsi')
        return None
    
    def get_state_summary(self) -> str:
        """Génère un résumé de l'état du bot."""
        summary = []
        summary.append("📊 ÉTAT DU BOT:")
        
        # Progression des données
        progression = self.get_data_progression()
        kraken_count = progression.get('kraken_candles_count', 0)
        total_required = progression.get('total_required', 80)
        is_complete = progression.get('is_transition_complete', False)
        
        if is_complete:
            summary.append("   ✅ Transition vers données temps réel: TERMINÉE")
        else:
            progress_pct = (kraken_count / total_required) * 100
            summary.append(f"   🔄 Progression données: {kraken_count}/{total_required} ({progress_pct:.1f}%)")
        
        # Position actuelle
        current_pos = self.get_current_position()
        if current_pos:
            summary.append(f"   📈 Position ouverte: {current_pos['type'].upper()}")
            summary.append(f"      Entrée: ${current_pos['entry_data'].get('entry_price', 0):.2f}")
            summary.append(f"      RSI: {current_pos['entry_data'].get('entry_rsi', 0):.2f}")
        else:
            summary.append("   ⚪ Aucune position ouverte")
        
        # Stats de trading
        stats = self.state.get('trading_stats', {})
        total_trades = stats.get('total_trades', 0)
        if total_trades > 0:
            win_rate = (stats.get('winning_trades', 0) / total_trades) * 100
            summary.append(f"   📊 Stats: {total_trades} trades, {win_rate:.1f}% win rate")
            summary.append(f"      PnL total: ${stats.get('total_pnl', 0):.2f}")
        
        return "\n".join(summary) 