import requests
import logging
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from db import DBManager, Measurement

logger = logging.getLogger(__name__)

class ERPSender:
    def __init__(self, erp_url: str, db_manager: DBManager):
        self.erp_url = erp_url
        self.db = db_manager

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True
    )
    def _send_record(self, payload: dict) -> requests.Response:
        """Отправляет одну запись с exponential backoff."""
        response = requests.post(self.erp_url, json=payload, timeout=5)
        response.raise_for_status()
        return response

    def process_unsent_data(self) -> None:
        """Читает неотправленные данные из БД и пытается отправить их в 1С."""
        unsent_records = self.db.get_unsent_measurements()
        if not unsent_records:
            return

        successful_ids = []
        for record in unsent_records:
            payload = {
                "bunker_id": record.bunker_id,
                "level_pct": record.level,
                "timestamp": record.timestamp.isoformat()
            }
            try:
                self._send_record(payload)
                successful_ids.append(record.id)
            except requests.RequestException as e:
                logger.error(f"Failed to send record {record.id} to ERP after retries: {e}")
                break  # Прерываем цикл, если ERP недоступен, чтобы не долбить сеть

        if successful_ids:
            self.db.mark_as_sent(successful_ids)