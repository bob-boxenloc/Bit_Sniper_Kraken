import requests
import json
import os
from datetime import datetime

def test_brevo_email():
    api_key = os.getenv('BREVO_API_KEY')
    sender_email = os.getenv('BREVO_SENDER_EMAIL')
    receiver_email = os.getenv('BREVO_RECEIVER_EMAIL')
    
    if not api_key:
        print("❌ BREVO_API_KEY non trouvée dans les variables d'environnement")
        return
    
    url = "https://api.brevo.com/v3/smtp/email"
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key
    }
    
    payload = {
        "sender": {
            "name": "BitSniper Bot",
            "email": sender_email
        },
        "to": [
            {
                "email": receiver_email,
                "name": "Hugo"
            }
        ],
        "subject": "Test BitSniper - " + datetime.now().strftime("%d/%m %H:%M"),
        "htmlContent": "<h1>Test BitSniper</h1><p>Si vous recevez cet email, la configuration Brevo fonctionne !</p>"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            print("✅ Email envoyé avec succès !")
            print(f"📧 Vérifiez votre boîte mail {receiver_email}")
        else:
            print(f"❌ Erreur: {response.status_code}")
            print(f"Réponse: {response.text}")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    test_brevo_email() 