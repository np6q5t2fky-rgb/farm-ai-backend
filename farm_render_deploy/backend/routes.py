"""
API маршрути та бізнес-логіка для системи обліку свиноферми
"""

from fastapi import UploadFile, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime
import pandas as pd
import google.generativeai as genai
import os
import sys
from dotenv import load_dotenv

# Додаємо шлях до database модуля
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.models import WeeklyRecord, Sow

# Завантаження змінних середовища
load_dotenv()

# Налаштування Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None
    print("⚠️  GEMINI_API_KEY не знайдено. AI чат не буде працювати.")


# ============ PYDANTIC СХЕМИ ============

class WeeklyRecordCreate(BaseModel):
    """Схема для створення тижневого запису"""
    week_start_date: date
    farrowings: int = Field(ge=0, description="Кількість опоросів")
    piglets_born_alive: int = Field(ge=0, description="Живих поросят")
    piglets_born_dead: int = Field(ge=0, description="Мертвих поросят")
    notes: Optional[str] = None


class WeeklyRecordUpdate(BaseModel):
    """Схема для оновлення тижневого запису"""
    week_start_date: Optional[date] = None
    farrowings: Optional[int] = Field(None, ge=0)
    piglets_born_alive: Optional[int] = Field(None, ge=0)
    piglets_born_dead: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class SowCreate(BaseModel):
    """Схема для створення свиноматки"""
    number: str = Field(..., min_length=1, description="Номер свиноматки")
    birth_date: date
    status: str = Field(default="активна", pattern="^(активна|вибракувана)$")
    notes: Optional[str] = None


class SowUpdate(BaseModel):
    """Схема для оновлення свиноматки"""
    number: Optional[str] = Field(None, min_length=1)
    birth_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(активна|вибракувана)$")
    notes: Optional[str] = None


class ChatRequest(BaseModel):
    """Схема для запиту до AI чату"""
    message: str = Field(..., min_length=1, description="Повідомлення користувача")
    include_context: bool = Field(default=True, description="Включити контекст даних")


# ============ WEEKLY RECORDS ФУНКЦІЇ ============

async def get_weekly_records(db: Session) -> List[dict]:
    """
    Отримання всіх тижневих записів
    """
    records = db.query(WeeklyRecord).order_by(WeeklyRecord.week_start_date.desc()).all()
    return [record.to_dict() for record in records]


async def create_weekly_record(record: WeeklyRecordCreate, db: Session) -> dict:
    """
    Створення нового тижневого запису
    """
    # Перевірка чи існує запис на цю дату
    existing = db.query(WeeklyRecord).filter(
        WeeklyRecord.week_start_date == record.week_start_date
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Запис для тижня {record.week_start_date} вже існує"
        )
    
    # Створення нового запису
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


async def update_weekly_record(record_id: int, record: WeeklyRecordUpdate, db: Session) -> dict:
    """
    Оновлення існуючого тижневого запису
    """
    db_record = db.query(WeeklyRecord).filter(WeeklyRecord.id == record_id).first()
    
    if not db_record:
        raise HTTPException(status_code=404, detail="Запис не знайдено")
    
    # Оновлення полів
    update_data = record.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_record, field, value)
    
    # Перерахунок виживаності
    db_record.calculate_survival_rate()
    db_record.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_record)
    
    return db_record.to_dict()


async def delete_weekly_record(record_id: int, db: Session) -> dict:
    """
    Видалення тижневого запису
    """
    db_record = db.query(WeeklyRecord).filter(WeeklyRecord.id == record_id).first()
    
    if not db_record:
        raise HTTPException(status_code=404, detail="Запис не знайдено")
    
    db.delete(db_record)
    db.commit()
    
    return {"message": "Запис успішно видалено", "id": record_id}


# ============ SOWS ФУНКЦІЇ ============

async def get_sows(db: Session) -> List[dict]:
    """
    Отримання всіх свиноматок
    """
    sows = db.query(Sow).order_by(Sow.number).all()
    return [sow.to_dict() for sow in sows]


async def create_sow(sow: SowCreate, db: Session) -> dict:
    """
    Додавання нової свиноматки
    """
    # Перевірка чи існує свиноматка з таким номером
    existing = db.query(Sow).filter(Sow.number == sow.number).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Свиноматка з номером {sow.number} вже існує"
        )
    
    # Створення нової свиноматки
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


async def update_sow(sow_id: int, sow: SowUpdate, db: Session) -> dict:
    """
    Оновлення даних свиноматки
    """
    db_sow = db.query(Sow).filter(Sow.id == sow_id).first()
    
    if not db_sow:
        raise HTTPException(status_code=404, detail="Свиноматку не знайдено")
    
    # Перевірка унікальності номера (якщо він змінюється)
    if sow.number and sow.number != db_sow.number:
        existing = db.query(Sow).filter(Sow.number == sow.number).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Свиноматка з номером {sow.number} вже існує"
            )
    
    # Оновлення полів
    update_data = sow.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_sow, field, value)
    
    db_sow.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_sow)
    
    return db_sow.to_dict()


async def delete_sow(sow_id: int, db: Session) -> dict:
    """
    Видалення свиноматки
    """
    db_sow = db.query(Sow).filter(Sow.id == sow_id).first()
    
    if not db_sow:
        raise HTTPException(status_code=404, detail="Свиноматку не знайдено")
    
    db.delete(db_sow)
    db.commit()
    
    return {"message": "Свиноматку успішно видалено", "id": sow_id}


# ============ IMPORT ФУНКЦІЯ ============

async def import_excel(file: UploadFile, data_type: str, db: Session) -> dict:
    """
    Імпорт даних з Excel файлу
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Файл повинен бути в форматі Excel (.xlsx або .xls)"
        )
    
    try:
        # Читання Excel файлу
        contents = await file.read()
        df = pd.read_excel(contents)
        
        imported_count = 0
        errors = []
        
        if data_type == "weekly":
            # Імпорт тижневих записів
            required_columns = ['Дата', 'Опороси', 'Живих', 'Мертвих']
            
            for index, row in df.iterrows():
                try:
                    week_date = pd.to_datetime(row['Дата']).date()
                    
                    # Перевірка чи існує запис
                    existing = db.query(WeeklyRecord).filter(
                        WeeklyRecord.week_start_date == week_date
                    ).first()
                    
                    if existing:
                        # Оновлення існуючого
                        existing.farrowings = int(row['Опороси'])
                        existing.piglets_born_alive = int(row['Живих'])
                        existing.piglets_born_dead = int(row['Мертвих'])
                        existing.notes = str(row.get('Примітки', '')) if pd.notna(row.get('Примітки')) else None
                        existing.calculate_survival_rate()
                        existing.updated_at = datetime.utcnow()
                    else:
                        # Створення нового
                        record = WeeklyRecord(
                            week_start_date=week_date,
                            farrowings=int(row['Опороси']),
                            piglets_born_alive=int(row['Живих']),
                            piglets_born_dead=int(row['Мертвих']),
                            notes=str(row.get('Примітки', '')) if pd.notna(row.get('Примітки')) else None
                        )
                        record.calculate_survival_rate()
                        db.add(record)
                    
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Рядок {index + 2}: {str(e)}")
        
        elif data_type == "sows":
            # Імпорт свиноматок
            required_columns = ['Номер', 'Дата народження', 'Статус']
            
            for index, row in df.iterrows():
                try:
                    number = str(row['Номер'])
                    birth_date = pd.to_datetime(row['Дата народження']).date()
                    status = str(row['Статус']).lower()
                    
                    # Перевірка чи існує свиноматка
                    existing = db.query(Sow).filter(Sow.number == number).first()
                    
                    if existing:
                        # Оновлення існуючої
                        existing.birth_date = birth_date
                        existing.status = status
                        existing.notes = str(row.get('Примітки', '')) if pd.notna(row.get('Примітки')) else None
                        existing.updated_at = datetime.utcnow()
                    else:
                        # Створення нової
                        sow = Sow(
                            number=number,
                            birth_date=birth_date,
                            status=status,
                            notes=str(row.get('Примітки', '')) if pd.notna(row.get('Примітки')) else None
                        )
                        db.add(sow)
                    
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Рядок {index + 2}: {str(e)}")
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Невірний тип даних. Використовуйте 'weekly' або 'sows'"
            )
        
        db.commit()
        
        return {
            "message": f"Імпорт завершено успішно!",
            "imported": imported_count,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Помилка імпорту: {str(e)}"
        )


# ============ AI CHAT ФУНКЦІЯ ============

async def chat_with_ai(request: ChatRequest, db: Session) -> dict:
    """
    Чат з AI асистентом (з даними з БД та Excel файлів)
    """
    if not model:
        raise HTTPException(
            status_code=503,
            detail="AI сервіс недоступний. Перевірте GEMINI_API_KEY в .env файлі"
        )
    
    try:
        # Імпорт модуля для читання Excel
        from backend.excel_reader import get_excel_context_for_ai
        
        # Підготовка контексту з даними
        context = ""
        
        if request.include_context:
            # 1. ДАНІ З БАЗИ ДАНИХ (SQLite)
            recent_records = db.query(WeeklyRecord).order_by(
                WeeklyRecord.week_start_date.desc()
            ).limit(10).all()
            
            active_sows = db.query(Sow).filter(Sow.status == "активна").count()
            total_sows = db.query(Sow).count()
            
            # Формування контексту з БД
            context = f"""
📊 ДАНІ З БАЗИ ДАНИХ (farm.db):

Свиноматки в БД:
- Всього: {total_sows}
- Активних: {active_sows}
- Вибракуваних: {total_sows - active_sows}

Останні тижневі записи в БД:
"""
            for record in recent_records:
                total_born = record.piglets_born_alive + record.piglets_born_dead
                context += f"\n- Тиждень {record.week_start_date}: {record.farrowings} опоросів, {total_born} поросят (виживаність: {record.survival_rate:.1f}%)"
            
            # 2. ДАНІ З EXCEL ФАЙЛІВ
            excel_context = get_excel_context_for_ai()
            context += f"\n\n{excel_context}\n\n"
        
        # Системний промпт
        system_prompt = """Ти - експертний AI асистент для управління свинофермою. 
Твоя роль - аналізувати дані з бази даних та Excel файлів (farm.xlsx, облік свиноматок.xlsx), 
давати практичні рекомендації та відповідати на питання фермерів українською мовою.

У тебе є доступ до двох джерел даних:
1. База даних (farm.db) - оперативні дані, які вводить користувач через веб-інтерфейс
2. Excel файли - детальний облік осіменіння, тестів на вагітність, планування опоросів

Будь конкретним, професійним та корисним. Використовуй надані дані для точних відповідей.
Якщо бачиш розбіжності між БД та Excel - поясни це користувачу.
Надавай рекомендації на основі показників виживаності, відсотка перегулу, кількості опоросів."""
        
        # Генерація відповіді
        full_prompt = f"{system_prompt}\n\n{context}Питання користувача: {request.message}"
        
        response = model.generate_content(full_prompt)
        
        return {
            "response": response.text,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Помилка AI: {str(e)}"
        )
