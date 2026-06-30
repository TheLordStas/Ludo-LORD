import random
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.economy import (
    get_or_create_user, transfer_money, check_cooldown, update_cooldown
)
from database.helpers import is_registered, vip_mention
from config import FAP_MAX_PER_DAY, FAP_MAX_PER_DAY_VIP, SHOVEL_MULTIPLIER
from phrases import *


# ---------- ПЕРЕВОД МОНЕТ ----------
async def transfer_handler(update: Update, context: CallbackContext):
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

        from_user = get_or_create_user(db, update.effective_user.id, update.effective_user.username)
        to_user = get_or_create_user(db, update.message.reply_to_message.from_user.id,
                                     update.message.reply_to_message.from_user.username)
        if not is_registered(from_user) or not is_registered(to_user):
            await update.message.reply_text("Оба пользователя должны быть зарегистрированы!")
            return
        success, message = transfer_money(db, from_user, to_user, amount)
        await update.message.reply_text(
            f"{message}\n💰 Твой баланс: {from_user.balance}\n💰 Баланс {to_user.username}: {to_user.balance}"
        )
    finally:
        db.close()


# ---------- ФАП ----------
async def fap_reply(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        from_user_data = update.effective_user
        to_user_data = update.message.reply_to_message.from_user
        chat_id = update.effective_chat.id

        if to_user_data.id == from_user_data.id:
            await fap_solo(update, context)
            return

        from_user = get_or_create_user(db, from_user_data.id, from_user_data.username)
        to_user = get_or_create_user(db, to_user_data.id, to_user_data.username)

        if not is_registered(from_user) or not is_registered(to_user):
            await update.message.reply_text("Оба должны быть зарегистрированы!")
            return

        # Проверка смазки у вызывающего
        if from_user.lube_count <= 0:
            await update.message.reply_text("❌ У тебя нет смазки! Купи в /shop")
            return

        # Кулдаун
        can_use, remaining = check_cooldown(from_user, 'fap')
        if not can_use:
            minutes = remaining // 60
            seconds = remaining % 60
            await update.message.reply_text(f"⏳ Подожди ещё {minutes}м {seconds}с перед фапом!")
            return

        # Дневной лимит
        now = datetime.utcnow()
        is_vip = from_user.is_vip and from_user.vip_until and from_user.vip_until > now
        max_day = FAP_MAX_PER_DAY_VIP if is_vip else FAP_MAX_PER_DAY
        if from_user.fap_day_reset and now.date() > from_user.fap_day_reset.date():
            from_user.faps_today = 0
            from_user.fap_day_reset = now
        if from_user.faps_today >= max_day:
            await update.message.reply_text(f"🛑 Дневной лимит фапов исчерпан ({max_day}/день)!")
            return

        # Списываем смазку
        from_user.lube_count -= 1
        update_cooldown(db, from_user, 'fap')

        # Выбор фразы по полу
        g1 = from_user.gender
        g2 = to_user.gender
        if g1 == 'male' and g2 == 'male':
            phrases = FAP_REPLY_MALE_TO_MALE
        elif g1 == 'male' and g2 == 'female':
            phrases = FAP_REPLY_MALE_TO_FEMALE
        elif g1 == 'female' and g2 == 'male':
            phrases = FAP_REPLY_FEMALE_TO_MALE
        elif g1 == 'female' and g2 == 'female':
            phrases = FAP_REPLY_FEMALE_TO_FEMALE
        else:
            phrases = FAP_REPLY_MALE_TO_MALE  # fallback

        message = random.choice(phrases).format(
            from_user=vip_mention(from_user),
            to_user=vip_mention(to_user)
        )
        await update.message.reply_text(
            f"{message}\n💕 Фапов у {vip_mention(from_user)}: {from_user.faps}",
            parse_mode='HTML'
        )
    finally:
        db.close()


async def fap_solo(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id
        user = get_or_create_user(db, user_data.id, user_data.username)
        if not is_registered(user):
            await update.message.reply_text("Сначала выбери пол!")
            return
        if user.lube_count <= 0:
            await update.message.reply_text("❌ У тебя нет смазки! Купи в /shop")
            return

        can_use, remaining = check_cooldown(user, 'fap')
        if not can_use:
            minutes = remaining // 60
            seconds = remaining % 60
            await update.message.reply_text(f"⏳ Подожди ещё {minutes}м {seconds}с перед фапом!")
            return

        now = datetime.utcnow()
        is_vip = user.is_vip and user.vip_until and user.vip_until > now
        max_day = FAP_MAX_PER_DAY_VIP if is_vip else FAP_MAX_PER_DAY
        if user.fap_day_reset and now.date() > user.fap_day_reset.date():
            user.faps_today = 0
            user.fap_day_reset = now
        if user.faps_today >= max_day:
            await update.message.reply_text(f"🛑 Дневной лимит фапов исчерпан ({max_day}/день)!")
            return

        user.lube_count -= 1
        update_cooldown(db, user, 'fap')

        if user.gender == 'male':
            phrases = FAP_SOLO_MALE
        else:
            phrases = FAP_SOLO_FEMALE
        message = random.choice(phrases).format(user=vip_mention(user))
        await update.message.reply_text(
            f"{message}\n💕 Фапов сегодня: {user.faps_today}/{max_day}\n💕 Всего: {user.faps}",
            parse_mode='HTML'
        )
    finally:
        db.close()


# ---------- РАСТИТЬ КАКТУС ----------
async def grow(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.username)
        if not is_registered(user):
            await update.message.reply_text("Сначала выбери пол!")
            return
        can_use, remaining = check_cooldown(user, 'grow')
        if not can_use:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await update.message.reply_text(f"⏳ Кактус уже полит! Подожди ещё {hours}ч {minutes}м")
            return

        growth = random.uniform(1, 12)
        user.cactus += growth
        # Сброс флага удобрения при новом росте
        user.fertilizer_used_this_grow = False
        update_cooldown(db, user, 'grow')

        if user.gender == 'male':
            phrases = GROW_MALE
        else:
            phrases = GROW_FEMALE
        message = random.choice(phrases).format(user=vip_mention(user))
        await update.message.reply_text(f"{message}\n📈 +{growth:.1f} см\n🌵 Размер кактуса: {user.cactus:.1f} см",
                                        parse_mode='HTML')
    finally:
        db.close()


# ---------- КОПАТЬ МОНЕТЫ ----------
async def dig(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.username)
        if not is_registered(user):
            await update.message.reply_text("Сначала выбери пол!")
            return

        can_use, remaining = check_cooldown(user, 'dig')
        if not can_use:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await update.message.reply_text(f"⏳ Ты уже копал! Подожди ещё {hours}ч {minutes}м")
            return

        # Базовые монеты
        base_coins = random.randint(1000, 10000)
        # Бонус от лопаты (каждый уровень удваивает награду)
        multiplier = SHOVEL_MULTIPLIER ** (user.shovel_level - 1)
        coins = int(base_coins * multiplier)

        user.balance += coins
        update_cooldown(db, user, 'dig')

        # Выбор фразы по полу и сумме
        is_male = user.gender == 'male'
        if coins <= 10000:
            phrases = DIG_VERY_SMALL_MALE if is_male else DIG_VERY_SMALL_FEMALE
        elif coins <= 50000:
            phrases = DIG_SMALL_MALE if is_male else DIG_SMALL_FEMALE
        elif coins <= 250000:
            phrases = DIG_MEDIUM_MALE if is_male else DIG_MEDIUM_FEMALE
        elif coins <= 1000000:
            phrases = DIG_BIG_MALE if is_male else DIG_BIG_FEMALE
        else:
            phrases = DIG_LARGE_MALE if is_male else DIG_LARGE_FEMALE

        message = random.choice(phrases).format(user=vip_mention(user))
        await update.message.reply_text(
            f"⛏️ {message}\n💰 +{coins} монет!\n💰 Баланс: {user.balance}",
            parse_mode='HTML'
        )
    finally:
        db.close()
