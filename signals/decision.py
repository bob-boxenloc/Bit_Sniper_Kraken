"""
Module de décision pour BitSniper
Prend les décisions de trading basées sur l'analyse technique et l'état du compte
"""

def decide_action(analysis, conditions_check, account_summary, state_manager=None):
    """
    Prend une décision de trading basée sur l'analyse technique et l'état du compte.
    
    :param analysis: dict retourné par analyze_candles()
    :param conditions_check: dict retourné par check_all_conditions()
    :param account_summary: dict retourné par get_account_summary()
    :param previous_state: dict avec l'état précédent (positions, RSI d'entrée, etc.)
    :return: dict avec la décision prise
    """
    
    # TEMPORAIRE: Bloquer tous les trades pour debug
    return {
        'action': 'hold',
        'reason': 'Trading temporairement désactivé pour debug RSI/Volume',
        'details': 'En attente de validation des données RSI et volume'
    }
    
    # Vérifications de base
    if not conditions_check['trading_allowed']:
        return {
            'action': 'hold',
            'reason': conditions_check['reason'],
            'details': 'Trading bloqué par règle de sécurité'
        }
    
    # Vérifier s'il y a déjà une position ouverte
    has_open_position = account_summary['has_open_position']
    open_positions = account_summary['positions']
    
    # Si on a une position ouverte, vérifier les conditions de sortie
    if has_open_position:
        return check_exit_conditions(analysis, open_positions, state_manager)
    
    # Si pas de position, vérifier les conditions d'entrée
    return check_entry_conditions(analysis, conditions_check, account_summary, state_manager)

def check_exit_conditions(analysis, open_positions, state_manager):
    """
    Vérifie les conditions de sortie pour les positions ouvertes.
    """
    if not open_positions:
        return {'action': 'hold', 'reason': 'Aucune position à vérifier'}
    
    position = open_positions[0]  # On ne gère qu'une position à la fois
    current_rsi = analysis['rsi_n1']
    current_close = analysis['close_n1']
    entry_price = position['price']
    
    # Calcul du pourcentage de perte/gain
    if position['side'] == 'long':
        price_change_pct = (current_close - entry_price) / entry_price * 100
    else:  # short
        price_change_pct = (entry_price - current_close) / entry_price * 100
    
    # Vérification des conditions de sortie selon le type de position
    if position['side'] == 'long':
        # Sortie long1: RSI >= 40
        if current_rsi >= 40:
            return {
                'action': 'exit_long',
                'reason': f'RSI ({current_rsi:.2f}) >= 40',
                'position': position,
                'exit_type': 'target'
            }
        
        # Stop loss long1: -0.7%
        if price_change_pct <= -0.7:
            return {
                'action': 'exit_long',
                'reason': f'Stop loss atteint: {price_change_pct:.2f}%',
                'position': position,
                'exit_type': 'stop_loss'
            }
        
        # Pour long2, vérifier si on a le RSI d'entrée sauvegardé
        if state_manager:
            long2_entry_rsi = state_manager.get_long2_entry_rsi()
            if long2_entry_rsi is not None:
                target_rsi = long2_entry_rsi + 1.5
                if current_rsi >= target_rsi:  # >= pour "supérieur ou égal"
                    return {
                        'action': 'exit_long',
                        'reason': f'RSI ({current_rsi:.2f}) >= target ({target_rsi:.2f})',
                        'position': position,
                        'exit_type': 'target'
                    }
            
            # Stop loss long2: -1.1%
            if price_change_pct <= -1.1:
                return {
                    'action': 'exit_long',
                    'reason': f'Stop loss atteint: {price_change_pct:.2f}%',
                    'position': position,
                    'exit_type': 'stop_loss'
                }
    
    elif position['side'] == 'short':
        # Sortie short: RSI <= 60
        if current_rsi <= 60:
            return {
                'action': 'exit_short',
                'reason': f'RSI ({current_rsi:.2f}) <= 60',
                'position': position,
                'exit_type': 'target'
            }
        
        # Stop loss short: +0.8%
        if price_change_pct <= -0.8:  # Pour short, perte si prix monte
            return {
                'action': 'exit_short',
                'reason': f'Stop loss atteint: {price_change_pct:.2f}%',
                'position': position,
                'exit_type': 'stop_loss'
            }
    
    # Aucune condition de sortie remplie
    return {
        'action': 'hold',
        'reason': 'Position maintenue',
        'position': position,
        'pnl_pct': price_change_pct
    }

def check_entry_conditions(analysis, conditions_check, account_summary, state_manager):
    """
    Vérifie les conditions d'entrée pour ouvrir de nouvelles positions.
    """
    
    # Priorité des stratégies (long1 > long2 > short)
    if conditions_check['long1_ready']:
        return {
            'action': 'enter_long1',
            'reason': 'Conditions long1 remplies',
            'size': account_summary['max_position_size']['max_btc_size'],
            'entry_price': analysis['close_n1'],
            'entry_rsi': analysis['rsi_n1']
        }
    
    if conditions_check['long2_ready']:
        # Vérifier la règle supplémentaire pour long2
        if state_manager:
            # Vérifier si le RSI est repassé sous 50 depuis la dernière position long2
            # Cette logique sera implémentée plus tard si nécessaire
            pass
        
        return {
            'action': 'enter_long2',
            'reason': 'Conditions long2 remplies',
            'size': account_summary['max_position_size']['max_btc_size'],
            'entry_price': analysis['close_n1'],
            'entry_rsi': analysis['rsi_n1']
        }
    
    if conditions_check['short_ready']:
        return {
            'action': 'enter_short',
            'reason': 'Conditions short remplies',
            'size': account_summary['max_position_size']['max_btc_size'],
            'entry_price': analysis['close_n1'],
            'entry_rsi': analysis['rsi_n1']
        }
    
    # Aucune condition d'entrée remplie
    return {
        'action': 'hold',
        'reason': 'Aucune stratégie prête',
        'details': {
            'long1_ready': conditions_check['long1_ready'],
            'long2_ready': conditions_check['long2_ready'],
            'short_ready': conditions_check['short_ready']
        }
    }

def get_decision_summary(decision):
    """
    Génère un résumé lisible de la décision prise.
    """
    action = decision['action']
    reason = decision['reason']
    
    summary = []
    summary.append("🎯 DÉCISION DE TRADING:")
    
    if action == 'hold':
        summary.append(f"   ⏸️  MAINTIEN: {reason}")
    elif action.startswith('enter_'):
        strategy = action.replace('enter_', '').upper()
        summary.append(f"   🟢 OUVERTURE {strategy}")
        summary.append(f"      Raison: {reason}")
        summary.append(f"      Taille: {decision['size']:.4f} BTC")
        summary.append(f"      Prix: ${decision['entry_price']:.2f}")
        summary.append(f"      RSI: {decision['entry_rsi']:.2f}")
    elif action.startswith('exit_'):
        side = action.replace('exit_', '').upper()
        summary.append(f"   🔴 FERMETURE {side}")
        summary.append(f"      Raison: {reason}")
        summary.append(f"      Type: {decision.get('exit_type', 'unknown')}")
        if 'pnl_pct' in decision:
            summary.append(f"      PnL: {decision['pnl_pct']:.2f}%")
    
    return "\n".join(summary)

# Test du module
if __name__ == "__main__":
    # Test avec des données fictives
    test_analysis = {
        'rsi_n1': 35.0,
        'rsi_n2': 30.0,
        'close_n1': 40000,
        'volume_n1': 95,
        'volume_n2': 50
    }
    
    test_conditions = {
        'trading_allowed': True,
        'long1_ready': True,
        'long2_ready': False,
        'short_ready': False
    }
    
    test_account = {
        'has_open_position': False,
        'max_position_size': {'max_btc_size': 0.001}
    }
    
    decision = decide_action(test_analysis, test_conditions, test_account)
    summary = get_decision_summary(decision)
    
    print(summary) 