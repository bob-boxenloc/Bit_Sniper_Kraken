"""
Module de gestion de l'état pour BitSniper
Gère la persistance des données et l'état du bot pour la nouvelle stratégie
"""

import json
import os
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

class StateManager:
    """
    Gère l'état du bot et la persistance des données pour la nouvelle stratégie.
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
                
                # Vérifier et ajouter les nouvelles clés pour la nouvelle stratégie
                if 'new_strategy_state' not in state:
                    state['new_strategy_state'] = {
                        'last_position_type': None,
                        'vi1_phase_timestamp': None,
                        'vi1_current_phase': None,
                        'last_position_exit_time': None
                    }
                    self.logger.info("Clé new_strategy_state ajoutée à l'état existant")
                
                # Vérifier si data_progression existe, sinon l'ajouter
                if 'data_progression' not in state:
                    state['data_progression'] = {
                        'kraken_candles_count': 0,
                        'total_required': 50,  # Réduit pour RSI(40) + ATR(28)
                        'last_transition_date': None,
                        'is_transition_complete': False
                    }
                    self.logger.info("Clé data_progression ajoutée à l'état existant")
                
                self.logger.info(f"État chargé depuis {self.state_file}")
                return state
            else:
                # État initial pour la nouvelle stratégie
                initial_state = {
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'current_position': None,
                    'position_history': [],
                    'new_strategy_state': {
                        'last_position_type': None,
                        'vi1_phase_timestamp': None,
                        'vi1_current_phase': None,
                        'last_position_exit_time': None
                    },
                    'data_progression': {
                        'kraken_candles_count': 0,
                        'total_required': 50,  # Réduit pour les nouveaux indicateurs
                        'last_transition_date': None,
                        'is_transition_complete': False
                    },
                    'trading_stats': {
                        'total_trades': 0,
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'total_pnl': 0.0,
                        'shorts_count': 0,
                        'long_vi1_count': 0,
                        'long_vi2_count': 0,
                        'long_reentry_count': 0
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
    
    # Méthodes pour la nouvelle stratégie
    
    def get_last_position_type(self) -> Optional[str]:
        """Récupère le type de la dernière position."""
        return self.state.get('new_strategy_state', {}).get('last_position_type')
    
    def set_last_position_type(self, position_type: str) -> None:
        """Définit le type de la dernière position."""
        if 'new_strategy_state' not in self.state:
            self.state['new_strategy_state'] = {}
        self.state['new_strategy_state']['last_position_type'] = position_type
        self._save_state(self.state)
        self.logger.info(f"Type de dernière position mis à jour: {position_type}")
    
    def get_vi1_phase_timestamp(self) -> Optional[float]:
        """Récupère le timestamp du dernier changement de phase VI1."""
        return self.state.get('new_strategy_state', {}).get('vi1_phase_timestamp')
    
    def set_vi1_phase_timestamp(self, timestamp: float) -> None:
        """Définit le timestamp du dernier changement de phase VI1."""
        if 'new_strategy_state' not in self.state:
            self.state['new_strategy_state'] = {}
        self.state['new_strategy_state']['vi1_phase_timestamp'] = timestamp
        self._save_state(self.state)
        self.logger.info(f"Timestamp phase VI1 mis à jour: {timestamp}")
    
    def get_vi1_current_phase(self) -> Optional[str]:
        """Récupère la phase actuelle VI1 ('SHORT' ou 'LONG')."""
        return self.state.get('new_strategy_state', {}).get('vi1_current_phase')
    
    def set_vi1_current_phase(self, phase: str) -> None:
        """Définit la phase actuelle VI1."""
        if 'new_strategy_state' not in self.state:
            self.state['new_strategy_state'] = {}
        self.state['new_strategy_state']['vi1_current_phase'] = phase
        self._save_state(self.state)
        self.logger.info(f"Phase VI1 mise à jour: {phase}")
    
    def update_vi1_phase(self, new_phase: str) -> None:
        """Met à jour la phase VI1 et enregistre le timestamp."""
        current_phase = self.get_vi1_current_phase()
        if current_phase != new_phase:
            self.set_vi1_current_phase(new_phase)
            self.set_vi1_phase_timestamp(time.time())
            self.logger.info(f"Changement de phase VI1: {current_phase} → {new_phase}")
    
    def get_last_position_exit_time(self) -> Optional[float]:
        """Récupère le timestamp de la dernière sortie de position."""
        return self.state.get('new_strategy_state', {}).get('last_position_exit_time')
    
    def set_last_position_exit_time(self, timestamp: float) -> None:
        """Définit le timestamp de la dernière sortie de position."""
        if 'new_strategy_state' not in self.state:
            self.state['new_strategy_state'] = {}
        self.state['new_strategy_state']['last_position_exit_time'] = timestamp
        self._save_state(self.state)
    
    # Méthodes existantes adaptées
    
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
        # Vérifier d'abord si on a assez de données historiques (960 bougies)
        try:
            from data.market_data import candle_buffer
            current_candles = len(candle_buffer.get_candles())
            if current_candles >= 960:
                return True
        except Exception as e:
            self.logger.warning(f"Erreur lors de la vérification du buffer: {e}")
        
        # Fallback vers l'ancienne logique
        return self.state.get('data_progression', {}).get('is_transition_complete', False)
    
    def get_kraken_candles_count(self) -> int:
        """Récupère le nombre de bougies Kraken récupérées."""
        return self.state.get('data_progression', {}).get('kraken_candles_count', 0)

    def update_position(self, position_type: str, action: str, data: Dict[str, Any]) -> None:
        """
        Met à jour la position actuelle pour la nouvelle stratégie.
        
        :param position_type: Type de position (SHORT, LONG_VI1, LONG_VI2, LONG_REENTRY)
        :param action: Action (open, close)
        :param data: Données de la position
        """
        if action == 'open':
            self.state['current_position'] = {
                'type': position_type,
                'entry_time': datetime.now().isoformat(),
                'entry_data': data
            }
            # Mettre à jour le type de dernière position
            self.set_last_position_type(position_type)
            
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
                
                # Mettre à jour les stats par type de position
                position_type = self.state['current_position']['type']
                if position_type == 'SHORT':
                    self.state['trading_stats']['shorts_count'] += 1
                elif position_type == 'LONG_VI1':
                    self.state['trading_stats']['long_vi1_count'] += 1
                elif position_type == 'LONG_VI2':
                    self.state['trading_stats']['long_vi2_count'] += 1
                elif position_type == 'LONG_REENTRY':
                    self.state['trading_stats']['long_reentry_count'] += 1
                
                # Enregistrer le timestamp de sortie
                self.set_last_position_exit_time(time.time())
            
            self.state['current_position'] = None
        
        self._save_state(self.state)
    
    def get_current_position(self) -> Optional[Dict[str, Any]]:
        """Récupère la position actuelle."""
        return self.state.get('current_position')
    
    def get_state_summary(self) -> str:
        """Génère un résumé de l'état du bot pour la nouvelle stratégie."""
        summary = []
        summary.append("📊 ÉTAT DU BOT (Nouvelle Stratégie):")
        
        # Vérifier si on a assez de données historiques (960 bougies)
        # Si oui, considérer la transition comme complète
        from data.market_data import candle_buffer
        current_candles = len(candle_buffer.get_candles())
        
        if current_candles >= 960:
            summary.append("   ✅ Données historiques complètes (960 bougies)")
            summary.append("   ✅ Prêt pour le trading")
        else:
            # Progression des données (fallback)
            progression = self.get_data_progression()
            kraken_count = progression.get('kraken_candles_count', 0)
            total_required = progression.get('total_required', 50)
            is_complete = progression.get('is_transition_complete', False)
            
            if is_complete:
                summary.append("   ✅ Transition vers données temps réel: TERMINÉE")
            else:
                progress_pct = (kraken_count / total_required) * 100
                summary.append(f"   🔄 Progression données: {kraken_count}/{total_required} ({progress_pct:.1f}%)")
        
        # État VI1
        vi1_phase = self.get_vi1_current_phase()
        vi1_timestamp = self.get_vi1_phase_timestamp()
        if vi1_phase and vi1_timestamp:
            hours_since_change = (time.time() - vi1_timestamp) / 3600
            summary.append(f"   📈 Phase VI1: {vi1_phase} (depuis {hours_since_change:.1f}h)")
        
        # Position actuelle
        current_pos = self.get_current_position()
        if current_pos:
            summary.append(f"   📈 Position ouverte: {current_pos['type']}")
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
            summary.append(f"      Répartition: SHORT={stats.get('shorts_count', 0)}, "
                         f"LONG_VI1={stats.get('long_vi1_count', 0)}, "
                         f"LONG_VI2={stats.get('long_vi2_count', 0)}, "
                         f"LONG_REENTRY={stats.get('long_reentry_count', 0)}")
        
        return "\n".join(summary)