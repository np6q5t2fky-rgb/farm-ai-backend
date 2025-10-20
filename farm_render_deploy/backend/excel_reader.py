"""
Модуль для читання даних з Excel файлів для AI аналітики
ОНОВЛЕНО: Читає ВСІ аркуші, розраховує все автоматично
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class ExcelDataReader:
    """Читає дані з Excel файлів для AI асистента - ВСІ АРКУШІ"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.farm_file = self.base_path / "farm.xlsx"
        self.sows_file = self.base_path / "облік свиноматок.xlsx"
        
        # Константи для розрахунків
        self.FEED_PER_SOW_KG = 300  # кг корму на свиню
        self.PREGNANCY_DAYS = 114  # днів вагітності (3 місяці 3 тижні 3 дні)
        self.GOOD_REGUSTATION_THRESHOLD = 85  # % вище 85 - добре
    
    def read_all_sheets(self, file_path: Path) -> Dict[str, pd.DataFrame]:
        """
        Читає ВСІ аркуші з Excel файлу
        
        Returns:
            Dict де ключ - назва аркуша, значення - DataFrame
        """
        try:
            if not file_path.exists():
                return {}
            
            # Читаємо всі аркуші
            all_sheets = pd.read_excel(file_path, sheet_name=None)
            
            # Очищаємо кожен аркуш від порожніх рядків
            cleaned_sheets = {}
            for sheet_name, df in all_sheets.items():
                cleaned_sheets[sheet_name] = df.dropna(how='all')
            
            return cleaned_sheets
        except Exception as e:
            print(f"Помилка читання {file_path.name}: {e}")
            return {}
    
    def calculate_farrowing_date(self, insemination_date: str) -> Optional[str]:
        """
        Розраховує планову дату опоросу (114 днів від осіменіння)
        """
        try:
            if pd.isna(insemination_date) or insemination_date == 'N/A':
                return None
            
            # Спробуємо різні формати дат
            date_obj = None
            for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y/%m/%d']:
                try:
                    date_obj = datetime.strptime(str(insemination_date).split()[0], fmt)
                    break
                except:
                    continue
            
            if date_obj:
                farrowing_date = date_obj + timedelta(days=self.PREGNANCY_DAYS)
                return farrowing_date.strftime('%d.%m.%Y')
            
            return None
        except:
            return None
    
    def analyze_regustation(self, percent: float) -> str:
        """
        Аналіз відсотка перегулу - чи це добре чи погано
        """
        if pd.isna(percent):
            return "немає даних"
        
        if percent >= self.GOOD_REGUSTATION_THRESHOLD:
            return f"✅ ДОБРЕ ({percent}% ≥ 85%)"
        else:
            return f"⚠️ ПОГАНО ({percent}% < 85% - потрібна увага!)"
    
    def read_farm_data(self) -> Optional[Dict[str, Any]]:
        """
        Читає ВСІ АРКУШІ з farm.xlsx з аналізом
        
        Returns:
            Dict з статистикою, всіма аркушами та розрахунками
        """
        try:
            all_sheets = self.read_all_sheets(self.farm_file)
            
            if not all_sheets:
                return None
            
            result = {
                "file": "farm.xlsx",
                "sheets": {},
                "total_sheets": len(all_sheets)
            }
            
            # Обробляємо кожен аркуш
            for sheet_name, df in all_sheets.items():
                sheet_data = {
                    "name": sheet_name,
                    "total_rows": len(df),
                    "columns": list(df.columns),
                    "data": df.head(30).to_dict('records')  # Перші 30 рядків
                }
                
                # Спеціальна обробка головного аркуша з тижнями
                if 'осіменіння' in df.columns:
                    total_inseminations = df['осіменіння'].sum() if pd.notna(df['осіменіння'].sum()) else 0
                    
                    # Аналіз перегулу
                    if '% перегулу' in df.columns:
                        avg_reg = df['% перегулу'].mean()
                        sheet_data['avg_regustation_percent'] = round(float(avg_reg), 2) if pd.notna(avg_reg) else 0
                        sheet_data['regustation_analysis'] = self.analyze_regustation(sheet_data['avg_regustation_percent'])
                    
                    sheet_data['total_inseminations'] = int(total_inseminations)
                    sheet_data['avg_inseminations_per_week'] = round(total_inseminations / len(df), 1) if len(df) > 0 else 0
                    
                    # Розрахунок корму (кг корму * кількість свиноматок)
                    estimated_sows = int(total_inseminations / len(df)) if len(df) > 0 else 0
                    sheet_data['estimated_feed_kg'] = estimated_sows * self.FEED_PER_SOW_KG
                
                result["sheets"][sheet_name] = sheet_data
            
            # Додаємо загальну статистику (з першого аркуша)
            first_sheet = list(all_sheets.values())[0]
            result["total_weeks"] = len(first_sheet)
            
            if 'осіменіння' in first_sheet.columns:
                result["total_inseminations"] = int(first_sheet['осіменіння'].sum())
                result["recent_weeks"] = first_sheet.head(10).to_dict('records')
            
            if '% перегулу' in first_sheet.columns:
                avg_reg = first_sheet['% перегулу'].mean()
                result["avg_regustation_percent"] = round(float(avg_reg), 2) if pd.notna(avg_reg) else 0
            
            return result
            
        except Exception as e:
            print(f"Помилка читання farm.xlsx: {e}")
            return None
    
    def read_sows_data(self) -> Optional[Dict[str, Any]]:
        """
        Читає ВСІ АРКУШІ з облік свиноматок.xlsx + розраховує планові опороси
        
        Returns:
            Dict з статистикою, всіма аркушами, плановими опоросами
        """
        try:
            all_sheets = self.read_all_sheets(self.sows_file)
            
            if not all_sheets:
                return None
            
            result = {
                "file": "облік свиноматок.xlsx",
                "sheets": {},
                "total_sheets": len(all_sheets),
                "planned_farrowings": []
            }
            
            # Обробляємо кожен аркуш
            for sheet_name, df in all_sheets.items():
                sheet_data = {
                    "name": sheet_name,
                    "total_rows": len(df),
                    "columns": list(df.columns),
                    "data": df.head(30).to_dict('records')  # Перші 30 рядків
                }
                
                # Рахуємо унікальних свиноматок
                if '№ свиноматки' in df.columns:
                    sheet_data['unique_sows'] = int(df['№ свиноматки'].nunique())
                
                # Рахуємо позитивні тести
                if '28 день тест' in df.columns:
                    sheet_data['positive_pregnancy_tests'] = int((df['28 день тест'] == '+').sum())
                
                # Розраховуємо планові опороси для записів з позитивним тестом
                if 'Дата осіменіння' in df.columns and '28 день тест' in df.columns:
                    positive_df = df[df['28 день тест'] == '+']
                    
                    for _, row in positive_df.head(20).iterrows():  # Беремо перші 20
                        sow_num = row.get('№ свиноматки', 'N/A')
                        insem_date = row.get('Дата осіменіння', 'N/A')
                        farrowing_date = self.calculate_farrowing_date(insem_date)
                        
                        if farrowing_date:
                            result["planned_farrowings"].append({
                                "sow": sow_num,
                                "insemination_date": str(insem_date).split()[0],
                                "planned_farrowing": farrowing_date,
                                "feed_needed_kg": self.FEED_PER_SOW_KG
                            })
                
                result["sheets"][sheet_name] = sheet_data
            
            # Загальна статистика з першого аркуша
            first_sheet = list(all_sheets.values())[0]
            result["total_records"] = len(first_sheet)
            
            if '№ свиноматки' in first_sheet.columns:
                result["unique_sows"] = int(first_sheet['№ свиноматки'].nunique())
                result["recent_records"] = first_sheet.head(20).to_dict('records')
            
            if '28 день тест' in first_sheet.columns:
                result["positive_pregnancy_tests"] = int((first_sheet['28 день тест'] == '+').sum())
            
            return result
            
        except Exception as e:
            print(f"Помилка читання облік свиноматок.xlsx: {e}")
            return None
    
    def get_full_context(self) -> str:
        """
        Генерує ПОВНИЙ детальний контекст для AI з ВСІХ аркушів та розрахунками
        
        Returns:
            Форматований текст з даними для AI
        """
        context_parts = []
        
        # Дані з farm.xlsx - ВСІ АРКУШІ
        farm_data = self.read_farm_data()
        if farm_data:
            context_parts.append(f"""
📊 ТИЖНЕВИЙ ОБЛІК (farm.xlsx):
📁 Всього аркушів: {farm_data.get('total_sheets', 0)}
📅 Тижнів в обліку: {farm_data.get('total_weeks', 0)}
💉 Загальна кількість осіменінь: {farm_data.get('total_inseminations', 0)}
📉 Середній % перегулу: {farm_data.get('avg_regustation_percent', 0)}%
""")
            
            # Детально по кожному аркушу
            for sheet_name, sheet_info in farm_data.get('sheets', {}).items():
                context_parts.append(f"\n📄 Аркуш '{sheet_name}':")
                context_parts.append(f"   - Рядків: {sheet_info.get('total_rows', 0)}")
                context_parts.append(f"   - Колонки: {', '.join(sheet_info.get('columns', []))}")
                
                if 'avg_regustation_percent' in sheet_info:
                    context_parts.append(f"   - Середній % перегулу: {sheet_info['avg_regustation_percent']}%")
                    context_parts.append(f"   - Оцінка: {sheet_info.get('regustation_analysis', 'N/A')}")
                
                if 'total_inseminations' in sheet_info:
                    context_parts.append(f"   - Всього осіменінь: {sheet_info['total_inseminations']}")
                    context_parts.append(f"   - Середньо на тиждень: {sheet_info.get('avg_inseminations_per_week', 0)}")
                
                if 'estimated_feed_kg' in sheet_info:
                    context_parts.append(f"   - Приблизна потреба корму: {sheet_info['estimated_feed_kg']} кг ({self.FEED_PER_SOW_KG} кг/свиня)")
            
            # Останні тижні детально
            recent = farm_data.get('recent_weeks', [])[:5]
            if recent:
                context_parts.append(f"\n📅 Останні 5 тижнів:")
                for i, week in enumerate(recent, 1):
                    week_num = week.get('№ тижня', 'N/A')
                    date = week.get('дата початку тижня', 'N/A')
                    insem = week.get('осіменіння', 0)
                    reg = week.get('% перегулу', 0)
                    reg_analysis = self.analyze_regustation(reg)
                    context_parts.append(f"   {i}. Тиждень {week_num} ({date}): {insem} осіменінь, перегул {reg}% - {reg_analysis}")
        
        # Дані з облік свиноматок.xlsx - ВСІ АРКУШІ + ПЛАНОВІ ОПОРОСИ
        sows_data = self.read_sows_data()
        if sows_data:
            context_parts.append(f"""

🐷 ОБЛІК СВИНОМАТОК (облік свиноматок.xlsx):
📁 Всього аркушів: {sows_data.get('total_sheets', 0)}
📝 Всього записів: {sows_data.get('total_records', 0)}
🐷 Унікальних свиноматок: {sows_data.get('unique_sows', 0)}
✅ Позитивних тестів на 28 день: {sows_data.get('positive_pregnancy_tests', 0)}
""")
            
            # Детально по кожному аркушу
            for sheet_name, sheet_info in sows_data.get('sheets', {}).items():
                context_parts.append(f"\n📄 Аркуш '{sheet_name}':")
                context_parts.append(f"   - Рядків: {sheet_info.get('total_rows', 0)}")
                context_parts.append(f"   - Колонки: {', '.join(sheet_info.get('columns', []))}")
                
                if 'unique_sows' in sheet_info:
                    context_parts.append(f"   - Унікальних свиноматок: {sheet_info['unique_sows']}")
                
                if 'positive_pregnancy_tests' in sheet_info:
                    context_parts.append(f"   - Позитивних тестів: {sheet_info['positive_pregnancy_tests']}")
            
            # ПЛАНОВІ ОПОРОСИ (ПРОГНОЗ)
            planned = sows_data.get('planned_farrowings', [])[:10]
            if planned:
                context_parts.append(f"\n🔮 ПРОГНОЗ ПЛАНОВИХ ОПОРОСІВ (перші 10):")
                for i, plan in enumerate(planned, 1):
                    context_parts.append(
                        f"   {i}. Свиноматка {plan['sow']}: "
                        f"осіменіння {plan['insemination_date']} → "
                        f"плановий опорос {plan['planned_farrowing']} "
                        f"(потреба корму: {plan['feed_needed_kg']} кг)"
                    )
            
            # Останні записи
            recent = sows_data.get('recent_records', [])[:5]
            if recent:
                context_parts.append(f"\n📋 Останні 5 записів:")
                for i, record in enumerate(recent, 1):
                    sow_num = record.get('№ свиноматки', 'N/A')
                    date = record.get('Дата осіменіння', 'N/A')
                    test = record.get('28 день тест', 'N/A')
                    context_parts.append(f"   {i}. {sow_num} - {date}, тест: {test}")
        
        # Загальні правила та константи
        context_parts.append(f"""

📐 ПРАВИЛА ТА РОЗРАХУНКИ:
- Вагітність триває: {self.PREGNANCY_DAYS} днів (3 місяці 3 тижні 3 дні)
- Корм на свиню: {self.FEED_PER_SOW_KG} кг протягом вагітності
- Добрий % перегулу: ≥ {self.GOOD_REGUSTATION_THRESHOLD}%
- Поганий % перегулу: < {self.GOOD_REGUSTATION_THRESHOLD}% (потрібна увага!)
""")
        
        if not context_parts:
            return "⚠️ Excel файли не знайдено або порожні"
        
        return "\n".join(context_parts)
    
    def search_sow(self, sow_number: str) -> Optional[Dict[str, Any]]:
        """
        Пошук всіх записів по конкретній свиноматці
        
        Args:
            sow_number: Номер свиноматки
            
        Returns:
            Dict з історією свиноматки
        """
        try:
            if not self.sows_file.exists():
                return None
            
            df = pd.read_excel(self.sows_file)
            
            # Фільтруємо по номеру свиноматки
            sow_records = df[df['№ свиноматки'].astype(str).str.contains(str(sow_number), case=False, na=False)]
            
            if len(sow_records) == 0:
                return None
            
            return {
                "sow_number": sow_number,
                "total_records": len(sow_records),
                "records": sow_records.to_dict('records')
            }
        except Exception as e:
            print(f"Помилка пошуку свиноматки: {e}")
            return None
    
    def get_statistics_summary(self) -> Dict[str, Any]:
        """
        Повна статистична зводка для AI
        
        Returns:
            Dict з усією статистикою
        """
        farm_data = self.read_farm_data()
        sows_data = self.read_sows_data()
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "farm_data": farm_data,
            "sows_data": sows_data
        }
        
        return summary


# Глобальний екземпляр для використання в API
excel_reader = ExcelDataReader()


def get_excel_context_for_ai() -> str:
    """
    Зручна функція для отримання контексту для AI
    
    Returns:
        Форматований текст для додавання до промпту AI
    """
    return excel_reader.get_full_context()
