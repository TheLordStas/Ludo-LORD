from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.economy import get_or_create_user
from database.models import User
from config import ADMINS, START_BALANCE


def is_admin(username: str) -> bool:
    return username in ADMINS


def check_ban(user) -> bool:
    from database.economy import check_ban as _check
    return _check(user)


# --- Команда /money ---
async def set_money(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        if not is_admin(user_data.username):
            await update.message.reply_text("❌ Нет прав администратора!")
            return

        text = update.message.text.strip()
        if text.startswith('/money'):
            parts = text.split()[1:]
        elif text.lower().startswith('мани'):
            parts = text.split()[1:]
        else:
            parts = text.split()[1:]

        if len(parts) < 1:
            await update.message.reply_text("💰 /money [сумма] [@user] или мани 5000 @user")
            return

        try:
            amount = int(parts[0])
        except ValueError:
            await update.message.reply_text("❌ Сумма должна быть числом!")
            return

        # Определяем цель
        if update.message.reply_to_message:
            target_user_id = update.message.reply_to_message.from_user.id
            target_username = update.message.reply_to_message.from_user.username
        elif len(parts) >= 2:
            username = parts[1].replace('@', '')
            # Ищем в БД
            target_user_db = db.query(User).filter_by(username=username).first()
            if not target_user_db:
                await update.message.reply_text("❌ Пользователь не найден!")
                return
            target_user_id = target_user_db.user_id
            target_username = username
        else:
            target_user_id = user_data.id
            target_username = user_data.username

        # Устанавливаем баланс
        user = get_or_create_user(db, target_user_id, target_username)
        user.balance = amount
        db.commit()

        await update.message.reply_text(
            f"✅ Баланс @{user.username} установлен на {amount} монет"
        )
    finally:
        db.close()


async def money_text(update: Update, context: CallbackContext):
    """Текстовый обработчик: мани 5000 @user"""
    parts = update.message.text.strip().split()
    context.args = parts[1:]
    await set_money(update, context)


# --- /setnull (исправлено) ---
async def null_stats(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        if not is_admin(user_data.username):
            await update.message.reply_text("❌ Нет прав!")
            return

        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
        elif context.args:
            username = context.args[0].replace('@', '')
            target_db = db.query(User).filter_by(username=username).first()
            if not target_db:
                await update.message.reply_text("❌ Пользователь не найден!")
                return
            target = target_db
        else:
            target = user_data

        user = get_or_create_user(db, target.id if hasattr(target, 'id') else target.user_id, target.username)
        # Обнуляем игровую статистику и инвентарь, баланс в START_BALANCE
        user.balance = START_BALANCE
        user.cactus = 0.0
        user.faps = 0
        user.games_played = 0
        user.total_bets = 0
        user.total_won = 0
        user.total_lost = 0
        user.shovel_level = 1
        user.lube_count = 0
        user.fertilizer_count = 0
        user.fertilizer_used_this_grow = False
        # Кулдауны сбрасываем
        user.last_grow = None
        user.last_dig = None
        user.last_fap = None
        user.faps_today = 0
        user.fap_day_reset = None
        db.commit()

        await update.message.reply_text(f"✅ Статистика и инвентарь @{user.username} обнулены, баланс = {START_BALANCE}")
    finally:
        db.close()


# --- Бан на игры ---
async def ban_user(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        if not is_admin(user_data.username):
            await update.message.reply_text("❌ Нет прав!")
            return

        text = update.message.text.strip()
        if text.startswith('/ban'):
            parts = text.split()[1:]
        elif text.lower().startswith('бан'):
            parts = text.split()[1:]
        else:
            parts = text.split()[1:]

        if len(parts) < 2:
            await update.message.reply_text("🚫 /ban [@user] [минуты] или бан @user 60")
            return

        username = parts[0].replace('@', '')
        try:
            minutes = int(parts[1])
        except ValueError:
            await update.message.reply_text("❌ Время должно быть числом в минутах!")
            return

        target_user = db.query(User).filter_by(username=username).first()
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден!")
            return

        target_user.banned_until = datetime.utcnow() + timedelta(minutes=minutes)
        db.commit()
        await update.message.reply_text(f"🚫 @{username} забанен на {minutes} минут!")
    finally:
        db.close()


# --- Разбан ---
async def unban_user(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        if not is_admin(update.effective_user.username):
            await update.message.reply_text("❌ Нет прав!")
            return

        if not context.args:
            await update.message.reply_text("Использование: /unban @user")
            return

        username = context.args[0].replace('@', '')
        user = db.query(User).filter_by(username=username).first()
        if not user:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        user.banned_until = None
        db.commit()
        await update.message.reply_text(f"✅ @{username} разбанен!")
    finally:
        db.close()


# --- Ручная выдача VIP ---
async def vip_grant(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        if not is_admin(update.effective_user.username):
            await update.message.reply_text("❌ Нет прав!")
            return

        text = update.message.text.strip()
        if text.startswith('/vip'):
            parts = text.split()[1:]
        elif text.lower().startswith('вип'):
            parts = text.split()[1:]
        else:
            parts = text.split()[1:]

        if len(parts) < 2:
            await update.message.reply_text("Использование: /vip @user [дни]")
            return

        username = parts[0].replace('@', '')
        try:
            days = int(parts[1])
        except ValueError:
            await update.message.reply_text("❌ Дни должны быть числом!")
            return

        user = db.query(User).filter_by(username=username).first()
        if not user:
            await update.message.reply_text("❌ Пользователь не найден!")
            return

        now = datetime.utcnow()
        if user.vip_until and user.vip_until > now:
            user.vip_until += timedelta(days=days)
        else:
            user.vip_until = now + timedelta(days=days)
        user.is_vip = True
        db.commit()
        await update.message.reply_text(f"✅ @{username} получил VIP на {days} дн.")
    finally:
        db.close()


# --- Снятие VIP ---
async def vip_remove(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        if not is_admin(update.effective_user.username):
            await update.message.reply_text("❌ Нет прав!")
            return

        if not context.args:
            await update.message.reply_text("Использование: /setvip @user")
            return

        username = context.args[0].replace('@', '')
        user = db.query(User).filter_by(username=username).first()
        if not user:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        user.is_vip = False
        user.vip_until = None
        db.commit()
        await update.message.reply_text(f"✅ VIP снят с @{username}")
    finally:
        db.close()


async def ban_text(update: Update, context: CallbackContext):
    parts = update.message.text.strip().split()
    context.args = parts[1:]
    await ban_user(update, context)
