# handlers/user_payments.py

import logging
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import SUBSCRIPTION_PRICE
from database.db import get_payment_details
from services.sheets_api import SheetsManager # Импорт для записи в GSheets
from handlers.admin_panel import notify_checker_new_payment # Импорт функции уведомления

router = Router()

# Машина состояний для процесса оплаты
class PaymentProcess(StatesGroup):
    choosing_method = State()
    waiting_for_payment_proof = State()

# --- 1. Вход в процесс оплаты ---

@router.message(F.text == "💳 Оплата подписки")
async def cmd_pay_start(message: types.Message, state: FSMContext):
    """Выводит стоимость и предлагает выбрать метод оплаты."""
    
    await message.answer(
        f"🔮 **Вход в Resonance**\n\n"
        f"Стоимость подписки на месяц: **{SUBSCRIPTION_PRICE} ₸**.\n\n"
        "Выберите удобный способ оплаты:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Kaspi Bank (₸)", callback_data="pay_method:Kaspi"),
                types.InlineKeyboardButton(text="Tinkoff (RUB)", callback_data="pay_method:Tinkoff"),
            ],
            [
                types.InlineKeyboardButton(text="Crypto (USDT TRC-20)", callback_data="pay_method:USDT"),
            ]
        ])
    )
    # Переход в состояние выбора метода (хотя выбор происходит через callback)
    await state.set_state(PaymentProcess.choosing_method)


# --- 2. Выдача реквизитов и запрос чека ---

@router.callback_query(PaymentProcess.choosing_method, F.data.startswith("pay_method"))
async def choose_payment_method(call: types.CallbackQuery, state: FSMContext):
    """Выдает реквизиты оплаты и переводит в режим ожидания чека."""
    await call.answer()
    method = call.data.split(':')[1]
    
    # 1. Получаем реквизиты из БД
    details = await get_payment_details(method)
    
    # 2. Сохраняем выбранный метод в FSM
    await state.update_data(payment_method=method)
    
    text = (
        f"💰 **Оплата через {method}**\n\n"
        f"**Реквизиты:** `{details}`\n\n"
        "**После оплаты:** Отправьте сюда скриншот или фото чека.\n"
        "Администратор подтвердит доступ в течение нескольких минут."
    )
    
    # Редактируем сообщение, чтобы показать реквизиты и запросить чек
    await call.message.edit_text(text,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Я оплатил, готов отправить чек", callback_data="ready_to_send_proof")]
        ])
    )


@router.callback_query(F.data == "ready_to_send_proof")
async def ready_to_send_proof(call: types.CallbackQuery, state: FSMContext):
    """Уведомляет пользователя, что теперь нужно прислать чек."""
    await call.answer()
    
    # 1. Меняем состояние FSM на ожидание доказательства
    await state.set_state(PaymentProcess.waiting_for_payment_proof)
    
    await call.message.edit_text(
        "📸 **Жду ваш чек!**\n\n"
        "Отправьте изображение или документ с подтверждением оплаты."
    )


# --- 3. Прием чека и уведомление админа ---

@router.message(PaymentProcess.waiting_for_payment_proof, F.photo | F.document)
async def process_payment_proof(message: types.Message, state: FSMContext, bot: Bot, sheets_manager: SheetsManager):
    """Принимает чек, сохраняет его ID и уведомляет Венеру."""
    
    data = await state.get_data()
    method = data.get('payment_method', 'N/A')
    
    # Определяем file_id (либо фото, либо документ)
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        # Это не должно произойти из-за фильтра F.photo | F.document
        await message.answer("Пожалуйста, отправьте именно фото или документ.")
        return

    # 1. Уведомление Венеры (Администратора)
    user_id = message.from_user.id
    username = message.from_user.username
    
    await notify_checker_new_payment(
        bot=bot, 
        user_id=user_id, 
        username=username, 
        method=method, 
        file_id=file_id, 
        sheets_manager=sheets_manager
    )

    # 2. Уведомление пользователя
    await message.answer(
        "🥳 **Чек принят на проверку!**\n\n"
        "Администратор (Венера) уже получила ваше подтверждение. "
        "Ожидайте, пожалуйста, уведомления об активации доступа."
    )
    
    # 3. Очистка FSM
    await state.clear()
    
# --- 4. Обработка, если прислали текст вместо чека ---

@router.message(PaymentProcess.waiting_for_payment_proof)
async def process_invalid_proof(message: types.Message):
    """Обрабатывает, если пользователь прислал текст вместо чека."""
    await message.answer(
        "❌ **Неверный формат.**\n\n"
        "Пожалуйста, отправьте именно **скриншот** или **фото** чека/квитанции."
    )
