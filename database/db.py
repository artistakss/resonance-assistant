import aiosqlite
from config import SUBSCRIPTION_DURATION_DAYS
from datetime import datetime, timedelta

DB_NAME = 'bot_data.db'

async def init_db():
    """Инициализация базы данных и создание таблиц."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                sub_start_date TEXT,
                sub_end_date TEXT,
                status TEXT DEFAULT 'inactive'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_details (
                method TEXT PRIMARY KEY,
                details TEXT
            )
        """)
        # Инициализация реквизитов по умолчанию
        await db.execute("INSERT OR IGNORE INTO payment_details VALUES ('Kaspi', 'Ссылка на Kaspi Банк по умолчанию')")
        await db.execute("INSERT OR IGNORE INTO payment_details VALUES ('Tinkoff', 'Карта Tinkoff по умолчанию')")
        await db.execute("INSERT OR IGNORE INTO payment_details VALUES ('USDT', 'Кошелек TRC-20 по умолчанию')")
        await db.commit()

async def get_user(user_id):
    """Получает информацию о пользователе."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()

async def add_user(user_id, username, full_name):
    """Добавляет нового пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )
        await db.commit()

async def activate_subscription(user_id):
    """Активирует подписку на 30 дней."""
    start_date = datetime.now()
    end_date = start_date + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET sub_start_date = ?, sub_end_date = ?, status = 'active' WHERE user_id = ?",
            (start_date.isoformat(), end_date.isoformat(), user_id)
        )
        await db.commit()
    return start_date, end_date

async def get_payment_details(method):
    """Получает реквизиты оплаты."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT details FROM payment_details WHERE method = ?", (method,))
        result = await cursor.fetchone()
        return result[0] if result else "Реквизиты не найдены."
    
# ... (Добавить функции для получения всех активных пользователей, обновления реквизитов и т.д.)

feat: add initial database setup
