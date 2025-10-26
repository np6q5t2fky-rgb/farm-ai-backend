"""
Frontend додаток на Reflex для системи обліку свиноферми
"""

import reflex as rx
from typing import List, Dict
import httpx
from datetime import datetime, date

# URL Backend API
API_URL = "https://farm-ai-chat.fly.dev/api"


class FarmState(rx.State):
    """
    Стан додатку - зберігає всі дані та методи
    """
    # Поточна сторінка
    current_page: str = "weekly"
    
    # Тижневі записи
    weekly_records: List[Dict] = []
    loading_weekly: bool = False
    
    # Свиноматки
    sows: List[Dict] = []
    loading_sows: bool = False
    
    # Дані для таблиці Excel
    table_data: List[Dict] = []
    loading_table: bool = False
    # Пам'ять AI
    memory: List[Dict] = []
    loading_memory: bool = False
    # Завантаження Excel
    show_excel_upload: bool = False
    excel_upload_loading: bool = False
    # Звіт
    report_loading: bool = False

    # Форми для створення/редагування
    show_weekly_form: bool = False
    show_sow_form: bool = False
    editing_id: int = None
    
    # Поля форми тижневого запису
    form_week_date: str = ""
    form_farrowings: int = 0
    form_alive: int = 0
    form_dead: int = 0
    form_notes: str = ""
    
    # Поля форми свиноматки
    form_number: str = ""
    form_birth_date: str = ""
    form_status: str = "активна"
    form_sow_notes: str = ""
    
    # Чат
    chat_messages: List[Dict] = []
    chat_input: str = ""
    chat_loading: bool = False
    show_chat: bool = False
    
    # Повідомлення
    message: str = ""
    message_type: str = ""  # success, error, info
    
    async def load_weekly_records(self):
        """Завантаження тижневих записів"""
        self.loading_weekly = True
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/weekly-records")
                if response.status_code == 200:
                    self.weekly_records = response.json()
        except Exception as e:
            self.show_message(f"Помилка завантаження: {str(e)}", "error")
        finally:
            self.loading_weekly = False
    
    async def load_sows(self):
        """Завантаження свиноматок"""
        self.loading_sows = True
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/sows")
                if response.status_code == 200:
                    self.sows = response.json()
        except Exception as e:
            self.show_message(f"Помилка завантаження: {str(e)}", "error")
        finally:
            self.loading_sows = False
    
    async def load_table(self):
        """Завантажити таблицю Excel"""
        self.loading_table = True
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/table")
                if response.status_code == 200:
                    self.table_data = response.json()
                else:
                    self.show_message(f"Помилка: {response.text}", "error")
        except Exception as e:
            self.show_message(f"Помилка таблиці: {str(e)}", "error")
        finally:
            self.loading_table = False

    async def load_memory(self):
        """Завантажити пам'ять AI"""
        self.loading_memory = True
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/memory")
                if response.status_code == 200:
                    self.memory = response.json()
                else:
                    self.show_message(f"Помилка: {response.text}", "error")
        except Exception as e:
            self.show_message(f"Помилка пам'яті: {str(e)}", "error")
        finally:
            self.loading_memory = False

    def open_excel_upload(self):
        self.show_excel_upload = True
    def close_excel_upload(self):
        self.show_excel_upload = False

    async def upload_excel(self, file):
        """Завантажити Excel файл на сервер"""
        self.excel_upload_loading = True
        try:
            async with httpx.AsyncClient() as client:
                files = {"file": (file.name, file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                response = await client.post(f"{API_URL}/upload-excel", files=files)
                if response.status_code == 200:
                    self.show_message("Excel успішно завантажено!", "success")
                    self.close_excel_upload()
                    return FarmState.load_table
                else:
                    self.show_message(f"Помилка: {response.text}", "error")
        except Exception as e:
            self.show_message(f"Помилка завантаження: {str(e)}", "error")
        finally:
            self.excel_upload_loading = False

    async def download_report(self):
        """Завантажити Excel звіт"""
        self.report_loading = True
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/report")
                if response.status_code == 200:
                    # Зберегти файл на пристрій
                    with open("farm_report.xlsx", "wb") as f:
                        f.write(response.content)
                    self.show_message("Звіт збережено!", "success")
                else:
                    self.show_message(f"Помилка: {response.text}", "error")
        except Exception as e:
            self.show_message(f"Помилка звіту: {str(e)}", "error")
        finally:
            self.report_loading = False

    def switch_page(self, page: str):
        """Перемикання між сторінками"""
        self.current_page = page
        if page == "weekly":
            return FarmState.load_weekly_records
        elif page == "sows":
            return FarmState.load_sows
        elif page == "table":
            return FarmState.load_table
        elif page == "memory":
            return FarmState.load_memory
        elif page == "report":
            return None
    
    def toggle_chat(self):
        """Показати/сховати чат"""
        self.show_chat = not self.show_chat
    
    def open_weekly_form(self, record_id: int = None):
        """Відкрити форму тижневого запису"""
        if record_id:
            # Редагування існуючого
            record = next((r for r in self.weekly_records if r["id"] == record_id), None)
            if record:
                self.editing_id = record_id
                self.form_week_date = record["week_start_date"]
                self.form_farrowings = record["farrowings"]
                self.form_alive = record["piglets_born_alive"]
                self.form_dead = record["piglets_born_dead"]
                self.form_notes = record.get("notes", "")
        else:
            # Новий запис
            self.editing_id = None
            self.form_week_date = ""
            self.form_farrowings = 0
            self.form_alive = 0
            self.form_dead = 0
            self.form_notes = ""
        
        self.show_weekly_form = True
    
    def close_weekly_form(self):
        """Закрити форму тижневого запису"""
        self.show_weekly_form = False
        self.editing_id = None
    
    async def save_weekly_record(self):
        """Зберегти тижневий запис"""
        try:
            data = {
                "week_start_date": self.form_week_date,
                "farrowings": self.form_farrowings,
                "piglets_born_alive": self.form_alive,
                "piglets_born_dead": self.form_dead,
                "notes": self.form_notes
            }
            
            async with httpx.AsyncClient() as client:
                if self.editing_id:
                    # Оновлення
                    response = await client.put(
                        f"{API_URL}/weekly-records/{self.editing_id}",
                        json=data
                    )
                else:
                    # Створення
                    response = await client.post(
                        f"{API_URL}/weekly-records",
                        json=data
                    )
                
                if response.status_code in [200, 201]:
                    self.show_message("Запис збережено успішно!", "success")
                    self.close_weekly_form()
                    return FarmState.load_weekly_records
                else:
                    self.show_message(f"Помилка: {response.text}", "error")
        
        except Exception as e:
            self.show_message(f"Помилка збереження: {str(e)}", "error")
    
    async def delete_weekly_record(self, record_id: int):
        """Видалити тижневий запис"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(f"{API_URL}/weekly-records/{record_id}")
                
                if response.status_code == 200:
                    self.show_message("Запис видалено!", "success")
                    return FarmState.load_weekly_records
                else:
                    self.show_message(f"Помилка видалення: {response.text}", "error")
        
        except Exception as e:
            self.show_message(f"Помилка: {str(e)}", "error")
    
    def open_sow_form(self, sow_id: int = None):
        """Відкрити форму свиноматки"""
        if sow_id:
            sow = next((s for s in self.sows if s["id"] == sow_id), None)
            if sow:
                self.editing_id = sow_id
                self.form_number = sow["number"]
                self.form_birth_date = sow["birth_date"]
                self.form_status = sow["status"]
                self.form_sow_notes = sow.get("notes", "")
        else:
            self.editing_id = None
            self.form_number = ""
            self.form_birth_date = ""
            self.form_status = "активна"
            self.form_sow_notes = ""
        
        self.show_sow_form = True
    
    def close_sow_form(self):
        """Закрити форму свиноматки"""
        self.show_sow_form = False
        self.editing_id = None
    
    async def save_sow(self):
        """Зберегти свиноматку"""
        try:
            data = {
                "number": self.form_number,
                "birth_date": self.form_birth_date,
                "status": self.form_status,
                "notes": self.form_sow_notes
            }
            
            async with httpx.AsyncClient() as client:
                if self.editing_id:
                    response = await client.put(
                        f"{API_URL}/sows/{self.editing_id}",
                        json=data
                    )
                else:
                    response = await client.post(
                        f"{API_URL}/sows",
                        json=data
                    )
                
                if response.status_code in [200, 201]:
                    self.show_message("Свиноматку збережено!", "success")
                    self.close_sow_form()
                    return FarmState.load_sows
                else:
                    self.show_message(f"Помилка: {response.text}", "error")
        
        except Exception as e:
            self.show_message(f"Помилка збереження: {str(e)}", "error")
    
    async def delete_sow(self, sow_id: int):
        """Видалити свиноматку"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(f"{API_URL}/sows/{sow_id}")
                
                if response.status_code == 200:
                    self.show_message("Свиноматку видалено!", "success")
                    return FarmState.load_sows
                else:
                    self.show_message(f"Помилка видалення: {response.text}", "error")
        
        except Exception as e:
            self.show_message(f"Помилка: {str(e)}", "error")
    
    async def send_chat_message(self):
        """Відправити повідомлення в чат"""
        if not self.chat_input.strip():
            return
        
        user_message = self.chat_input
        self.chat_messages.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        self.chat_input = ""
        self.chat_loading = True
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{API_URL}/chat",
                    json={"message": user_message, "include_context": True}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.chat_messages.append({
                        "role": "assistant",
                        "content": data["response"],
                        "timestamp": data["timestamp"]
                    })
                else:
                    self.chat_messages.append({
                        "role": "assistant",
                        "content": f"Помилка: {response.text}",
                        "timestamp": datetime.now().isoformat()
                    })
        
        except Exception as e:
            self.chat_messages.append({
                "role": "assistant",
                "content": f"Помилка зв'язку: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
        
        finally:
            self.chat_loading = False
    
    def show_message(self, text: str, msg_type: str):
        """Показати повідомлення"""
        self.message = text
        self.message_type = msg_type


# ============ UI КОМПОНЕНТИ ============

def navbar() -> rx.Component:
    """Навігаційна панель з вкладками"""
    return rx.hstack(
        rx.heading("🐷 Облік Свиноферми", size="7"),
        rx.spacer(),
        rx.button("Тижневий облік", on_click=FarmState.switch_page("weekly"), variant=rx.cond(FarmState.current_page == "weekly", "soft", "outline"), size="3"),
        rx.button("Свиноматки", on_click=FarmState.switch_page("sows"), variant=rx.cond(FarmState.current_page == "sows", "soft", "outline"), size="3"),
        rx.button("Таблиця", on_click=FarmState.switch_page("table"), variant=rx.cond(FarmState.current_page == "table", "soft", "outline"), size="3"),
        rx.button("Пам'ять", on_click=FarmState.switch_page("memory"), variant=rx.cond(FarmState.current_page == "memory", "soft", "outline"), size="3"),
        rx.button("Звіт", on_click=FarmState.switch_page("report"), variant=rx.cond(FarmState.current_page == "report", "soft", "outline"), size="3"),
        width="100%",
        padding="1em",
        background_color="var(--accent-3)",
        align="center",
    )


def weekly_records_page() -> rx.Component:
    """Сторінка тижневого обліку"""
    return rx.vstack(
        rx.hstack(
            rx.heading("📊 Тижневий облік", size="6"),
            rx.spacer(),
            rx.button(
                "+ Новий запис",
                on_click=lambda: FarmState.open_weekly_form(),
                size="3",
            ),
            width="100%",
            padding="1em",
        ),
        rx.cond(
            FarmState.loading_weekly,
            rx.spinner(size="3"),
            rx.box(
                rx.foreach(
                    FarmState.weekly_records,
                    lambda record: rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.text(
                                    f"Тиждень: {record['week_start_date']}",
                                    weight="bold",
                                    size="4",
                                ),
                                rx.spacer(),
                                rx.hstack(
                                    rx.button(
                                        "✏️",
                                        on_click=lambda: FarmState.open_weekly_form(record["id"]),
                                        size="2",
                                        variant="soft",
                                    ),
                                    rx.button(
                                        "🗑️",
                                        on_click=lambda: FarmState.delete_weekly_record(record["id"]),
                                        size="2",
                                        color_scheme="red",
                                        variant="soft",
                                    ),
                                    spacing="2",
                                ),
                                width="100%",
                            ),
                            rx.divider(),
                            rx.grid(
                                rx.vstack(
                                    rx.text("Опороси", size="1", color_scheme="gray"),
                                    rx.text(record["farrowings"], size="5", weight="bold"),
                                    align="center",
                                ),
                                rx.vstack(
                                    rx.text("Живих", size="1", color_scheme="gray"),
                                    rx.text(record["piglets_born_alive"], size="5", weight="bold", color_scheme="green"),
                                    align="center",
                                ),
                                rx.vstack(
                                    rx.text("Мертвих", size="1", color_scheme="gray"),
                                    rx.text(record["piglets_born_dead"], size="5", weight="bold", color_scheme="red"),
                                    align="center",
                                ),
                                rx.vstack(
                                    rx.text("Виживаність", size="1", color_scheme="gray"),
                                    rx.text(f"{record['survival_rate']}%", size="5", weight="bold", color_scheme="blue"),
                                    align="center",
                                ),
                                columns="4",
                                spacing="4",
                                width="100%",
                            ),
                            rx.cond(
                                record["notes"],
                                rx.box(
                                    rx.text("Примітки:", size="1", color_scheme="gray"),
                                    rx.text(record["notes"], size="2"),
                                ),
                                rx.box(),
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        width="100%",
                    ),
                ),
                width="100%",
            ),
        ),
        spacing="4",
        width="100%",
        padding="1em",
    )


def sows_page() -> rx.Component:
    """Сторінка свиноматок"""
    return rx.vstack(
        rx.hstack(
            rx.heading("🐖 Свиноматки", size="6"),
            rx.spacer(),
            rx.button(
                "+ Додати свиноматку",
                on_click=lambda: FarmState.open_sow_form(),
                size="3",
            ),
            width="100%",
            padding="1em",
        ),
        rx.cond(
            FarmState.loading_sows,
            rx.spinner(size="3"),
            rx.box(
                rx.foreach(
                    FarmState.sows,
                    lambda sow: rx.card(
                        rx.hstack(
                            rx.vstack(
                                rx.text(f"№ {sow['number']}", weight="bold", size="5"),
                                rx.text(f"Народження: {sow['birth_date']}", size="2"),
                                rx.badge(
                                    sow["status"],
                                    color_scheme=rx.cond(sow["status"] == "активна", "green", "gray"),
                                ),
                                spacing="1",
                            ),
                            rx.spacer(),
                            rx.hstack(
                                rx.button(
                                    "✏️",
                                    on_click=lambda: FarmState.open_sow_form(sow["id"]),
                                    size="2",
                                    variant="soft",
                                ),
                                rx.button(
                                    "🗑️",
                                    on_click=lambda: FarmState.delete_sow(sow["id"]),
                                    size="2",
                                    color_scheme="red",
                                    variant="soft",
                                ),
                                spacing="2",
                            ),
                            width="100%",
                            align="center",
                        ),
                        width="100%",
                    ),
                ),
                width="100%",
            ),
        ),
        spacing="4",
        width="100%",
        padding="1em",
    )


def table_page() -> rx.Component:
    """Сторінка перегляду таблиці Excel"""
    return rx.vstack(
        rx.heading("📋 Таблиця Excel", size="6"),
        rx.button(
            "Завантажити Excel",
            on_click=lambda: FarmState.open_excel_upload(),
            size="3",
        ),
        rx.cond(
            FarmState.loading_table,
            rx.spinner(size="3"),
            rx.box(
                rx.foreach(
                    FarmState.table_data,
                    lambda row: rx.card(
                        rx.text(str(row)),
                        width="100%",
                    ),
                ),
                width="100%",
            ),
        ),
        width="100%",
        padding="1em",
    )


def memory_page() -> rx.Component:
    """Сторінка пам'яті AI"""
    return rx.vstack(
        rx.heading("🧠 Пам'ять AI", size="6"),
        rx.box(
            rx.foreach(
                FarmState.memory,
                lambda msg: rx.card(
                    rx.text(f"{msg['role']}: {msg['text']}", size="3"),
                    width="100%",
                ),
            ),
            width="100%",
        ),
        width="100%",
        padding="1em",
    )


def report_page() -> rx.Component:
    """Сторінка звіту Excel"""
    return rx.vstack(
        rx.heading("📑 Звіт Excel", size="6"),
        rx.button(
            "Завантажити звіт",
            on_click=FarmState.download_report,
            size="3",
        ),
        width="100%",
        padding="1em",
    )


def chat_panel() -> rx.Component:
    """Панель чату з AI"""
    return rx.cond(
        FarmState.show_chat,
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.heading("💬 AI Асистент", size="5"),
                    rx.spacer(),
                    rx.button(
                        "✕",
                        on_click=FarmState.toggle_chat,
                        size="2",
                        variant="soft",
                    ),
                    width="100%",
                    padding="1em",
                    background_color="var(--accent-3)",
                ),
                rx.box(
                    rx.foreach(
                        FarmState.chat_messages,
                        lambda msg: rx.box(
                            rx.card(
                                rx.text(msg["content"], size="2"),
                                background_color=rx.cond(
                                    msg["role"] == "user",
                                    "var(--accent-3)",
                                    "var(--gray-3)",
                                ),
                            ),
                            padding="0.5em",
                            align=rx.cond(msg["role"] == "user", "right", "left"),
                        ),
                    ),
                    height="300px",
                    overflow_y="auto",
                    padding="1em",
                ),
                rx.hstack(
                    rx.input(
                        placeholder="Напишіть ваше питання...",
                        value=FarmState.chat_input,
                        on_change=FarmState.set_chat_input,
                        width="100%",
                        size="3",
                    ),
                    rx.button(
                        "Відправити",
                        on_click=FarmState.send_chat_message,
                        loading=FarmState.chat_loading,
                        size="3",
                    ),
                    width="100%",
                    padding="1em",
                ),
                spacing="0",
                width="100%",
                max_width="600px",
            ),
            position="fixed",
            bottom="0",
            right="0",
            width=["100%", "100%", "600px"],
            height="500px",
            background_color="var(--gray-1)",
            border="1px solid var(--gray-5)",
            border_radius="8px 8px 0 0",
            box_shadow="0 -2px 10px rgba(0,0,0,0.1)",
            z_index="1000",
        ),
        rx.button(
            "💬 AI Чат",
            on_click=FarmState.toggle_chat,
            position="fixed",
            bottom="20px",
            right="20px",
            size="4",
            z_index="999",
        ),
    )


# Додати модальне вікно для завантаження Excel

def excel_upload_modal() -> rx.Component:
    return rx.cond(
        FarmState.show_excel_upload,
        rx.modal(
            rx.vstack(
                rx.heading("Завантажити Excel файл", size="5"),
                rx.input(type="file", accept=".xlsx", on_change=FarmState.upload_excel),
                rx.button("Закрити", on_click=FarmState.close_excel_upload, size="3"),
                spacing="3",
            ),
            is_open=True,
        ),
        rx.box(),
    )


# Оновити index для модального вікна

def index() -> rx.Component:
    return rx.box(
        navbar(),
        rx.cond(FarmState.current_page == "weekly", weekly_records_page(),
            rx.cond(FarmState.current_page == "sows", sows_page(),
                rx.cond(FarmState.current_page == "table", table_page(),
                    rx.cond(FarmState.current_page == "memory", memory_page(),
                        rx.cond(FarmState.current_page == "report", report_page(), weekly_records_page())
                    )
                )
            )
        ),
        chat_panel(),
        excel_upload_modal(),
        width="100%",
        min_height="100vh",
    )


# Створення додатку
app = rx.App()
app.add_page(index, on_load=FarmState.load_weekly_records)
