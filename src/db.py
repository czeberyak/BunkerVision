import logging
from datetime import datetime
from typing import List

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# Настройка логгера
logger = logging.getLogger(__name__)

Base = declarative_base()

class Measurement(Base):
    """
    Модель данных для хранения результатов замеров.
    """
    __tablename__ = 'measurements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    bunker_id = Column(String, index=True, nullable=False)
    level = Column(Integer, nullable=False)          # Уровень в процентах (0, 25, 50, 75, 100)
    confidence = Column(Float, nullable=False)       # Уверенность модели (0.0 - 1.0)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_sent = Column(Boolean, default=False, index=True, nullable=False) # Флаг отправки в ERP

class DBManager:
    def __init__(self, db_path: str = "sqlite:///bunker_buffer.db"):
        """
        Инициализация подключения к БД.
        check_same_thread=False нужен для работы SQLite в многопоточной среде (например, с APScheduler).
        """
        self.engine = create_engine(db_path, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_measurement(self, bunker_id: str, level: int, confidence: float) -> None:
        """Сохраняет новый замер в базу."""
        with self.Session() as session:
            new_record = Measurement(
                bunker_id=bunker_id, 
                level=level, 
                confidence=confidence
            )
            session.add(new_record)
            session.commit()
            logger.debug(f"Saved to DB: {bunker_id} - {level}% (conf: {confidence:.2f})")

    def get_unsent_measurements(self) -> List[Measurement]:
        """Возвращает список всех неотправленных замеров."""
        with self.Session() as session:
            # Возвращаем объекты, отвязанные от сессии, чтобы с ними было удобно работать
            records = session.query(Measurement).filter(Measurement.is_sent == False).all()
            session.expunge_all()
            return records

    def mark_as_sent(self, measurement_ids: List[int]) -> None:
        """Помечает замеры как успешно отправленные."""
        if not measurement_ids:
            return
            
        with self.Session() as session:
            session.query(Measurement).filter(Measurement.id.in_(measurement_ids)).update(
                {"is_sent": True}, synchronize_session=False
            )
            session.commit()
            logger.info(f"Marked {len(measurement_ids)} records as sent.")