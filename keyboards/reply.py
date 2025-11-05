# keyboards/reply.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🧘 Описание Анжелики"),
            KeyboardButton(text="📅 Записаться на консультацию"),
        ],
        [
            KeyboardButton(text="🔮 Войти в Resonance"),
            KeyboardButton(text="💳 Оплата подписки"),
        ],
        [
            KeyboardButton(text="🧾 Проверить статус"),
            KeyboardButton(text="❓ Задать вопрос (/ask)"),
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие в Resonance Assistant"
)

feat: add reply keyboard for main menu
