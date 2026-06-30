from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.economy import get_or_create_user


async def require_registration(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.username)
        if user.gender is None:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Я парень", callback_data=f"gender:male:{user.user_id}"),
                    InlineKeyboardButton("Я девушка", callback_data=f"gender:female:{user.user_id}"),
                ]
            ])
            msg = await update.message.reply_text(
                "Привет! Перед использованием бота выбери свой пол:",
                reply_markup=keyboard
            )
            from database.helpers import schedule_message_deletion
            await schedule_message_deletion(context, msg.chat_id, msg.message_id, 300)
            return False
        return True
    finally:
        db.close()


async def gender_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split(":")
    gender = data[1]
    user_id = int(data[2])

    # Проверяем, что нажимает именно тот, кому меню предназначено
    if query.from_user.id != user_id:
        await query.answer("Это меню не для тебя! Вызови свою команду /start", show_alert=True)
        return

    db = SessionLocal()
    try:
        user = get_or_create_user(db, user_id, query.from_user.username)
        user.gender = gender
        db.commit()
        await query.answer()
        await query.edit_message_text(f"Пол установлен: {'мужской' if gender == 'male' else 'женский'}")
    finally:
        db.close()
