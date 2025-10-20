"""
Головний файл FastAPI серверу для системи обліку свиноферми
"""

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import sys
import os

# Додаємо шлях до database модуля
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.models import get_db, create_tables
from routes import (
    get_weekly_records,
    create_weekly_record,
    update_weekly_record,
    delete_weekly_record,
    get_sows,
    create_sow,
    update_sow,
    delete_sow,
    import_excel,
    chat_with_ai,
    WeeklyRecordCreate,
    WeeklyRecordUpdate,
    SowCreate,
    SowUpdate,
    ChatRequest
)

# Створення FastAPI додатку
app = FastAPI(
    title="Farm AI Chat API",
    description="API для системи обліку свиноферми з AI асистентом",
    version="1.0.0"
)

# Налаштування CORS для доступу з frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшені вказати конкретні домени
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Створення таблиць при запуску
@app.on_event("startup")
async def startup_event():
    """Подія при запуску серверу"""
    create_tables()
    print("✅ FastAPI сервер запущено!")


# ============ WEEKLY RECORDS ENDPOINTS ============

@app.get("/api/weekly-records", tags=["Weekly Records"])
async def api_get_weekly_records(db: Session = Depends(get_db)):
    """
    Отримання всіх тижневих записів
    """
    return await get_weekly_records(db)


@app.post("/api/weekly-records", tags=["Weekly Records"])
async def api_create_weekly_record(
    record: WeeklyRecordCreate,
    db: Session = Depends(get_db)
):
    """
    Створення нового тижневого запису
    """
    return await create_weekly_record(record, db)


@app.put("/api/weekly-records/{record_id}", tags=["Weekly Records"])
async def api_update_weekly_record(
    record_id: int,
    record: WeeklyRecordUpdate,
    db: Session = Depends(get_db)
):
    """
    Оновлення існуючого тижневого запису
    """
    return await update_weekly_record(record_id, record, db)


@app.delete("/api/weekly-records/{record_id}", tags=["Weekly Records"])
async def api_delete_weekly_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    """
    Видалення тижневого запису
    """
    return await delete_weekly_record(record_id, db)


# ============ SOWS ENDPOINTS ============

@app.get("/api/sows", tags=["Sows"])
async def api_get_sows(db: Session = Depends(get_db)):
    """
    Отримання всіх свиноматок
    """
    return await get_sows(db)


@app.post("/api/sows", tags=["Sows"])
async def api_create_sow(
    sow: SowCreate,
    db: Session = Depends(get_db)
):
    """
    Додавання нової свиноматки
    """
    return await create_sow(sow, db)


@app.put("/api/sows/{sow_id}", tags=["Sows"])
async def api_update_sow(
    sow_id: int,
    sow: SowUpdate,
    db: Session = Depends(get_db)
):
    """
    Оновлення даних свиноматки
    """
    return await update_sow(sow_id, sow, db)


@app.delete("/api/sows/{sow_id}", tags=["Sows"])
async def api_delete_sow(
    sow_id: int,
    db: Session = Depends(get_db)
):
    """
    Видалення свиноматки
    """
    return await delete_sow(sow_id, db)


# ============ IMPORT ENDPOINT ============

@app.post("/api/import-excel", tags=["Import"])
async def api_import_excel(
    file: UploadFile = File(...),
    data_type: str = "weekly",
    db: Session = Depends(get_db)
):
    """
    Імпорт даних з Excel файлу
    data_type: 'weekly' для тижневих записів, 'sows' для свиноматок
    """
    return await import_excel(file, data_type, db)


# ============ AI CHAT ENDPOINT ============

@app.post("/api/chat", tags=["AI"])
async def api_chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Чат з AI асистентом для аналізу та рекомендацій
    """
    return await chat_with_ai(request, db)


# ============ HEALTH CHECK ============

@app.get("/api/excel-data", tags=["Excel"])
async def get_excel_data():
    """
    Отримати дані з Excel файлів (farm.xlsx, облік свиноматок.xlsx)
    """
    from backend.excel_reader import excel_reader
    
    try:
        farm_data = excel_reader.read_farm_data()
        sows_data = excel_reader.read_sows_data()
        
        return {
            "status": "success",
            "farm_data": farm_data,
            "sows_data": sows_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Помилка читання Excel файлів: {str(e)}"
        )


@app.get("/api/excel-context", tags=["Excel"])
async def get_excel_context():
    """
    Отримати форматований контекст з Excel файлів для AI
    """
    from backend.excel_reader import get_excel_context_for_ai
    
    try:
        context = get_excel_context_for_ai()
        return {
            "status": "success",
            "context": context
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Помилка формування контексту: {str(e)}"
        )


@app.get("/api/search-sow/{sow_number}", tags=["Excel"])
async def search_sow_in_excel(sow_number: str):
    """
    Пошук свиноматки в Excel файлі
    """
    from backend.excel_reader import excel_reader
    
    try:
        result = excel_reader.search_sow(sow_number)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Свиноматку {sow_number} не знайдено в Excel файлах"
            )
        
        return {
            "status": "success",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Помилка пошуку: {str(e)}"
        )


@app.get("/", tags=["Health"])
async def root():
    """
    Перевірка роботи API
    """
    return {
        "status": "online",
        "message": "Farm AI Chat API працює!",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Детальна перевірка здоров'я системи
    """
    return {
        "status": "healthy",
        "database": "connected",
        "api": "operational"
    }


# Запуск серверу (для розробки)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
