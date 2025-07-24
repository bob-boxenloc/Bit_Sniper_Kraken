"""
Module de gestion des trades pour BitSniper
Implémente l'ouverture et la fermeture des positions via l'API Kraken Futures pour la nouvelle stratégie
"""

import time
import logging
from kraken.futures import Trade
from core.error_handler import handle_network_errors

class TradeManager:
    def __init__(self, api_key, api_secret):
        """
        Initialise le gestionnaire de trades.
        
        :param api_key: Clé API Kraken Futures
        :param api_secret: Secret API Kraken Futures
        """
        self.trade = Trade(key=api_key, secret=api_secret)
        self.symbol = "PI_XBTUSD"  # Symbole BTC Perp selon la doc Kraken
        self.logger = logging.getLogger(__name__)
        
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
        
        :param size: Taille de la position en BTC (ex: 0.001)
        :param order_type: Type d'ordre ("mkt" pour market, "lmt" pour limit)
        :return: dict avec le résultat de l'ordre
        """
        try:
            self.logger.info(f"Fermeture position LONG: {size:.4f} BTC ({order_type})")
            
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
        
        :param size: Taille de la position en BTC (ex: 0.001)
        :param order_type: Type d'ordre ("mkt" pour market, "lmt" pour limit)
        :return: dict avec le résultat de l'ordre
        """
        try:
            self.logger.info(f"Fermeture position SHORT: {size:.4f} BTC ({order_type})")
            
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
        Exécute une décision de trading pour la nouvelle stratégie.
        
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
        
        # Exécuter l'action selon la nouvelle stratégie
        if action in ['enter_long_vi1', 'enter_long_vi2', 'enter_long_reentry']:
            result = self.open_long_position(decision['size'])
            result['decision'] = decision
            result['position_type'] = decision['position_type']
            return result
            
        elif action == 'enter_short':
            result = self.open_short_position(decision['size'])
            result['decision'] = decision
            result['position_type'] = decision['position_type']
            return result
            
        elif action == 'exit_long':
            position = decision['position']
            result = self.close_long_position(position['size'])
            result['decision'] = decision
            result['position_type'] = position.get('type', 'LONG')
            return result
            
        elif action == 'exit_short':
            position = decision['position']
            result = self.close_short_position(position['size'])
            result['decision'] = decision
            result['position_type'] = position.get('type', 'SHORT')
            return result
        
        else:
            return {
                'executed': False,
                'reason': f'Action non reconnue: {action}',
                'decision': decision
            }
    
    def get_execution_summary(self, execution_result):
        """
        Génère un résumé lisible du résultat d'exécution pour la nouvelle stratégie.
        
        :param execution_result: dict retourné par execute_decision()
        :return: str avec le résumé
        """
        if not execution_result.get('executed', True):
            return f"❌ NON EXÉCUTÉ: {execution_result['reason']}"
        
        if not execution_result.get('success', False):
            return f"❌ ERREUR: {execution_result['error']}"
        
        # Succès
        action = execution_result['decision']['action']
        position_type = execution_result.get('position_type', 'UNKNOWN')
        
        if action.startswith('enter_'):
            size = execution_result['decision']['size']
            price = execution_result.get('price', 'N/A')
            return f"✅ POSITION {position_type} OUVERTE: {size:.4f} BTC @ ${price}"
        elif action.startswith('exit_'):
            price = execution_result.get('price', 'N/A')
            reason = execution_result['decision']['reason']
            return f"✅ POSITION {position_type} FERMÉE @ ${price} - {reason}"
        
        return "✅ Action exécutée avec succès"

# Test du module
if __name__ == "__main__":
    # Test avec des clés fictives
    import os
    api_key = os.getenv("KRAKEN_API_KEY", "test_key")
    api_secret = os.getenv("KRAKEN_API_SECRET", "test_secret")
    
    tm = TradeManager(api_key, api_secret)
    
    # Test de décision fictive pour la nouvelle stratégie
    test_decision = {
        'action': 'enter_long_vi1',
        'size': 0.001,
        'entry_price': 40000,
        'entry_rsi': 55.0,
        'position_type': 'LONG_VI1',
        'entry_time': time.time()
    }
    
    test_account = {
        'max_position_size': {'max_btc_size': 0.002}
    }
    
    result = tm.execute_decision(test_decision, test_account)
    summary = tm.get_execution_summary(result)
    
    print(summary) 