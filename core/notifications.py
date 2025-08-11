"""
Module de notifications email via Brevo
Gère l'envoi d'emails pour les trades et les pannes système
"""

import requests
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BrevoNotifier:
    def __init__(self):
        """Initialise le notificateur Brevo avec les variables d'environnement."""
        self.api_key = os.getenv('BREVO_API_KEY')
        self.sender_email = os.getenv('BREVO_SENDER_EMAIL')
        self.receiver_email = os.getenv('BREVO_RECEIVER_EMAIL')
        
        if not self.api_key:
            logger.warning("BREVO_API_KEY non trouvée - notifications désactivées")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Notifications Brevo activées")
    
    def send_email(self, subject, html_content):
        """
        Envoie un email via l'API Brevo.
        
        :param subject: Sujet de l'email
        :param html_content: Contenu HTML de l'email
        :return: True si succès, False sinon
        """
        if not self.enabled:
            logger.warning("Notifications désactivées - email non envoyé")
            return False
        
        url = "https://api.brevo.com/v3/smtp/email"
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": self.api_key
        }
        
        payload = {
            "sender": {
                "name": "BitSniper Bot",
                "email": self.sender_email
            },
            "to": [
                {
                    "email": self.receiver_email,
                    "name": "Hugo"
                }
            ],
            "subject": subject,
            "htmlContent": html_content
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 201:
                logger.info(f"Email envoyé avec succès: {subject}")
                return True
            else:
                logger.error(f"Erreur envoi email: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi d'email: {e}")
            return False
    
    def send_trade_notification(self, action, position_type, price=None, datetime_str=None, size=None, pnl=None):
        """
        Envoie une notification de trade enrichie.
        
        :param action: 'ENTRÉE', 'SORTIE', 'SORTIE D\'URGENCE', 'SORTIE CONTRÔLE 3H'
        :param position_type: Type de position (SHORT, LONG_VI1, etc.)
        :param price: Prix d'entrée/sortie (optionnel)
        :param datetime_str: Date/heure (optionnel)
        :param size: Taille de la position (optionnel)
        :param pnl: Profit/Loss réalisé (optionnel)
        """
        if not datetime_str:
            datetime_str = datetime.now().strftime("%d/%m %H:%M")
        
        # Déterminer la couleur et l'icône selon l'action
        if "ENTRÉE" in action:
            color = "#28a745"  # Vert
            icon = "🚀"
        elif "CROISEMENT VI1" in action:
            if "BEARISH" in position_type:
                color = "#dc3545"  # Rouge pour BEARISH
                icon = "📈"
            else:  # BULLISH
                color = "#28a745"  # Vert pour BULLISH
                icon = "📉"
        elif "SORTIE D'URGENCE" in action:
            color = "#dc3545"  # Rouge
            icon = "🚨"
        elif "SORTIE CONTRÔLE" in action:
            color = "#ffc107"  # Jaune
            icon = "⚠️"
        else:  # SORTIE normale
            color = "#17a2b8"  # Bleu
            icon = "📉"
        
        subject = f"BitSniper - {action} {position_type} - {datetime_str}"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, {color}, #6c757d); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; text-align: center;">{icon} BitSniper Trading Bot</h1>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 10px 10px; border: 1px solid #dee2e6;">
                <h2 style="color: {color}; margin-top: 0;">{action} {position_type}</h2>
                
                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid {color};">
                    <p style="margin: 5px 0;"><strong>📅 Date/Heure:</strong> {datetime_str}</p>
                    <p style="margin: 5px 0;"><strong>🎯 Type:</strong> {position_type}</p>
        """
        
        if price and price != 'N/A':
            html_content += f'<p style="margin: 5px 0;"><strong>💰 Prix:</strong> {price}</p>'
        
        if size:
            html_content += f'<p style="margin: 5px 0;"><strong>📊 Taille:</strong> {size:.4f} BTC</p>'
        
        if pnl is not None and pnl != 0:
            pnl_color = "#28a745" if pnl > 0 else "#dc3545"
            pnl_icon = "📈" if pnl > 0 else "📉"
            html_content += f'<p style="margin: 5px 0;"><strong>{pnl_icon} PnL:</strong> <span style="color: {pnl_color}; font-weight: bold;">${pnl:.2f}</span></p>'
        
        html_content += f"""
                </div>
                
                <div style="text-align: center; margin-top: 20px; padding: 15px; background: #e9ecef; border-radius: 8px;">
                    <p style="margin: 0; color: #6c757d; font-style: italic;">
                        🤖 Notification automatique du bot de trading<br>
                        <small>Stratégie RSI(40) + Volatility Indexes sur Kraken Futures</small>
                    </p>
                </div>
            </div>
        </div>
        """
        
        return self.send_email(subject, html_content)
    
    def send_system_notification(self, event, details=None):
        """
        Envoie une notification système (panne/rétablissement).
        
        :param event: Type d'événement ('PANNE', 'RÉTABLI', etc.)
        :param details: Détails supplémentaires (optionnel)
        """
        datetime_str = datetime.now().strftime("%d/%m %H:%M")
        subject = f"BitSniper - {event} - {datetime_str}"
        
        html_content = f"""
        <h2>BitSniper Trading Bot</h2>
        <h3>{event}</h3>
        <p><strong>Date/Heure:</strong> {datetime_str}</p>
        """
        
        if details:
            html_content += f"<p><strong>Détails:</strong> {details}</p>"
        
        html_content += """
        <p><em>Notification automatique du système</em></p>
        """
        
        return self.send_email(subject, html_content)

# Instance globale du notificateur
notifier = BrevoNotifier() 