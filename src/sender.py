import requests
import logging
from src.db import DBManager

logger = logging.getLogger(__name__)

class ERPSender:
    def __init__(self, erp_url: str, db_manager: DBManager):
        self.erp_url = erp_url
        self.db = db_manager

    def process_unsent_data(self):
        """
        Читает неотправленные данные из БД и пытается отправить их в учетную систему.
        """
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
                # Таймаут обязателен! Иначе скрипт зависнет, если ERP "лежит"
                response = requests.post(self.erp_url, json=payload, timeout=5)
                
                if response.status_code == 200:
                    successful_ids.append(record.id)
                else:
                    logger.warning(f"ERP returned status {response.status_code} for record {record.id}")
                    
            except requests.RequestException as e:
                logger.error(f"Network error while sending to ERP: {e}")
                break # Прерываем цикл, нет смысла долбить лежащую сеть

        # Помечаем в БД только те, что реально ушли
        if successful_ids:
            self.db.mark_as_sent(successful_ids)