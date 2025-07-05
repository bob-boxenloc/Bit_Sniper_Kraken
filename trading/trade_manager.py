"""
Module de gestion des trades pour BitSniper
Implémente l'ouverture et la fermeture des positions via l'API Kraken Futures
"""

import time
import logging
from kraken.futures import Trade
from core.error_handler import handle_network_errors
from core.logger import get_logger

class TradeManager:
    def __init__(self, kraken_client, state_manager):
        """
        Initialise le gestionnaire de trades.
        
        :param kraken_client: Instance du client Kraken
        :param state_manager: Instance du gestionnaire d'état
        """
        self.kraken_client = kraken_client
        self.state_manager = state_manager
        self.symbol = "PI_XBTUSD"  # Symbole BTC Perp selon la doc Kraken
        self.logger = get_logger(__name__)
        
    def execute_action(self, action, current_price):
        """
        Exécute une action de trading.
        
        :param action: Action à exécuter ('hold', 'enter_long1', etc.)
        :param current_price: Prix actuel
        :return: dict avec le résultat de l'exécution
        """
        if action == 'hold':
            return {
                'executed': False,
                'reason': 'Aucune action à exécuter',
                'action': action
            }
        
        # Pour l'instant, on ne fait rien (trading désactivé)
        self.logger.info(f"Action {action} ignorée (trading désactivé)")
        return {
            'executed': False,
            'reason': 'Trading temporairement désactivé',
            'action': action
        }
    
    @handle_network_errors(max_retries=3, timeout=30.0)
    def open_long_position(self, size, order_type="mkt"):
        """
        Ouvre une position longue (buy).
        
        :param size: Taille de la position en BTC (ex: 0.001)
        :param order_type: Type d'ordre ("mkt" pour market, "lmt" pour limit)
        :return: dict avec le résultat de l'ordre
        """
        try:
            self.logger.info(f"Ouverture position LONG: {size:.4f} BTC ({order_type})")
            
            # Selon la doc Kraken Futures API
            order = self.trade.create_order(
                orderType=order_type,
                side="buy",
                size=size,
                symbol=self.symbol
            )
            
            result = {
                'success': True,
                'order_id': order.get('orderId'),
                'status': order.get('status'),
                'filled_size': order.get('filledSize'),
                'price': order.get('price'),
                'raw_response': order
            }
            
            self.logger.info(f"Position LONG ouverte: {result['filled_size']} BTC @ ${result['price']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur ouverture position LONG: {e}")
            return {
                'success': False,
                'error': str(e),
                'action': 'open_long'
            }
    
    @handle_network_errors(max_retries=3, timeout=30.0)
    def open_short_position(self, size, order_type="mkt"):
        """
        Ouvre une position courte (sell).
        
        :param size: Taille de la position en BTC (ex: 0.001)
        :param order_type: Type d'ordre ("mkt" pour market, "lmt" pour limit)
        :return: dict avec le résultat de l'ordre
        """
        try:
            self.logger.info(f"Ouverture position SHORT: {size:.4f} BTC ({order_type})")
            
            # Selon la doc Kraken Futures API
            order = self.trade.create_order(
                orderType=order_type,
                side="sell",
                size=size,
                symbol=self.symbol
            )
            
            result = {
                'success': True,
                'order_id': order.get('orderId'),
                'status': order.get('status'),
                'filled_size': order.get('filledSize'),
                'price': order.get('price'),
                'raw_response': order
            }
            
            self.logger.info(f"Position SHORT ouverte: {result['filled_size']} BTC @ ${result['price']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur ouverture position SHORT: {e}")
            return {
                'success': False,
                'error': str(e),
                'action': 'open_short'
            }
    
    @handle_network_errors(max_retries=3, timeout=30.0)
    def close_long_position(self, size, order_type="mkt"):
        """
        Ferme une position longue (sell pour fermer un long).
        
        :param size: Taille de la position à fermer en BTC
        :param order_type: Type d'ordre ("mkt" pour market, "lmt" pour limit)
        :return: dict avec le résultat de l'ordre
        """
        try:
            self.logger.info(f"Fermeture position LONG: {size:.4f} BTC ({order_type})")
            
            # Pour fermer un long, on vend (sell)
            order = self.trade.create_order(
                orderType=order_type,
                side="sell",
                size=size,
                symbol=self.symbol,
                reduceOnly=True  # S'assurer qu'on ferme seulement, pas d'ouverture
            )
            
            result = {
                'success': True,
                'order_id': order.get('orderId'),
                'status': order.get('status'),
                'filled_size': order.get('filledSize'),
                'price': order.get('price'),
                'raw_response': order
            }
            
            self.logger.info(f"Position LONG fermée: {result['filled_size']} BTC @ ${result['price']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur fermeture position LONG: {e}")
            return {
                'success': False,
                'error': str(e),
                'action': 'close_long'
            }
    
    @handle_network_errors(max_retries=3, timeout=30.0)
    def close_short_position(self, size, order_type="mkt"):
        """
        Ferme une position courte (buy pour fermer un short).
        
        :param size: Taille de la position à fermer en BTC
        :param order_type: Type d'ordre ("mkt" pour market, "lmt" pour limit)
        :return: dict avec le résultat de l'ordre
        """
        try:
            self.logger.info(f"Fermeture position SHORT: {size:.4f} BTC ({order_type})")
            
            # Pour fermer un short, on achète (buy)
            order = self.trade.create_order(
                orderType=order_type,
                side="buy",
                size=size,
                symbol=self.symbol,
                reduceOnly=True  # S'assurer qu'on ferme seulement, pas d'ouverture
            )
            
            result = {
                'success': True,
                'order_id': order.get('orderId'),
                'status': order.get('status'),
                'filled_size': order.get('filledSize'),
                'price': order.get('price'),
                'raw_response': order
            }
            
            self.logger.info(f"Position SHORT fermée: {result['filled_size']} BTC @ ${result['price']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur fermeture position SHORT: {e}")
            return {
                'success': False,
                'error': str(e),
                'action': 'close_short'
            }
    
    def execute_decision(self, decision, account_summary):
        """
        Exécute une décision de trading.
        
        :param decision: dict retourné par decide_action()
        :param account_summary: dict retourné par get_account_summary()
        :return: dict avec le résultat de l'exécution
        """
        action = decision['action']
        
        if action == 'hold':
            return {
                'executed': False,
                'reason': 'Aucune action à exécuter',
                'decision': decision
            }
        
        # Vérifier qu'on a assez de marge pour trader
        if 'size' in decision:
            max_size = account_summary['max_position_size']['max_btc_size']
            if decision['size'] > max_size:
                return {
                    'executed': False,
                    'reason': f'Taille demandée ({decision["size"]:.4f} BTC) > taille max ({max_size:.4f} BTC)',
                    'decision': decision
                }
        
        # Exécuter l'action
        if action == 'enter_long1' or action == 'enter_long2':
            result = self.open_long_position(decision['size'])
            result['decision'] = decision
            return result
            
        elif action == 'enter_short':
            result = self.open_short_position(decision['size'])
            result['decision'] = decision
            return result
            
        elif action == 'exit_long':
            position = decision['position']
            result = self.close_long_position(position['size'])
            result['decision'] = decision
            return result
            
        elif action == 'exit_short':
            position = decision['position']
            result = self.close_short_position(position['size'])
            result['decision'] = decision
            return result
        
        else:
            return {
                'executed': False,
                'reason': f'Action non reconnue: {action}',
                'decision': decision
            }
    
    def get_execution_summary(self, execution_result):
        """
        Génère un résumé lisible du résultat d'exécution.
        
        :param execution_result: dict retourné par execute_decision()
        :return: str avec le résumé
        """
        if not execution_result.get('executed', True):
            return f"❌ NON EXÉCUTÉ: {execution_result['reason']}"
        
        if not execution_result.get('success', False):
            return f"❌ ERREUR: {execution_result['error']}"
        
        # Succès
        action = execution_result['decision']['action']
        if action.startswith('enter_'):
            strategy = action.replace('enter_', '').upper()
            size = execution_result['decision']['size']
            price = execution_result.get('price', 'N/A')
            return f"✅ POSITION {strategy} OUVERTE: {size:.4f} BTC @ ${price}"
        elif action.startswith('exit_'):
            side = action.replace('exit_', '').upper()
            price = execution_result.get('price', 'N/A')
            reason = execution_result['decision']['reason']
            return f"✅ POSITION {side} FERMÉE @ ${price} - {reason}"
        
        return "✅ Action exécutée avec succès"

# Test du module
if __name__ == "__main__":
    # Test avec des clés fictives
    import os
    api_key = os.getenv("KRAKEN_API_KEY", "test_key")
    api_secret = os.getenv("KRAKEN_API_SECRET", "test_secret")
    
    tm = TradeManager(api_key, api_secret)
    
    # Test de décision fictive
    test_decision = {
        'action': 'enter_long1',
        'size': 0.001,
        'entry_price': 40000,
        'entry_rsi': 35.0
    }
    
    test_account = {
        'max_position_size': {'max_btc_size': 0.002}
    }
    
    result = tm.execute_decision(test_decision, test_account)
    summary = tm.get_execution_summary(result)
    
    print(summary) 