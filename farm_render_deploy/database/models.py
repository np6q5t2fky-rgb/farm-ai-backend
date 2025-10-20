"""
Моделі бази даних для системи обліку свиноферми
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# База для моделей
Base = declarative_base()

# URL бази даних з .env або за замовчуванням
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./farm.db")

# Створення двигуна бази даних
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Сесія для роботи з БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Sow(Base):
    """
    Модель свиноматки
    """
    __tablename__ = "sows"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, nullable=False, index=True)  # Номер свиноматки
    birth_date = Column(Date, nullable=False)  # Дата народження
    status = Column(String(20), default="активна")  # Статус: активна, вибракувана
    notes = Column(Text, nullable=True)  # Примітки
    created_at = Column(DateTime, default=datetime.utcnow)  # Дата створення запису
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Дата оновлення

    def to_dict(self):
        """Перетворення об'єкта в словник"""
        return {
            "id": self.id,
            "number": self.number,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WeeklyRecord(Base):
    """
    Модель тижневого обліку опоросів
    """
    __tablename__ = "weekly_records"
    
    id = Column(Integer, primary_key=True, index=True)
    week_start_date = Column(Date, nullable=False, unique=True, index=True)  # Дата початку тижня
    farrowings = Column(Integer, default=0)  # Кількість опоросів
    piglets_born_alive = Column(Integer, default=0)  # Живих поросят народилось
    piglets_born_dead = Column(Integer, default=0)  # Мертвих поросят
    survival_rate = Column(Float, default=0.0)  # Відсоток виживаності
    notes = Column(Text, nullable=True)  # Примітки
    created_at = Column(DateTime, default=datetime.utcnow)  # Дата створення запису
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Дата оновлення

    def calculate_survival_rate(self):
        """Розрахунок відсотка виживаності"""
        total_born = self.piglets_born_alive + self.piglets_born_dead
        if total_born > 0:
            self.survival_rate = (self.piglets_born_alive / total_born) * 100
        else:
            self.survival_rate = 0.0

    def to_dict(self):
        """Перетворення об'єкта в словник"""
        return {
            "id": self.id,
            "week_start_date": self.week_start_date.isoformat() if self.week_start_date else None,
            "farrowings": self.farrowings,
            "piglets_born_alive": self.piglets_born_alive,
            "piglets_born_dead": self.piglets_born_dead,
            "survival_rate": round(self.survival_rate, 2),
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def get_db():
    """
    Отримання сесії бази даних
    Використовується як dependency в FastAPI
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Створення всіх таблиць в базі даних
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Таблиці бази даних створено успішно!")
