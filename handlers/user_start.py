# handlers/user_start.py
from aiogram import Router, types
from keyboards.reply import main_menu_keyboard

router = Router()

@router.message(F.text == "🧘 Описание Анжелики")
async def handle_description(message: types.Message):
    await message.answer(
        "✨ **Анжелика — специалист по саморазвитию и осознанности.**\n\n"
        "Её миссия — помогать людям находить внутренний резонанс и гармонию. "
        "Она проводит онлайн и оффлайн консультации по проработке блоков и "
        "управлению энергией. Присоединяйтесь к пути осознанности!"
    )

# ... (Добавьте обработчики для других кнопок главного меню, кроме тех, что ведут в FSM)

feat: add main menu handlers
