# src/model.py  
'''
Обертка для YOLO
Скрипт загружает веса, прогоняет кадр и возвращает предсказанный класс и уровень уверенности.
'''

import logging
from ultralytics import YOLO


logger = logging.getLogger(__name__)

class BunkerModel:
    def __init__(self, weights_path: str):
        """Инициализация модели YOLO-cls. Модель грузится в память один раз при старте службы."""
        try:
            self.model = YOLO(weights_path)
            logger.info(f"Model loaded successfully from {weights_path}")
        except Exception as e:
            logger.critical(f"Failed to load model: {e}")
            raise

    def predict(self, frame) -> tuple[int, float]:
        """
        Прогоняет кадр через нейросеть.
        Возвращает: (уровень_в_процентах, уверенность)
        """
        try:
            # verbose=False отключает спам в консоль при каждом инференсе
            results = self.model(frame, verbose=False)[0]
            
            top1_index = results.probs.top1
            confidence = results.probs.top1conf.item()
            predicted_class = int(results.names[top1_index])
            
            return predicted_class, confidence
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return -1, 0.0