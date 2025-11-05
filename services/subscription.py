from aiogram import Bot
from config import CHANNEL_ID, REMINDER_BEFORE_DAYS
from database.db import get_user, get_users_with_active_sub, activate_subscription, get_all_active_users
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def check_and_manage_subscriptions(bot: Bot):
    """
    Проверяет статус подписки всех активных пользователей.
    Удаляет истёкших, напоминает о скором окончании.
    """
    now = datetime.now()
    active_users = await get_all_active_users()

    for user in active_users:
        user_id = user['user_id']
        end_date = datetime.fromisoformat(user['sub_end_date'])
        username = user['username'] or f"ID: {user_id}"

        # 1. Проверка на Истечение Срока
        if now >= end_date:
            try:
                # Попытка удаления пользователя из канала
                await bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=user_id, until_date=0)
                # Разбанить сразу, чтобы дать возможность вернуться после оплаты
                await bot.unban_chat_member(chat_id=CHANNEL_ID, user_id=user_id) 
                
                # Обновление статуса в БД (для примера, в реальном проекте обновим в db.py)
                # await db.set_user_inactive(user_id) 
                
                # Уведомление админа
                # await notify_admin(bot, f"⚠️ У пользователя @{username} (ID: {user_id}) закончился доступ и он удален из канала.")
                
                # Уведомление пользователя
                await bot.send_message(user_id, "⛔ **Доступ к каналу 'Resonance' закрыт.**\n\nВаша подписка истекла. Продлите её, чтобы снова получить доступ.")
            except Exception as e:
                print(f"Ошибка при удалении пользователя {user_id}: {e}")
            
            # TODO: Обновить статус в Google Sheets на "⛔ Истёк доступ"

        # 2. Напоминание о скором окончании
        elif end_date - now <= timedelta(days=REMINDER_BEFORE_DAYS):
            try:
                # Отправка напоминания
                await bot.send_message(user_id, 
                    f"⚠️ **Ваш доступ скоро закончится!**\n\n"
                    f"Подписка на канал 'Resonance' истекает **{end_date.strftime('%d.%m.%Y')}**.\n"
                    f"Продлите подписку, чтобы не потерять доступ к каналу.",
                    reply_markup=None # Кнопка для оплаты
                )
            except Exception as e:
                print(f"Ошибка при отправке напоминания {user_id}: {e}")

def setup_scheduler(bot: Bot):
    """Настройка и запуск планировщика задач."""
    scheduler = AsyncIOScheduler()
    # Запускать проверку каждый день в 04:00 AM по времени сервера
    scheduler.add_job(check_and_manage_subscriptions, 'cron', hour=4, minute=0, args=(bot,))
    scheduler.start()
    return scheduler

# Инициализация планировщика в bot.py
# scheduler = setup_scheduler(bot)

feat: add subscription scheduler logic
