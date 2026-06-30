# src/capture.py
'''
Глаза системы
Закрывает требование FR-08 (детекция недоступности камеры). 
Открывает RTSP-поток, забирает один актуальный кадр, применяет ROI и сразу закрывает соединение, 
чтобы не грузить сеть завода.
'''

import cv2
import logging
import numpy as np

logger = logging.getLogger(__name__)

class CameraCapture:
    @staticmethod
    def get_frame(rtsp_url: str, roi_ratio: float = 0.55) -> np.ndarray:
        """
        Подключается к камере, забирает кадр и применяет ROI.
        Возвращает None, если камера недоступна.
        """
        cap = cv2.VideoCapture(rtsp_url)
        
        # Устанавливаем таймаут на случай зависшего RTSP потока
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000) 
        
        ret, frame = cap.read()
        cap.release() # Сразу освобождаем ресурс
        
        if not ret or frame is None:
            logger.warning(f"Failed to capture frame from {rtsp_url}")
            return None
            
        # Применяем жесткий кроп (ROI), как в твоем PoC-ноутбуке
        h, w = frame.shape[:2]
        roi_w = int(w * roi_ratio)
        cropped_frame = frame[:, :roi_w]
        
        return cropped_frame