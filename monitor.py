# monitor.py

'''
Оркестратор и точка входа службы
Этот файл связывает всё воедино. 
Используем APScheduler для запуска задачи каждые 30 минут, как просят в FR-01.
'''

import sys
import json
import logging
from apscheduler.schedulers.blocking import BlockingScheduler

from src.db import DBManager
from src.sender import ERPSender
from src.model import BunkerModel
from src.capture import CameraCapture
from src.telegram import TelegramAlerts

# Настройка промышленного логирования (FR-07)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bunker_vision.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Monitor")

# 1. Загрузка конфигурации
def load_config():
    with open("cameras_config.json", "r") as f:
        return json.load(f)

CONFIG = load_config()

# 2. Инициализация модулей
db = DBManager("sqlite:///data/bunker_buffer.db")
sender = ERPSender(CONFIG["erp_url"], db)
model = BunkerModel("runs/models/bunker_poc/weights/best.pt")
tg_alerts = TelegramAlerts(CONFIG["telegram"]["bot_token"], CONFIG["telegram"]["chat_id"])

def job_pipeline():
    """Основной пайплайн, запускаемый по расписанию"""
    logger.info("--- Starting monitoring cycle ---")
    
    # Шаг 1: Опрос камер и инференс
    for cam in CONFIG["cameras"]:
        bunker_id = cam["bunker_id"]
        rtsp_url = cam["rtsp_url"]
        
        # Получаем кадр (FR-01, FR-08)
        frame = CameraCapture.get_frame(rtsp_url, cam.get("roi_ratio", 0.55))
        if frame is None:
            continue
            
        # Инференс (FR-02)
        level, confidence = model.predict(frame)
        
        if level != -1:
            # Сохранение в локальный буфер (FR-03)
            db.add_measurement(bunker_id, level, confidence)
            # Отправка алертов (FR-05)
            tg_alerts.send_alert(bunker_id, level)

    # Шаг 2: Выгрузка накопленных данных в 1С (FR-04)
    logger.info("Pushing data to ERP...")
    sender.process_unsent_data()
    logger.info("--- Cycle completed ---")

if __name__ == "__main__":
    logger.info("BunkerVision Service Started.")
    
    # Для теста прогоняем один раз сразу
    job_pipeline()
    
    # Настраиваем планировщик на запуск каждые 30 минут (FR-01)
    scheduler = BlockingScheduler()
    scheduler.add_job(job_pipeline, 'interval', minutes=30)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("BunkerVision Service Stopped.")