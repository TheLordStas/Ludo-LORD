from telegram import Update
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.economy import get_or_create_user
from database.helpers import vip_mention, is_registered
from datetime import datetime

START_TEXT = """
🎮 Привет, {username}!

Я — Ludo LORD v2.0! Ваш игровой бот.
Вот что я умею:

🎰 ИГРЫ:
• БАНДИТ [ставка] — Слот-машина (джекпот x50!)
• РУЛЕТКА — Европейская рулетка (0-36)
• МИНЫ [ставка] — Сапёр с яблоками
• ДУЭЛЬ [ставка] — Дуэль на кубиках (ответом)
• УДВОИТЬ [ставка] — Удвоение (50%)
• ТРЕЙД [ставка] — График x0..x5

🌵 ЭКОНОМИКА:
• /grow — Растить кактус
• /dig — Копать монеты
• /profile — Твой профиль
• /shop — Магазин

💕 ИНТЕРАКТИВ:
• ФАП — Подрочить (нужна смазка)
• +500 — Перевести монеты (ответом)

🏆 ТОПЫ:
• /topmoney — Богачи
• /topgrow — Кактусоводы
• /topfap — Фаперы

💎 ДОНАТ: /donate 
 Реквизиты для поддержания проекта - 2202 2085 4171 2288
 По всем вопросам и багам - @TheLordStas
"""

HELP_TEXT = """
📖 СПРАВКА ПО КОМАНДАМ:

🎰 СЛОТЫ — /slots [ставка]
3 барабана, 8 эмодзи. 💀 = проигрыш.

🎡 РУЛЕТКА — /roulette [ставка] + меню
Типы: число x35, диапазон x3, цвет x2, зеро x14

💣 МИНЫ — /mines [ставка]
Поле 5x5, 5 мин. Открывай яблоки.

🎲 КУБИК — /dice [ставка] ответом
🎯 УДВОЕНИЕ — /double [ставка]
📈 ТРЕЙД — /trade [ставка]

💎 VIP — сокращённые кулдауны, бонусы в играх.
🛒 /shop — смазка, удобрения, лопата
💕 ФАП — нужно иметь смазку (покупается в магазине)
🌵 /grow — кактус, /dig — копать (лопата даёт множитель)
"""


async def start(update: Update, context: CallbackContext):
    username = update.effective_user.first_name
    await update.message.reply_text(START_TEXT.format(username=username))
    # Проверка регистрации
    db = SessionLocal()
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.username)
        if not is_registered(user):
            from handlers.registration import require_registration
            await require_registration(update, context)
    finally:
        db.close()


async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(HELP_TEXT)


async def balance(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
        else:
            target = update.effective_user
        user = get_or_create_user(db, target.id, target.username)
        display = vip_mention(user)
        await update.message.reply_text(f"💰 Баланс {display}: {user.balance} монет", parse_mode='HTML')
    finally:
        db.close()


async def profile(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
        else:
            target = update.effective_user
        user = get_or_create_user(db, target.id, target.username)

        total_games_result = user.total_won + user.total_lost
        winrate = (user.total_won / total_games_result * 100) if total_games_result > 0 else 0
        display = vip_mention(user)
        text = (
            f"👤 Профиль {display}\n\n"
            f"💰 Баланс: {user.balance} монет\n"
            f"🌵 Кактус: {user.cactus:.1f} см\n"
            f"💕 Фапов: {user.faps}\n"
            f"🛒 Смазка: {user.lube_count} шт.\n"
            f"🌿 Удобрения: {user.fertilizer_count} шт.\n"
            f"⛏ Лопата: ур. {user.shovel_level}\n\n"
            f"🎮 Статистика игр:\n"
            f"├ Сыграно: {user.games_played}\n"
            f"├ Ставок: {user.total_bets}\n"
            f"├ Выиграно: {user.total_won}\n"
            f"├ Проиграно: {user.total_lost}\n"
            f"└ Винрейт: {winrate:.1f}%\n"
        )
        if user.banned_until and user.banned_until > datetime.utcnow():
            remaining = user.banned_until - datetime.utcnow()
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            text += f"\n🚫 БАН до: {user.banned_until.strftime('%d.%m.%Y %H:%M')} (ещё {hours}ч {minutes}м)"
        await update.message.reply_text(text, parse_mode='HTML')
    finally:
        db.close()
