import sys
import logging
from apscheduler.schedulers.blocking import BlockingScheduler

from config import AppConfig
from db import DBManager
from sender import ERPSender
from model import BunkerModel  # Предполагается, что model.py существует
from capture import CameraCapture
from telegram import TelegramAlerts

# Настройка логирования (в файл и консоль)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bunker_vision.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Monitor")

class BunkerVisionPipeline:
    def __init__(self, config: AppConfig):
        self.config = config
        self.db = DBManager(config.db_path)
        self.sender = ERPSender(config.erp_url, self.db)
        self.model = BunkerModel(config.model_path)
        self.tg_alerts = TelegramAlerts(config.telegram.bot_token, config.telegram.chat_id)

    def run_cycle(self):
        """Основной пайплайн, запускаемый по расписанию"""
        logger.info("- Starting monitoring cycle -")

        # Шаг 1: Опрос камер и инференс
        for cam in self.config.cameras:
            bunker_id = cam.bunker_id
            rtsp_url = cam.rtsp_url
            
            frame = CameraCapture.get_frame(rtsp_url, cam.roi_ratio)
            if frame is None:
                logger.warning(f"Skipping bunker {bunker_id} due to capture failure.")
                continue

            level, confidence = self.model.predict(frame)
            
            if level != -1:
                self.db.add_measurement(bunker_id, level, confidence)
                self.tg_alerts.send_alert(bunker_id, level)

        # Шаг 2: Выгрузка накопленных данных в 1С (ERP)
        logger.info("Pushing data to ERP...")
        self.sender.process_unsent_data()
        
        logger.info("- Cycle completed -")

def main():
    logger.info("BunkerVision Service Starting...")
    
    try:
        config = AppConfig.load("cameras_config.json")
    except Exception as e:
        logger.critical(f"Failed to load configuration: {e}")
        sys.exit(1)

    pipeline = BunkerVisionPipeline(config)
    
    # Для теста прогоняем один раз сразу
    pipeline.run_cycle()

    # Настраиваем планировщик APScheduler
    scheduler = BlockingScheduler()
    scheduler.add_job(pipeline.run_cycle, 'interval', minutes=config.poll_interval_minutes)
    
    logger.info(f"Scheduler started. Interval: {config.poll_interval_minutes} mins.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("BunkerVision Service Stopped.")

if __name__ == "__main__":
    main()