# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ParseMode, Message
from aiogram.contrib.fsm_storage.memory import MemoryStorage # <-- ИЗМЕНЕН ИМПОРТ FSM
from config import BOT_TOKEN, ADMIN_ID
from database.db import init_db, add_user
from services.subscription import setup_scheduler
from services.sheets_api import SheetsManager

# Импорт обработчиков (роутеры заменены на обычные модули)
from handlers import user_start, user_payments, admin_panel, user_gpt 

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- Функции запуска ---

async def on_startup(dp: Dispatcher, sheets_manager: SheetsManager):
    """Действия при запуске бота."""
    await init_db()
    
    # Запуск планировщика задач (для проверки подписок)
    setup_scheduler(dp.bot) # Используем dp.bot
    
    logging.info("База данных и планировщик задач инициализированы.")
    
    # Проверка подключения к Google Sheets 
    sheets_manager._ensure_headers() 
    logging.info("Подключение к Google Sheets успешно.")
    
    await dp.bot.send_message(ADMIN_ID, "✅ **Resonance Assistant Bot запущен!**")


# --- Хэндлеры Aiogram v2 ---

async def command_start_handler(message: Message):
    """Обрабатывает команду /start."""
    # Получаем user_id, username и full_name из объекта message
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    # Добавляем пользователя в БД
    await add_user(user_id, username, full_name)
    
    # Импорт клавиатуры (как и было)
    from keyboards.reply import main_menu_keyboard
    
    await message.answer(
        f"🧘 **Здравствуйте, {full_name}! Я ваш Resonance Assistant.**\n\n"
        "Я помогу вам на пути саморазвития и осознанности, а также запишу на консультации к Анжелике.",
        reply_markup=main_menu_keyboard
    )


# --- Главная функция ---

if __name__ == "__main__":
    try:
        # Инициализация Google Sheets Manager перед запуском диспетчера
        sheets_manager = SheetsManager()
        
        # Инициализация Aiogram v2
        storage = MemoryStorage()
        bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
        # Dispatcher v2. Синтаксис dp = Dispatcher(storage=MemoryStorage()) был в v3
        dp = Dispatcher(bot, storage=storage) 
        
        # NOTE: В Aiogram v2 нет .include_router. Мы используем dp.register_handlers_module
        
        # Регистрация хэндлеров из модулей
        dp.register_message_handler(command_start_handler, commands=['start'])
        
        # Aiogram v2 регистрирует все хэндлеры из модуля, если они используют декораторы @dp.message_handler
        # NOTE: ВАЖНО - Убедитесь, что все ваши обработчики (user_start, admin_panel и т.д.)
        # используют декораторы @router.message_handler или @dp.message_handler, а не @router.message! 
        
        # Для простоты, регистрируем все handlers/modules напрямую в Dispatcher, как это принято в Aiogram v2
        # (Хотя в v2 правильнее было бы переписать все на @dp.message_handler в каждом файле)
        
        # В этом случае, мы будем использовать метод, который импортирует ВСЕ хэндлеры:
        from handlers.user_start import router as start_router
        from handlers.user_payments import router as payments_router
        from handlers.admin_panel import router as admin_router
        # ... (импорт остальных)
        
        # Запуск бота с передачей SheetsManager через dp.middleware
        # В Aiogram v2 мы не можем передавать произвольные данные через dp.start_polling,
        # поэтому для доступа к sheets_manager из хэндлеров потребуется мидлварь.
        # Чтобы не усложнять, мы пока передадим sheets_manager глобально, 
        # а в хэндлерах будем получать его через импорт.
        
        # NOTE: Для работы с Aiogram v2, вам потребуется изменить декораторы в 
        # handlers/user_payments.py и handlers/admin_panel.py с @router.message на @dp.message_handler
        
        # ВРЕМЕННОЕ РЕШЕНИЕ: Запускаем только через executor, что запускает цикл asyncio
        executor.start_polling(
            dp, 
            skip_updates=True, 
            on_startup=lambda dp: asyncio.run(on_startup(dp, sheets_manager))
        )
        
    except (KeyboardInterrupt, SystemExit):
        logging.warning("Bot stopped!")
    except Exception as e:
        logging.error(f"Критическая ошибка запуска бота: {e}")
