import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.models import User
from services.economy import get_or_create_user, transfer_money, check_cooldown, update_cooldown
from config import *


# ============ ПЕРЕВОД МОНЕТ ============
async def transfer_handler(update: Update, context: CallbackContext):
    """Обработчик перевода монет через reply"""
    db = SessionLocal()
    try:
        if not update.message.reply_to_message:
            return

        text = update.message.text.strip()
        if not text.startswith('+'):
            return

        try:
            amount = int(text[1:])
        except ValueError:
            return

        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной!")
            return

        from_user_data = update.effective_user
        to_user_data = update.message.reply_to_message.from_user
        chat_id = update.effective_chat.id

        if to_user_data.id == from_user_data.id:
            await update.message.reply_text("❌ Нельзя перевести монеты самому себе!")
            return

        if to_user_data.is_bot:
            await update.message.reply_text("❌ Нельзя перевести монеты боту!")
            return

        from_user = get_or_create_user(db, from_user_data.id, chat_id, from_user_data.username)
        to_user = get_or_create_user(db, to_user_data.id, chat_id, to_user_data.username)

        success, message = transfer_money(db, from_user, to_user, amount)
        await update.message.reply_text(
            f"{message}\n"
            f"💰 Твой баланс: {from_user.balance}\n"
            f"💰 Баланс {to_user_data.mention_html()}: {to_user.balance}",
            parse_mode='HTML'
        )
    finally:
        db.close()


# ============ ФАП ============
FAP_REPLY_MESSAGES = [
    "{from_user} подрочил и спустил на лицо {to_user} 💦",
    "{from_user} кончил на {to_user}, какое блаженство! 😱💦",
    "{from_user} обкончал {to_user} с ног до головы! 💦💦💦",
    "{from_user} не сдержался и залил {to_user} своей любовью 💦❤️",
    "О да! {from_user} снова спустил на {to_user}! 💦😈",
]

FAP_SOLO_MESSAGES = [
    "{user} нашёл классный видос на порносайте и хорошенько подрочил 💦🔞",
    "{user} уединился в туалете... через 5 минут вышел довольный 💦😏",
    "{user} включил режим инкогнито и... ну вы поняли 💦🫣",
    "{user} вспомнил свою бывшую и грустно подрочил 💦😢",
    "{user} нашёл новую коллекцию хентая и пропал на час 💦🎌",
    "{user} дрочит как не в себя! Рекорд по фапу! 💦🏆",
    "Соседи {user} вызвали полицию из-за подозрительных звуков 💦🚔",
]


async def fap_reply(update: Update, context: CallbackContext):
    """Обработчик фапа через reply"""
    db = SessionLocal()
    try:
        from_user_data = update.effective_user
        to_user_data = update.message.reply_to_message.from_user
        chat_id = update.effective_chat.id

        if to_user_data.id == from_user_data.id:
            # Если на себя - считаем как соло
            await fap_action(update, context, db, from_user_data, chat_id, solo=True)
            return

        user = get_or_create_user(db, from_user_data.id, chat_id, from_user_data.username)

        # Проверка кулдауна
        can_use, remaining = check_cooldown(user, 'fap', minutes=FAP_COOLDOWN_MINUTES)
        if not can_use:
            minutes = remaining // 60
            seconds = remaining % 60
            await update.message.reply_text(
                f"⏳ Ты уже фапал недавно! Подожди ещё {minutes}м {seconds}с"
            )
            return

        # Проверка дневного лимита
        now = datetime.utcnow()
        if user.fap_day_reset and now.date() > user.fap_day_reset.date():
            user.faps_today = 0
            user.fap_day_reset = now

        if user.faps_today >= FAP_MAX_PER_DAY:
            await update.message.reply_text(
                f"🛑 Дневной лимит фапов исчерпан ({FAP_MAX_PER_DAY}/день)! "
                f"Приходи завтра, дрочер 😏"
            )
            return

        update_cooldown(db, user, 'fap')

        to_user = get_or_create_user(db, to_user_data.id, chat_id, to_user_data.username)

        message = random.choice(FAP_REPLY_MESSAGES).format(
            from_user=from_user_data.mention_html(),
            to_user=to_user_data.mention_html()
        )

        await update.message.reply_text(
            f"{message}\n"
            f"💕 Фапов у {from_user_data.first_name}: {user.faps}",
            parse_mode='HTML'
        )
    finally:
        db.close()


async def fap_solo(update: Update, context: CallbackContext):
    """Обработчик соло фапа"""
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id
        await fap_action(update, context, db, user_data, chat_id, solo=True)
    finally:
        db.close()


async def fap_action(update, context, db, user_data, chat_id, solo=False):
    user = get_or_create_user(db, user_data.id, chat_id, user_data.username)

    # Проверка кулдауна
    can_use, remaining = check_cooldown(user, 'fap', minutes=FAP_COOLDOWN_MINUTES)
    if not can_use:
        minutes = remaining // 60
        seconds = remaining % 60
        await update.message.reply_text(
            f"⏳ Эй, дрочер! Подожди ещё {minutes}м {seconds}с перед следующим фапом!"
        )
        return

    # Проверка дневного лимита
    now = datetime.utcnow()
    if user.fap_day_reset and now.date() > user.fap_day_reset.date():
        user.faps_today = 0
        user.fap_day_reset = now

    if user.faps_today >= FAP_MAX_PER_DAY:
        await update.message.reply_text(
            f"🛑 Дневной лимит фапов исчерпан ({FAP_MAX_PER_DAY}/день)! "
            f"Твой член больше не выдержит 😏"
        )
        return

    update_cooldown(db, user, 'fap')

    message = random.choice(FAP_SOLO_MESSAGES).format(
        user=user_data.mention_html()
    )

    await update.message.reply_text(
        f"{message}\n"
        f"💕 Фапов сегодня: {user.faps_today}/{FAP_MAX_PER_DAY}\n"
        f"💕 Всего фапов: {user.faps}",
        parse_mode='HTML'
    )


# ============ ПРОФИЛЬ ============
async def profile(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id

        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
        else:
            target_user = user_data

        user = get_or_create_user(db, target_user.id, chat_id, target_user.username)

        total_games_result = user.total_won + user.total_lost
        winrate = (user.total_won / total_games_result * 100) if total_games_result > 0 else 0

        profile_text = (
            f"👤 Профиль {target_user.mention_html()}\n\n"
            f"💰 Баланс: {user.balance} монет\n"
            f"🌵 Кактус: {user.cactus:.1f} см\n"
            f"💕 Фапов: {user.faps}\n\n"
            f"🎮 Статистика игр:\n"
            f"├ Сыграно раз: {user.games_played}\n"
            f"├ Сумма ставок: {user.total_bets}\n"
            f"├ Выиграно: {user.total_won}\n"
            f"├ Проиграно: {user.total_lost}\n"
            f"└ Винрейт: {winrate:.1f}%\n"
        )

        if user.banned_until and user.banned_until > datetime.utcnow():
            remaining = user.banned_until - datetime.utcnow()
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            profile_text += f"\n🚫 БАН до: {user.banned_until.strftime('%d.%m.%Y %H:%M')} (ещё {hours}ч {minutes}м)"

        await update.message.reply_text(profile_text, parse_mode='HTML')
    finally:
        db.close()


# ============ РАСТИТЬ КАКТУС ============
GROW_MESSAGES = [
    "Ты полил кактус 🌵💧",
    "Ты поговорил с кактусом 🌵💬",
    "Ты поставил кактус на солнце 🌵☀️",
    "Ты спел кактусу колыбельную 🌵🎵",
    "Ты удобрил кактус 🌵💩",
    "Кактус послушал твои проблемы и подрос 🌵😢",
]


async def grow(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id

        user = get_or_create_user(db, user_data.id, chat_id, user_data.username)

        can_use, remaining = check_cooldown(user, 'grow', hours=GROW_COOLDOWN_HOURS)
        if not can_use:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await update.message.reply_text(
                f"⏳ Кактус уже полит! Подожди ещё {hours}ч {minutes}м"
            )
            return

        growth = random.uniform(1, 12)
        user.cactus += growth
        update_cooldown(db, user, 'grow')

        message = random.choice(GROW_MESSAGES)

        await update.message.reply_text(
            f"{message}\n"
            f"📈 +{growth:.1f} см\n"
            f"🌵 Размер кактуса: {user.cactus:.1f} см"
        )
    finally:
        db.close()


# ============ КОПАТЬ МОНЕТЫ ============
DIG_MESSAGES_SMALL = [
    "Ты нашёл горсть монет в песочнице 🪙",
    "Под скамейкой валялась мелочь 🪙",
    "Ты проверил карманы старой куртки 🪙",
    "Монетка завалялась под диваном 🪙",
]

DIG_MESSAGES_MEDIUM = [
    "Ты нашёл заначку бабушки! 💰",
    "Клад в собственном огороде! 💰",
    "Ты откопал старый кошелёк 💰",
    "Ты выкопал медный кабель 💰",
]

DIG_MESSAGES_LARGE = [
    "ТЫ ОТКОПАЛ СУНДУК ПИРАТОВ! 🏴‍☠️💎",
    "Нефть! Ты нашёл нефть! 🛢️💰💰",
    "Биткоин-кошелёк с 2013 года! 🚀💎",
    "Ты нашёл чемодан с деньгами! 💼💵💵",
    "Клад Чингисхана! Легенды не врали! 👑💎",
]


async def dig(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id

        user = get_or_create_user(db, user_data.id, chat_id, user_data.username)

        can_use, remaining = check_cooldown(user, 'dig', hours=DIG_COOLDOWN_HOURS)
        if not can_use:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await update.message.reply_text(
                f"⏳ Ты уже копал! Подожди ещё {hours}ч {minutes}м"
            )
            return

        coins = random.randint(100, 5000)
        user.balance += coins
        update_cooldown(db, user, 'dig')

        if coins <= 1000:
            message = random.choice(DIG_MESSAGES_SMALL)
        elif coins <= 3000:
            message = random.choice(DIG_MESSAGES_MEDIUM)
        else:
            message = random.choice(DIG_MESSAGES_LARGE)

        await update.message.reply_text(
            f"⛏️ {user_data.mention_html()} копает...\n"
            f"{message}\n"
            f"💰 +{coins} монет!\n"
            f"💰 Баланс: {user.balance}",
            parse_mode='HTML'
        )
    finally:
        db.close()
