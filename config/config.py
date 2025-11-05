# config.py
import os
from dotenv import load_dotenv

# На хостинге (Railway) эта строка ничего не делает, 
# но она полезна для локальной разработки.
load_dotenv() 

# Чтение переменных из окружения Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") 
GSPREAD_JSON_STRING = os.getenv("GSPREAD_JSON_STRING")
SHEET_URL = os.getenv("SHEET_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("Переменная BOT_TOKEN не найдена. Убедитесь, что она установлена в Railway.")




