"""
Скрипт ініціалізації бази даних
Створює таблиці та додає тестові дані
"""

from models import create_tables, SessionLocal, Sow, WeeklyRecord
from datetime import date, timedelta


def add_sample_data():
    """
    Додавання прикладних даних для тестування
    """
    db = SessionLocal()
    
    try:
        # Перевірка чи є вже дані
        existing_sows = db.query(Sow).count()
        existing_records = db.query(WeeklyRecord).count()
        
        if existing_sows > 0 or existing_records > 0:
            print("ℹ️  База даних вже містить дані. Пропускаємо додавання тестових даних.")
            return
        
        # Додавання прикладних свиноматок
        sows_data = [
            {"number": "001", "birth_date": date(2022, 1, 15), "status": "активна", "notes": "Високопродуктивна"},
            {"number": "002", "birth_date": date(2022, 3, 20), "status": "активна", "notes": "Першоопороска"},
            {"number": "003", "birth_date": date(2021, 11, 10), "status": "активна", "notes": ""},
            {"number": "004", "birth_date": date(2022, 5, 5), "status": "вибракувана", "notes": "Виведена через вік"},
            {"number": "005", "birth_date": date(2022, 2, 28), "status": "активна", "notes": "Добре здоров'я"},
        ]
        
        for sow_data in sows_data:
            sow = Sow(**sow_data)
            db.add(sow)
        
        # Додавання прикладних тижневих записів
        today = date.today()
        for i in range(8):  # Останні 8 тижнів
            week_date = today - timedelta(weeks=i)
            record = WeeklyRecord(
                week_start_date=week_date,
                farrowings=3 + (i % 3),
                piglets_born_alive=30 + (i * 2),
                piglets_born_dead=2 + (i % 2),
                notes=f"Тиждень {i+1}" if i < 3 else None
            )
            record.calculate_survival_rate()
            db.add(record)
        
        db.commit()
        print("✅ Тестові дані додано успішно!")
        print(f"   - Додано {len(sows_data)} свиноматок")
        print(f"   - Додано 8 тижневих записів")
        
    except Exception as e:
        print(f"❌ Помилка при додаванні тестових даних: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """
    Головна функція ініціалізації
    """
    print("🚀 Ініціалізація бази даних...")
    
    # Створення таблиць
    create_tables()
    
    # Додавання тестових даних
    print("\n📝 Додавання тестових даних...")
    add_sample_data()
    
    print("\n✨ Ініціалізація завершена!")
    print("Можете запускати додаток командою: python run.py")


if __name__ == "__main__":
    main()
