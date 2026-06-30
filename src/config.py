import json
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

@dataclass
class CameraConfig:
    bunker_id: str
    rtsp_url: str
    roi_ratio: Optional[Tuple[float, float, float, float]] = (0.0, 0.0, 0.55, 1.0)

@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str

@dataclass
class AppConfig:
    cameras: List[CameraConfig] = field(default_factory=list)
    erp_url: str = ""
    telegram: TelegramConfig = field(default_factory=lambda: TelegramConfig("", ""))
    db_path: str = "sqlite:///data/bunker_buffer.db"
    model_path: str = "runs/models/bunker_poc/weights/best.pt"
    poll_interval_minutes: int = 30

    @classmethod
    def load(cls, path: str = "cameras_config.json") -> "AppConfig":
        """Загружает и валидирует конфигурацию из JSON."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        cameras = [CameraConfig(**cam) for cam in data.get("cameras", [])]
        tg_data = data.get("telegram", {})
        
        return cls(
            cameras=cameras,
            erp_url=data.get("erp_url", ""),
            telegram=TelegramConfig(
                bot_token=tg_data.get("bot_token", ""),
                chat_id=tg_data.get("chat_id", "")
            ),
            db_path=data.get("db_path", "sqlite:///data/bunker_buffer.db"),
            model_path=data.get("model_path", "runs/models/bunker_poc/weights/best.pt"),
            poll_interval_minutes=data.get("poll_interval_minutes", 30)
        )