from telegram import Update
from telegram.ext import CallbackContext
from database.db import SessionLocal
from services.economy import get_or_create_user

START_TEXT = """
🎮 Привет, {username}!

Я — Ludo LORD v1.1.5 (beta)! 
Ваш игровой бот для этого чата! 
Вот что я умею:

🎰 ИГРЫ:
• БАНДИТ [ставка] — Слот-машина (джекпот x50!)
• РУЛЕТКА — Европейская рулетка (0-36)
• МИНЫ [ставка] — Сапёр с яблоками
• ДУЭЛЬ [ставка] — Дуэль на кубиках (ответом на сообщение)
• УДВОИТЬ [ставка] — Удвоение суммы ставки с шансом 50%

🌵 ЭКОНОМИКА:
• /grow — Растить кактус (раз в 24ч, +1-12см)
• /dig — Копать монеты (раз в 4ч, 100-5000)
• /profile — Твой профиль и статистика

💕 ИНТЕРАКТИВ:
• ФАП — Подрочить (раз в 15 мин, макс 20/день)
• +500 — Перевести монеты (ответом на сообщение)

🏆 ТОПЫ:
• /topmoney — Топ богачей
• /topgrow — Топ кактусоводов
• /topfap — Топ фаперов

💰 Стартовый баланс: 5000 монет
"""

HELP_TEXT = """
📖 СПРАВКА ПО КОМАНДАМ:

🎰 СЛОТЫ — /slots [ставка]
3 барабана, 8 эмодзи. 💀 = проигрыш. 7️7️7️ Джекпот x50!

🎡 РУЛЕТКА — /roulette [тип] [ставка] [параметр]
Типы ставок:
• число [0-36] — x35
• диапазон [1/2/3] — x3 (1-12/13-24/25-36)
• цвет [red/black] — x2
• зеро — x14

💣 МИНЫ — /mines [ставка]
Поле 5x5, 5 мин. Открывай яблоки — множитель растёт!

🎲 КУБИК — /dice [ставка]
Ответь на сообщение соперника. У кого больше — забирает банк.

🎯 УДВОЕНИЕ — /double [ставка]
Шанс 50% удвоить ставку.

🌵 /grow — Растить кактус (24ч)
⛏️ /dig — Копать монеты (4ч)
💰 /balance — Проверить баланс
📊 /profile — Профиль и статистика
💕 фап — Подрочить (соло или ответом)
💸 +[сумма] — Перевести (ответом)
"""


# 🛡️ АДМИНКА (для админов):
# • /money [сумма] [@user] — установить баланс
# • /setnull [@user] — обнулить статистику
# • /ban [@user] [минуты] — бан на игры


async def start(update: Update, context: CallbackContext):
    username = update.effective_user.first_name
    await update.message.reply_text(START_TEXT.format(username=username))


async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(HELP_TEXT)


async def balance(update: Update, context: CallbackContext):
    """Показывает баланс пользователя"""
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id

        # Если ответ на сообщение — показываем баланс того пользователя
        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
        else:
            target = user_data

        user = get_or_create_user(db, target.id, chat_id, target.username)

        await update.message.reply_text(
            f"💰 Баланс {target.mention_html()}: {user.balance} монет",
            parse_mode='HTML'
        )
    finally:
        db.close()
