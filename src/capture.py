import cv2
import logging
import numpy as np
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class CameraCapture:
    @staticmethod
    def get_frame(
        rtsp_url: str, 
        roi_bbox: Optional[Tuple[float, float, float, float]] = (0.0, 0.0, 0.55, 1.0)
    ) -> Optional[np.ndarray]:
        """Подключается к камере, забирает кадр и применяет ROI."""
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            logger.error(f"Failed to open RTSP stream: {rtsp_url}")
            return None

        # Аппаратные таймауты OpenCV (5 сек), чтобы не повесить поток
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
        
        ret, frame = cap.read()
        cap.release()  # Сразу освобождаем ресурс

        if not ret or frame is None:
            logger.warning(f"Failed to capture frame from {rtsp_url}")
            return None

        # Применяем универсальный кроп (ROI)
        if roi_bbox is not None:
            x_min, y_min, x_max, y_max = roi_bbox
            h, w = frame.shape[:2]
            
            x1 = max(0, int(w * x_min))
            y1 = max(0, int(h * y_min))
            x2 = min(w, int(w * x_max))
            y2 = min(h, int(h * y_max))

            if x2 > x1 and y2 > y1:
                return frame[y1:y2, x1:x2]
            else:
                logger.warning(f"Invalid ROI coordinates: {roi_bbox}. Returning full frame.")
                
        return frame