import logging
from datetime import datetime
from typing import List
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logger = logging.getLogger(__name__)
Base = declarative_base()

class Measurement(Base):
    __tablename__ = 'measurements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    bunker_id = Column(String, index=True, nullable=False)
    level = Column(Integer, nullable=False)  # Уровень: 0, 25, 50, 75, 100
    confidence = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_sent = Column(Boolean, default=False, index=True, nullable=False)

class DBManager:
    def __init__(self, db_url: str = "sqlite:///data/bunker_buffer.db"):
        # check_same_thread=False необходим для APScheduler
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        logger.info(f"Database initialized at {db_url}")

    @contextmanager
    def get_session(self) -> Session:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Database session error")
            raise
        finally:
            session.close()

    def add_measurement(self, bunker_id: str, level: int, confidence: float) -> None:
        with self.get_session() as session:
            new_record = Measurement(bunker_id=bunker_id, level=level, confidence=confidence)
            session.add(new_record)
            logger.debug(f"Saved to DB: {bunker_id} - {level}% (conf: {confidence:.2f})")

    def get_unsent_measurements(self) -> List[Measurement]:
        with self.get_session() as session:
            records = session.query(Measurement).filter(Measurement.is_sent == False).all()
            for rec in records:
                session.expunge(rec)  # Отвязываем от сессии для безопасного использования вне контекста
            return records

    def mark_as_sent(self, measurement_ids: List[int]) -> None:
        if not measurement_ids:
            return
        with self.get_session() as session:
            session.query(Measurement).filter(Measurement.id.in_(measurement_ids)).update(
                {"is_sent": True}, synchronize_session=False
            )
            logger.info(f"Marked {len(measurement_ids)} records as sent to ERP.")