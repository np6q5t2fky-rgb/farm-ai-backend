"""
Farm AI Backend - оптимізована версія для Vercel
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, date
from typing import Optional, List
import google.generativeai as genai
import os

# FastAPI додаток
app = FastAPI(
    title="Farm AI Backend",
    description="AI асистент для свиноферми",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# База даних
Base = declarative_base()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./farm.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# AI налаштування
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None

# Моделі
class Sow(Base):
    __tablename__ = "sows"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, nullable=False, index=True)
    birth_date = Column(Date, nullable=False)
    status = Column(String(20), default="активна")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
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
    __tablename__ = "weekly_records"
    
    id = Column(Integer, primary_key=True, index=True)
    week_start_date = Column(Date, nullable=False, unique=True, index=True)
    farrowings = Column(Integer, default=0)
    piglets_born_alive = Column(Integer, default=0)
    piglets_born_dead = Column(Integer, default=0)
    survival_rate = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def calculate_survival_rate(self):
        total_born = self.piglets_born_alive + self.piglets_born_dead
        if total_born > 0:
            self.survival_rate = (self.piglets_born_alive / total_born) * 100
        else:
            self.survival_rate = 0.0

    def to_dict(self):
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

# Pydantic схеми
class WeeklyRecordCreate(BaseModel):
    week_start_date: date
    farrowings: int = Field(ge=0)
    piglets_born_alive: int = Field(ge=0)
    piglets_born_dead: int = Field(ge=0)
    notes: Optional[str] = None

class SowCreate(BaseModel):
    number: str = Field(..., min_length=1)
    birth_date: date
    status: str = Field(default="активна")
    notes: Optional[str] = None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    include_context: bool = Field(default=True)

# База даних залежність
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Створення таблиць
@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    print("✅ FastAPI сервер та БД готові!")

# Endpoints
@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Farm AI Backend працює!",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "ai": "ready" if model else "no_api_key"
    }

@app.get("/api/weekly-records")
async def get_weekly_records(db: Session = Depends(get_db)):
    records = db.query(WeeklyRecord).order_by(WeeklyRecord.week_start_date.desc()).all()
    return [record.to_dict() for record in records]

@app.post("/api/weekly-records")
async def create_weekly_record(record: WeeklyRecordCreate, db: Session = Depends(get_db)):
    existing = db.query(WeeklyRecord).filter(
        WeeklyRecord.week_start_date == record.week_start_date
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Запис для {record.week_start_date} вже існує")
    
    db_record = WeeklyRecord(
        week_start_date=record.week_start_date,
        farrowings=record.farrowings,
        piglets_born_alive=record.piglets_born_alive,
        piglets_born_dead=record.piglets_born_dead,
        notes=record.notes
    )
    db_record.calculate_survival_rate()
    
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    
    return db_record.to_dict()

@app.get("/api/sows")
async def get_sows(db: Session = Depends(get_db)):
    sows = db.query(Sow).order_by(Sow.number).all()
    return [sow.to_dict() for sow in sows]

@app.post("/api/sows")
async def create_sow(sow: SowCreate, db: Session = Depends(get_db)):
    existing = db.query(Sow).filter(Sow.number == sow.number).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Свиноматка {sow.number} вже існує")
    
    db_sow = Sow(
        number=sow.number,
        birth_date=sow.birth_date,
        status=sow.status,
        notes=sow.notes
    )
    
    db.add(db_sow)
    db.commit()
    db.refresh(db_sow)
    
    return db_sow.to_dict()

@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest, db: Session = Depends(get_db)):
    if not model:
        raise HTTPException(status_code=503, detail="AI недоступний. Перевірте GEMINI_API_KEY")
    
    try:
        context = ""
        if request.include_context:
            recent_records = db.query(WeeklyRecord).order_by(
                WeeklyRecord.week_start_date.desc()
            ).limit(5).all()
            
            active_sows = db.query(Sow).filter(Sow.status == "активна").count()
            
            context = f"""
Дані ферми:
- Активних свиноматок: {active_sows}
- Останні записи: {len(recent_records)} тижнів

Останні тижневі дані:
"""
            for record in recent_records:
                context += f"- {record.week_start_date}: {record.farrowings} опоросів, виживаність {record.survival_rate:.1f}%\n"
        
        system_prompt = """Ти - експертний AI асистент для управління свинофермою. 
Аналізуй дані та давай практичні рекомендації українською мовою.
Будь конкретним та корисним."""
        
        full_prompt = f"{system_prompt}\n\n{context}Питання: {request.message}"
        
        response = model.generate_content(full_prompt)
        
        return {
            "response": response.text,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка AI: {str(e)}")

# Для Vercel (ВАЖЛИВО!)
handler = app
