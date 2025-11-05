# config.py

import os
from dotenv import load_dotenv

load_dotenv()

# ... (Остальные переменные: BOT_TOKEN, ADMIN_ID, CHECKER_ID и т.д.)

# --- Настройки Google Sheets ---
# Теперь мы ожидаем, что JSON будет передан как строка в переменной окружения
GSPREAD_JSON_STRING = os.getenv("GSPREAD_JSON_STRING")
SHEET_URL = os.getenv("SHEET_URL")

# ... (Остальные переменные)

config: add config.py
