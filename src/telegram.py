import requests
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class TelegramAlerts:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException),
        silent=True
    )
    def _send_message(self, payload: dict) -> None:
        response = requests.post(self.api_url, json=payload, timeout=5)
        response.raise_for_status()

    def send_alert(self, bunker_id: str, level: int) -> None:
        """Отправляет уведомление, если бункер пуст или переполнен."""
        if level <= 5:
            msg = f"⚠️ ВНИМАНИЕ: Бункер {bunker_id} почти ПУСТ ({level}%)!"
        elif level >= 95:
            msg = f"🚨 КРИТИЧНО: Бункер {bunker_id} ПЕРЕПОЛНЕН ({level}%)!"
        else:
            return  # Нормальный уровень, алерт не нужен

        payload = {"chat_id": self.chat_id, "text": msg}
        try:
            self._send_message(payload)
            logger.info(f"Telegram alert sent for {bunker_id}")
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram alert for {bunker_id} after retries: {e}")