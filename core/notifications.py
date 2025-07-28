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
    
    def send_trade_notification(self, action, position_type, price=None, datetime_str=None):
        """
        Envoie une notification de trade.
        
        :param action: 'ENTRÉE' ou 'SORTIE'
        :param position_type: Type de position (SHORT, LONG_VI1, etc.)
        :param price: Prix d'entrée/sortie (optionnel)
        :param datetime_str: Date/heure (optionnel)
        """
        if not datetime_str:
            datetime_str = datetime.now().strftime("%d/%m %H:%M")
        
        subject = f"BitSniper - {action} {position_type} - {datetime_str}"
        
        html_content = f"""
        <h2>BitSniper Trading Bot</h2>
        <h3>{action} {position_type}</h3>
        <p><strong>Date/Heure:</strong> {datetime_str}</p>
        """
        
        if price:
            html_content += f"<p><strong>Prix:</strong> {price}</p>"
        
        html_content += """
        <p><em>Notification automatique du bot de trading</em></p>
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