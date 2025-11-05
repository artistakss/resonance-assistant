import logging
from aiogram import Router, F, Bot, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ALLOWED_ADMINS, CHECKER_ID, SUBSCRIPTION_PRICE
from database.db import (
    get_user, activate_subscription, get_payment_details, 
    update_payment_details, get_all_active_users, get_users_about_to_expire
)
from services.sheets_api import SheetsManager

# Инициализация роутера
router = Router()

# Ограничение доступа только для админов
router.message.filter(F.from_user.id.in_(ALLOWED_ADMINS))
router.callback_query.filter(F.from_user.id.in_(ALLOWED_ADMINS))

# Машина состояний для обновления реквизитов
class PaymentDetailsUpdate(StatesGroup):
    choosing_method = State()
    waiting_for_details = State()

# --- 1. Главная Админ-панель ---
from aiogram.dispatcher.filters import Command
@router.message_handler(Command("admin"))
async def cmd_admin(message: types.Message):
    """Выводит главное меню администратора."""
    text = (
        "👑 **Административная Панель Resonance Assistant**\n\n"
        "Выберите действие:"
    )
    # Кнопки для Админа (Анжелика) и Проверяющего (Венера)
    admin_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💳 Обновить Реквизиты", callback_data="admin_update_details")],
        [types.InlineKeyboardButton(text="👥 Список Подписчиков", callback_data="admin_list_subs")],
        [types.InlineKeyboardButton(text="⏳ Скоро истекает", callback_data="admin_list_expiring")],
    ])
    
    await message.answer(text, reply_markup=admin_markup)


# --- 2. Логика Подтверждения/Отклонения Чеков (Венера) ---

# Эта функция вызывается из `handlers/user_payments.py`, когда пользователь отправляет чек.
async def notify_checker_new_payment(bot: Bot, user_id: int, username: str, method: str, file_id: str, sheets_manager: SheetsManager):
    """Отправляет Венере уведомление о новом чеке и сохраняет в Google Sheets."""
    
    # 1. Запись в Google Sheets
    try:
        # Получаем номер строки, чтобы потом обновить статус
        row_index = sheets_manager.log_payment_check(user_id, username, method, file_id)
    except Exception as e:
        logging.error(f"Ошибка записи чека в Google Sheets: {e}")
        await bot.send_message(CHECKER_ID, f"⚠️ Ошибка записи чека в Sheets от {username}: {e}")
        return

    # 2. Отправка медиа (чека) и уведомление
    caption = (
        f"💸 **НОВЫЙ ЧЕК НА ПРОВЕРКЕ!**\n"
        f"От: @{username} (ID: `{user_id}`)\n"
        f"Метод: **{method}**\n"
        f"Сумма: **{SUBSCRIPTION_PRICE} ₸**\n\n"
        f"Номер строки в Sheets для обновления: `{row_index}`"
    )
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Подтвердить Доступ", callback_data=f"confirm_payment:{user_id}:{row_index}"),
            types.InlineKeyboardButton(text="❌ Отклонить Оплату", callback_data=f"reject_payment:{user_id}:{row_index}")
        ]
    ])
    
    try:
        # Отправляем чек как фото/документ
        await bot.send_photo(CHECKER_ID, photo=file_id, caption=caption, reply_markup=markup)
    except Exception as e:
        # Если не удалось отправить фото, отправляем просто текст с file_id
        await bot.send_message(CHECKER_ID, f"⚠️ Не удалось отправить чек-фото. ID: {file_id}\n{caption}", reply_markup=markup)


@router.callback_query_handler(F.data.startswith("confirm_payment"))
async def process_confirm_payment(call: types.CallbackQuery, bot: Bot, sheets_manager: SheetsManager):
    """Обрабатывает подтверждение оплаты (нажимает Венера)."""
    # Удаляем кнопки после нажатия
    await call.message.edit_reply_markup(reply_markup=None) 
    
    try:
        _, user_id_str, row_index_str = call.data.split(':')
        user_id = int(user_id_str)
        row_index = int(row_index_str)
        
        # 1. Активация подписки в БД
        start_date, end_date = await activate_subscription(user_id)
        user = await get_user(user_id)
        
        # 2. Добавление пользователя в закрытый канал
        # NOTE: Добавление должно происходить через пригласительную ссылку,
        # или бот должен быть админом канала с правом приглашать.
        # В данном случае, отправляем пользователю пригласительную ссылку.
        # Для автоматического добавления (если бот - админ) нужно использовать 
        # API createChatInviteLink или unban_chat_member.
        
        # 3. Обновление статуса в Google Sheets
        sheets_manager.update_check_status(row_index, '✅ Подтверждено', start_date, end_date)
        
        # 4. Уведомление пользователя
        await bot.send_message(user_id, 
            f"✅ **Оплата подтверждена!**\n\n"
            f"Ваш доступ к каналу 'Resonance' активирован до **{end_date.strftime('%d.%m.%Y')}**.\n"
            f"Вот ваша **пригласительная ссылка** для входа: *[Ссылка на канал]*", # TODO: Вставьте ссылку
            disable_web_page_preview=True
        )
        
        await call.message.answer(
            f"✅ **Подписка для @{user['username']} (ID: {user_id}) активирована!**\n"
            f"Статус в Google Sheets (строка {row_index}) обновлен."
        )

    except Exception as e:
        logging.error(f"Ошибка при подтверждении оплаты: {e}")
        await call.message.answer(f"⚠️ **Критическая ошибка при подтверждении оплаты:** {e}")

# ... (Аналогично можно реализовать process_reject_payment)


# --- 3. Обновление Реквизитов Оплаты ---

@router.callback_query_handler(F.data == "admin_update_details")
async def choose_method_for_update(call: types.CallbackQuery, state: FSMContext):
    """Шаг 1: Выбор метода оплаты для обновления."""
    await call.message.edit_text("🔄 **Обновление Реквизитов Оплаты**\n\nВыберите метод, который хотите обновить:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Kaspi", callback_data="update_method:Kaspi"),
                types.InlineKeyboardButton(text="Tinkoff", callback_data="update_method:Tinkoff"),
                types.InlineKeyboardButton(text="USDT (TRC-20)", callback_data="update_method:USDT")
            ],
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
        ])
    )
    await state.set_state(PaymentDetailsUpdate.choosing_method)


@router.callback_query_handler(PaymentDetailsUpdate.choosing_method, F.data.startswith("update_method"))
async def start_details_input(call: types.CallbackQuery, state: FSMContext):
    """Шаг 2: Запрос новых реквизитов."""
    method = call.data.split(':')[1]
    
    # Получаем текущие реквизиты
    current_details = await get_payment_details(method)
    
    await state.update_data(method=method)
    await call.message.edit_text(
        f"📝 **Ввод новых реквизитов для {method}**\n\n"
        f"Текущие реквизиты: `{current_details}`\n\n"
        "Отправьте новое значение (ссылку, номер карты или кошелек):"
    )
    await state.set_state(PaymentDetailsUpdate.waiting_for_details)


@router.message_handler(PaymentDetailsUpdate.waiting_for_details)
async def finalize_details_update(message: types.Message, state: FSMContext):
    """Шаг 3: Сохранение новых реквизитов в БД."""
    new_details = message.text.strip()
    data = await state.get_data()
    method = data['method']
    
    # Обновление в БД
    await update_payment_details(method, new_details)
    
    await message.answer(
        f"✅ **Реквизиты {method} успешно обновлены!**\n"
        f"Новое значение: `{new_details}`",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.clear()
    await cmd_admin(message) # Возвращаемся в админ-панель
    
# --- 4. Просмотр отчетов ---

@router.callback_query_handler(F.data == "admin_list_subs")
async def list_active_subscribers(call: types.CallbackQuery):
    """Выводит список активных подписчиков."""
    users = await get_all_active_users()
    if not users:
        await call.answer("Нет активных подписчиков.", show_alert=True)
        return
    
    report = "👥 **АКТИВНЫЕ ПОДПИСЧИКИ** (только 10 первых):\n\n"
    for i, user in enumerate(users[:10]):
        end_date = datetime.fromisoformat(user['sub_end_date']).strftime('%d.%m.%Y')
        report += (
            f"**{i+1}.** @{user['username'] or 'N/A'} (ID: `{user['user_id']}`)\n"
            f"Истекает: **{end_date}**\n"
        )
    
    # TODO: Добавить кнопки для ручного продления/удаления
    await call.message.edit_text(report, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
    ]))


@router.callback_query_handler(F.data == "admin_list_expiring")
async def list_expiring_subscribers(call: types.CallbackQuery):
    """Выводит список подписчиков, у которых скоро истекает срок."""
    # NOTE: В db.py нужно реализовать get_users_about_to_expire
    await call.answer("Функция скоро будет реализована! (Проверка пользователей, срок которых истекает)", show_alert=True)

feat: add full admin panel logic
