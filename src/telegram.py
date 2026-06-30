# src/telegram.py

'''
Алерты
Закрывает требование FR-05. 
Используем чистый requests — для простой отправки текста этого более чем достаточно, 
тащить тяжелые асинхронные библиотеки ботов в фоновую службу не нужно.
'''

import requests
import logging

logger = logging.getLogger(__name__)

class TelegramAlerts:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_alert(self, bunker_id: str, level: int):
        """Отправляет уведомление, если бункер пуст или переполнен."""
        if level <= 5:
            msg = f"⚠️ ВНИМАНИЕ: Бункер {bunker_id} почти ПУСТ ({level}%)!"
        elif level >= 95:
            msg = f"🚨 КРИТИЧНО: Бункер {bunker_id} ПЕРЕПОЛНЕН ({level}%)!"
        else:
            return # Нормальный уровень, алерт не нужен

        try:
            payload = {"chat_id": self.chat_id, "text": msg}
            requests.post(self.api_url, json=payload, timeout=5)
            logger.info(f"Telegram alert sent for {bunker_id}")
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram alert: {e}")