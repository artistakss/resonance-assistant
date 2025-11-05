# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from config import BOT_TOKEN, ADMIN_ID
from database.db import init_db, add_user
from services.subscription import setup_scheduler
from services.sheets_api import SheetsManager

# Импорт обработчиков
from handlers import user_start, user_payments, admin_panel, user_gpt # GPT пока не реализован, но роутер добавлен

# Настройка логирования
logging.basicConfig(level=logging.INFO)

async def on_startup(bot: Bot, sheets_manager: SheetsManager):
    """Действия при запуске бота."""
    await init_db()
    
    # Запуск планировщика задач (для проверки подписок)
    setup_scheduler(bot)
    
    logging.info("База данных и планировщик задач инициализированы.")
    
    # Проверка подключения к Google Sheets (вызовет ошибку, если ключ или URL неверны)
    sheets_manager._ensure_headers() 
    logging.info("Подключение к Google Sheets успешно.")
    
    await bot.send_message(ADMIN_ID, "✅ **Resonance Assistant Bot запущен!**")

async def main():
    """Основная функция запуска бота."""
    # Инициализация Google Sheets Manager перед запуском диспетчера
    sheets_manager = SheetsManager()
    
    bot = Bot(BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация роутеров
    dp.include_router(user_start.router)
    dp.include_router(user_payments.router)
    dp.include_router(admin_panel.router)
    # dp.include_router(user_gpt.router) # Раскомментировать, когда будет реализован
    
    # Обработка команды /start
    @dp.message(CommandStart())
    async def command_start_handler(message: Message) -> None:
        user_id = message.from_user.id
        username = message.from_user.username
        full_name = message.from_user.full_name
        await add_user(user_id, username, full_name)
        
        # Используем reply_markup из user_start.py
        await message.answer(
            f"🧘 **Здравствуйте, {full_name}! Я ваш Resonance Assistant.**\n\n"
            "Я помогу вам на пути саморазвития и осознанности, а также запишу на консультации к Анжелике.",
            reply_markup=user_start.main_menu_keyboard # Вставьте сюда вашу основную Reply-клавиатуру
        )

    # Запуск бота с передачей SheetsManager в on_startup
    await on_startup(bot, sheets_manager)
    
    # Передаем sheets_manager в диспетчер, чтобы он был доступен в обработчиках
    await dp.start_polling(bot, sheets_manager=sheets_manager)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.warning("Bot stopped!")
