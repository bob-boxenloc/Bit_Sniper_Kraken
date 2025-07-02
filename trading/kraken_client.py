import os
import logging
from kraken.futures import User, Trade, Market
from core.error_handler import handle_network_errors

class KrakenFuturesClient:
    def __init__(self):
        self.api_key = os.getenv("KRAKEN_API_KEY")
        self.api_secret = os.getenv("KRAKEN_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise ValueError("Les variables d'environnement KRAKEN_API_KEY et KRAKEN_API_SECRET doivent être définies.")
        
        self.logger = logging.getLogger(__name__)
        self.user = User(key=self.api_key, secret=self.api_secret)
        self.trade = Trade(key=self.api_key, secret=self.api_secret)
        self.market = Market()

    @handle_network_errors(max_retries=3, timeout=10.0)
    def test_connection(self):
        try:
            wallets = self.user.get_wallets()
            self.logger.info("Connexion à Kraken Futures OK. Comptes disponibles :")
            for account, details in wallets.get('accounts', {}).items():
                self.logger.info(f"- {account}: {details.get('balances', {})}")
            return True
        except Exception as e:
            self.logger.error(f"Erreur de connexion à Kraken Futures : {e}")
            return False

    @handle_network_errors(max_retries=3, timeout=15.0)
    def get_wallet_info(self):
        """
        Récupère les informations du portefeuille selon la doc Kraken Futures API
        Endpoint: /get_wallets
        """
        try:
            wallets = self.user.get_wallets()
            # Le compte principal est généralement 'flex' pour Kraken Futures
            flex_account = wallets.get('accounts', {}).get('flex', {})
            balances = flex_account.get('balances', {})
            
            # Récupérer le solde en USD (ou la devise de base)
            usd_balance = balances.get('USD', {}).get('available', 0)
            
            result = {
                'usd_balance': float(usd_balance),
                'total_balance': flex_account.get('totalBalance', 0),
                'raw_response': wallets  # Garder la réponse complète pour debug
            }
            
            self.logger.debug(f"Portefeuille récupéré: {result['usd_balance']} USD disponible")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du portefeuille : {e}")
            raise

    @handle_network_errors(max_retries=3, timeout=15.0)
    def get_open_positions(self):
        """
        Récupère les positions ouvertes selon la doc Kraken Futures API
        Endpoint: /get_open_positions
        """
        try:
            positions = self.user.get_open_positions()
            open_positions = positions.get('openPositions', [])
            
            # Filtrer pour ne garder que les positions BTC (PI_XBTUSD)
            btc_positions = []
            for pos in open_positions:
                if pos.get('symbol') == 'PI_XBTUSD':
                    btc_positions.append({
                        'side': pos.get('side'),  # 'long' ou 'short'
                        'size': float(pos.get('size', 0)),
                        'price': float(pos.get('price', 0)),
                        'unrealizedPnl': float(pos.get('unrealizedPnl', 0)),
                        'cost': float(pos.get('cost', 0)),
                        'fee': float(pos.get('fee', 0)),
                        'margin': float(pos.get('margin', 0))
                    })
            
            self.logger.debug(f"Positions ouvertes récupérées: {len(btc_positions)} positions BTC")
            return btc_positions
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des positions ouvertes : {e}")
            raise

    def calculate_max_position_size(self):
        """
        Calcule la taille maximale de position possible avec le levier x10
        Basé sur la marge disponible et les règles Kraken Futures
        """
        try:
            wallet_info = self.get_wallet_info()
            usd_balance = wallet_info['usd_balance']
            
            # Avec levier x10, on peut ouvrir une position de taille = marge × 10
            # Mais il faut garder une marge de sécurité pour les frais et variations
            # On prend 95% de la marge disponible pour être sûr
            max_position_value = usd_balance * 10 * 0.95
            
            # Convertir en taille BTC (approximatif, le prix exact sera récupéré au moment de l'ordre)
            # Prix BTC actuel ~ 40,000 USD, donc taille max en BTC
            estimated_btc_price = 40000  # Prix approximatif pour le calcul
            max_btc_size = max_position_value / estimated_btc_price
            
            # Arrondir à 4 décimales (unité minimum 0.0001 BTC)
            max_btc_size = round(max_btc_size, 4)
            
            # S'assurer qu'on respecte le minimum
            if max_btc_size < 0.0001:
                max_btc_size = 0.0001
            
            result = {
                'max_btc_size': max_btc_size,
                'max_usd_value': max_position_value,
                'available_margin': usd_balance,
                'leverage_used': 10
            }
            
            self.logger.debug(f"Taille max calculée: {max_btc_size:.4f} BTC ({max_position_value:.2f} USD)")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de la taille max : {e}")
            return {'max_btc_size': 0.0001, 'max_usd_value': 0, 'available_margin': 0, 'leverage_used': 10}

    def get_account_summary(self, current_price):
        """
        Récupère un résumé complet du compte pour debug/affichage
        """
        try:
            wallet_info = self.get_wallet_info()
            open_positions = self.get_open_positions()
            max_size_info = self.calculate_max_position_size()
            
            result = {
                'wallet': wallet_info,
                'positions': open_positions,
                'max_position_size': max_size_info,
                'current_btc_price': current_price,
                'has_open_position': len(open_positions) > 0
            }
            
            self.logger.debug(f"Résumé compte: {len(open_positions)} positions, ${current_price:,.2f} BTC")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du résumé du compte : {e}")
            raise

if __name__ == "__main__":
    kf = KrakenFuturesClient()
    if kf.test_connection():
        print("\n=== RÉSUMÉ DU COMPTE ===")
        summary = kf.get_account_summary()
        if summary:
            print(f"Solde USD disponible : {summary['wallet']['usd_balance']}")
            print(f"Prix BTC actuel : {summary['current_btc_price']}")
            print(f"Taille max position : {summary['max_position_size']['max_btc_size']} BTC")
            print(f"Positions ouvertes : {len(summary['positions'])}")
            if summary['positions']:
                for pos in summary['positions']:
                    print(f"  - {pos['side']} {pos['size']} BTC @ {pos['price']} (PnL: {pos['unrealizedPnl']})") 