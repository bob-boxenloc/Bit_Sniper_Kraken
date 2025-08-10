"""
Module de décision pour BitSniper
Prend les décisions de trading basées sur la nouvelle stratégie RSI(40) + Volatility Indexes
"""

import time
from core.logger import logger

def decide_action(analysis, conditions_check, account_summary, state_manager=None):
    """
    Prend une décision de trading basée sur la nouvelle stratégie.
    
    :param analysis: dict retourné par analyze_candles()
    :param conditions_check: dict retourné par check_all_conditions()
    :param account_summary: dict retourné par get_account_summary()
    :param state_manager: gestionnaire d'état pour les règles de protection
    :return: dict avec la décision prise
    """
    
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
    Vérifie les conditions de sortie pour les positions ouvertes selon la nouvelle stratégie.
    """
    if not open_positions:
        return {'action': 'hold', 'reason': 'Aucune position à vérifier'}
    
    position = open_positions[0]  # On ne gère qu'une position à la fois
    current_rsi = analysis['rsi']
    current_close = analysis['current_close']
    entry_price = position['price']
    position_type = position.get('type', 'unknown')
    entry_rsi = position.get('entry_rsi')
    entry_time = position.get('entry_time', time.time())
    
    # Calcul du temps écoulé depuis l'entrée
    current_time = time.time()
    time_elapsed = current_time - entry_time
    hours_elapsed = time_elapsed / 3600
    
    # Vérification des délais de protection
    if position_type != "LONG_VI2":  # Exception pour LONG_VI2
        if hours_elapsed < 7:
            return {
                'action': 'hold',
                'reason': f'Protection 7h active ({hours_elapsed:.1f}h écoulées)',
                'position': position,
                'hours_elapsed': hours_elapsed
            }
    
    # Vérification des conditions de sortie selon le type de position
    if position_type == "SHORT":
        return check_short_exit_conditions(analysis, position, current_rsi, current_close, 
                                         entry_price, entry_rsi, hours_elapsed)
    
    elif position_type in ["LONG_VI1", "LONG_VI2", "LONG_REENTRY"]:
        return check_long_exit_conditions(analysis, position, current_rsi, current_close, 
                                        entry_price, entry_rsi, hours_elapsed)
    
    # Position type inconnu
    return {
        'action': 'hold',
        'reason': f'Type de position inconnu: {position_type}',
        'position': position
    }

def check_short_exit_conditions(analysis, position, current_rsi, current_close, 
                               entry_price, entry_rsi, hours_elapsed):
    """
    Vérifie les conditions de sortie pour les positions SHORT.
    """
    # Log des conditions de sortie
    logger.log_position_exit_conditions("SHORT", current_rsi, entry_rsi, hours_elapsed, "Vérification en cours")
    
    # Contrôle spécial à 3h pour SHORT
    if hours_elapsed >= 3 and hours_elapsed < 7:
        price_change_pct = (current_close - entry_price) / entry_price * 100
        if price_change_pct >= 1.0:
            logger.log_position_exit_conditions("SHORT", current_rsi, entry_rsi, hours_elapsed, f"Contrôle 3h: prix monté de {price_change_pct:.2f}%")
            return {
                'action': 'exit_short',
                'reason': f'Contrôle 3h: prix monté de {price_change_pct:.2f}%',
                'position': position,
                'exit_type': 'control_3h'
            }
    
    # Emergency exit après 7h
    if hours_elapsed >= 7:
        if entry_rsi is not None:
            rsi_increase = current_rsi - entry_rsi
            if rsi_increase > 18:
                logger.log_position_exit_conditions("SHORT", current_rsi, entry_rsi, hours_elapsed, f"Emergency exit: RSI monté de {rsi_increase:.2f} points")
                return {
                    'action': 'exit_short',
                    'reason': f'Emergency exit: RSI monté de {rsi_increase:.2f} points',
                    'position': position,
                    'exit_type': 'emergency'
                }
    
    # Exit principal basé sur la différence RSI
    if entry_rsi is not None and hours_elapsed >= 7:
        rsi_difference = entry_rsi - current_rsi  # Pour SHORT, on veut que RSI baisse
        
        # Déterminer le seuil selon le RSI d'entrée
        if 45 <= entry_rsi <= 50:
            threshold = 10
        elif 40 <= entry_rsi < 45:
            threshold = 7.5
        elif 35 <= entry_rsi < 40:
            threshold = 3.5
        elif 30 <= entry_rsi < 35:
            threshold = 1.75
        else:  # entry_rsi < 30
            threshold = 1
        
        if rsi_difference >= threshold:
            logger.log_position_exit_conditions("SHORT", current_rsi, entry_rsi, hours_elapsed, f"Exit principal: RSI baissé de {rsi_difference:.2f} points (seuil: {threshold})")
            return {
                'action': 'exit_short',
                'reason': f'Exit principal: RSI baissé de {rsi_difference:.2f} points (seuil: {threshold})',
                'position': position,
                'exit_type': 'target'
            }
        
    # Exit de dernier recours: VI1 repasse en-dessous du close
    if not analysis['vi1_above_close']:
        logger.log_position_exit_conditions("SHORT", current_rsi, entry_rsi, hours_elapsed, "VI1 repasse en-dessous du close")
        return {
            'action': 'exit_short',
            'reason': 'VI1 repasse en-dessous du close',
            'position': position,
            'exit_type': 'last_resort'
        }
    
    # Aucune condition de sortie remplie
    return {
        'action': 'hold',
        'reason': 'Position SHORT maintenue',
        'position': position,
        'hours_elapsed': hours_elapsed
    }

def check_long_exit_conditions(analysis, position, current_rsi, current_close, 
                              entry_price, entry_rsi, hours_elapsed):
    """
    Vérifie les conditions de sortie pour les positions LONG.
    """
    position_type = position['type']
    
    # Log des conditions de sortie
    logger.log_position_exit_conditions(position_type, current_rsi, entry_rsi, hours_elapsed, "Vérification en cours")
    
    # Exit principal basé sur la différence RSI (après 7h sauf pour LONG_VI2)
    if entry_rsi is not None and (hours_elapsed >= 7 or position_type == "LONG_VI2"):
        rsi_difference = current_rsi - entry_rsi  # Pour LONG, on veut que RSI monte
        
        # Déterminer le seuil selon le type de position et le RSI d'entrée
        if position_type == "LONG_VI1":
            if 45 <= entry_rsi <= 50:
                threshold = 20
            elif 50 <= entry_rsi < 55:
                threshold = 15
            elif 55 <= entry_rsi < 60:
                threshold = 9
            elif 60 <= entry_rsi < 65:
                threshold = 4.5
            elif 65 <= entry_rsi < 70:
                threshold = 3
            else:  # entry_rsi >= 70
                threshold = 1
        
        elif position_type == "LONG_VI2":
            if 45 <= entry_rsi <= 50:
                threshold = 9
            elif 50 <= entry_rsi < 55:
                threshold = 6.5
            elif 55 <= entry_rsi < 60:
                threshold = 3.5
            elif 60 <= entry_rsi < 65:
                threshold = 1.25
            elif 65 <= entry_rsi < 70:
                threshold = 0.5
            else:  # entry_rsi >= 70
                threshold = 0.5
        
        elif position_type == "LONG_REENTRY":
            if 45 <= entry_rsi <= 50:
                threshold = 18
            elif 50 <= entry_rsi < 55:
                threshold = 13
            elif 55 <= entry_rsi < 60:
                threshold = 7
            elif 60 <= entry_rsi < 65:
                threshold = 2.5
            elif 65 <= entry_rsi < 70:
                threshold = 1
            else:  # entry_rsi >= 70
                threshold = 1
        
        if rsi_difference >= threshold:
            logger.log_position_exit_conditions(position_type, current_rsi, entry_rsi, hours_elapsed, f"Exit principal: RSI monté de {rsi_difference:.2f} points (seuil: {threshold})")
            return {
                'action': 'exit_long',
                'reason': f'Exit principal: RSI monté de {rsi_difference:.2f} points (seuil: {threshold})',
                'position': position,
                'exit_type': 'target'
            }
    
    # Exit de dernier recours: VI1 repasse au-dessus du close
    if analysis['vi1_above_close']:
        logger.log_position_exit_conditions(position_type, current_rsi, entry_rsi, hours_elapsed, "VI1 repasse au-dessus du close")
        return {
            'action': 'exit_long',
            'reason': 'VI1 repasse au-dessus du close',
            'position': position,
            'exit_type': 'last_resort'
            }
    
    # Aucune condition de sortie remplie
    return {
        'action': 'hold',
        'reason': f'Position {position_type} maintenue',
        'position': position,
        'hours_elapsed': hours_elapsed
    }

def check_entry_conditions(analysis, conditions_check, account_summary, state_manager):
    """
    Vérifie les conditions d'entrée pour ouvrir de nouvelles positions.
    """
    
    # Récupérer les informations d'état
    last_position_type = None
    vi1_phase_timestamp = None
    if state_manager:
        last_position_type = state_manager.get_last_position_type()
        vi1_phase_timestamp = state_manager.get_vi1_phase_timestamp()
    
    # Priorité des stratégies (SHORT > LONG_VI1 > LONG_VI2 > LONG_REENTRY)
    if conditions_check['short_ready']:
        return {
            'action': 'enter_short',
            'reason': 'Conditions SHORT remplies',
            'size': account_summary['max_position_size']['max_btc_size'],
            'entry_price': float(analysis['current_candle']['close']),
            'entry_rsi': analysis['indicators']['rsi'],
            'position_type': 'SHORT',
            'entry_time': time.time()
        }
    
    if conditions_check['long_vi1_ready']:
        return {
            'action': 'enter_long_vi1',
            'reason': 'Conditions LONG_VI1 remplies',
            'size': account_summary['max_position_size']['max_btc_size'],
            'entry_price': float(analysis['current_candle']['close']),
            'entry_rsi': analysis['rsi'],
            'position_type': 'LONG_VI1',
            'entry_time': time.time()
        }
    
    if conditions_check['long_vi2_ready']:
        return {
            'action': 'enter_long_vi2',
            'reason': 'Conditions LONG_VI2 remplies',
            'size': account_summary['max_position_size']['max_btc_size'],
            'entry_price': float(analysis['current_candle']['close']),
            'entry_rsi': analysis['rsi'],
            'position_type': 'LONG_VI2',
            'entry_time': time.time()
        }
    
    if conditions_check['long_reentry_ready']:
        return {
            'action': 'enter_long_reentry',
            'reason': 'Conditions LONG_REENTRY remplies',
            'size': account_summary['max_position_size']['max_btc_size'],
            'entry_price': float(analysis['current_candle']['close']),
            'entry_rsi': analysis['rsi'],
            'position_type': 'LONG_REENTRY',
            'entry_time': time.time()
        }
    
    # Aucune condition d'entrée remplie
    return {
        'action': 'hold',
        'reason': 'Aucune stratégie prête',
        'details': {
            'short_ready': conditions_check['short_ready'],
            'long_vi1_ready': conditions_check['long_vi1_ready'],
            'long_vi2_ready': conditions_check['long_vi2_ready'],
            'long_reentry_ready': conditions_check['long_reentry_ready']
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
        if 'hours_elapsed' in decision:
            summary.append(f"      Temps écoulé: {decision['hours_elapsed']:.1f}h")
    elif action.startswith('enter_'):
        strategy = action.replace('enter_', '').upper()
        summary.append(f"   🟢 OUVERTURE {strategy}")
        summary.append(f"      Raison: {reason}")
        summary.append(f"      Taille: {decision['size']:.4f} BTC")
        summary.append(f"      Prix: ${decision['entry_price']:.2f}")
        summary.append(f"      RSI: {decision['entry_rsi']:.2f}")
        summary.append(f"      Type: {decision['position_type']}")
    elif action.startswith('exit_'):
        side = action.replace('exit_', '').upper()
        summary.append(f"   🔴 FERMETURE {side}")
        summary.append(f"      Raison: {reason}")
        summary.append(f"      Type: {decision.get('exit_type', 'unknown')}")
        if 'pnl_pct' in decision:
            summary.append(f"      PnL: {decision['pnl_pct']:.2f}%")
        if 'hours_elapsed' in decision:
            summary.append(f"      Temps écoulé: {decision['hours_elapsed']:.1f}h")
    
    return "\n".join(summary)

# Test du module
if __name__ == "__main__":
    # Test avec des données fictives
    test_analysis = {
        'rsi_n1': 55.0,
        'rsi_n2': 50.0,
        'close_n1': 40000,
        'vi1_n1': 40200,
        'vi2_n1': 40150,
        'vi3_n1': 40100,
        'vi1_above_close': True,
        'vi2_above_close': True,
        'vi3_above_close': True
    }
    
    test_conditions = {
        'trading_allowed': True,
        'short_ready': True,
        'long_vi1_ready': False,
        'long_vi2_ready': False,
        'long_reentry_ready': False
    }
    
    test_account = {
        'has_open_position': False,
        'max_position_size': {'max_btc_size': 0.001}
    }
    
    decision = decide_action(test_analysis, test_conditions, test_account)
    summary = get_decision_summary(decision)
    
    print(summary) 