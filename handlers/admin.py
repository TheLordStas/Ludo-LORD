from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.models import User
from services.economy import get_or_create_user
from config import ADMINS


def is_admin(username: str) -> bool:
    return username in ADMINS


def check_ban(user: User) -> bool:
    if user.banned_until and user.banned_until > datetime.utcnow():
        return True
    return False


async def set_money(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user

        if not is_admin(user_data.username):
            await update.message.reply_text("❌ Нет прав администратора!")
            return

        # Определяем цель и сумму из аргументов или текста
        text = update.message.text.strip()

        # Убираем команду
        if text.startswith('/money'):
            parts = text.split()[1:]  # аргументы после /money
        elif text.lower().startswith('мани'):
            parts = text.split()[1:]  # аргументы после "мани"
        else:
            parts = text.split()[1:]

        if len(parts) < 1:
            await update.message.reply_text("💰 /money [сумма] [@user] или мани [сумма] [@user]")
            return

        try:
            amount = int(parts[0])
        except ValueError:
            await update.message.reply_text("❌ Сумма должна быть числом!")
            return

        # Определяем цель
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
        elif len(parts) >= 2:
            username = parts[1].replace('@', '')
            target_user_db = db.query(User).filter_by(
                username=username, chat_id=update.effective_chat.id
            ).first()
            if not target_user_db:
                await update.message.reply_text("❌ Пользователь не найден!")
                return
            try:
                target_user = await update.effective_chat.get_member(target_user_db.user_id)
                target_user = target_user.user
            except:
                await update.message.reply_text("❌ Не удалось получить пользователя!")
                return
        else:
            target_user = user_data

        user = get_or_create_user(db, target_user.id, update.effective_chat.id, target_user.username)
        user.balance = amount
        db.commit()

        await update.message.reply_text(
            f"✅ Баланс {target_user.mention_html()} установлен на {amount} монет",
            parse_mode='HTML'
        )
    finally:
        db.close()


async def null_stats(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user

        if not is_admin(user_data.username):
            await update.message.reply_text("❌ Нет прав!")
            return

        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
        elif context.args:
            username = context.args[0].replace('@', '')
            target_user_db = db.query(User).filter_by(
                username=username, chat_id=update.effective_chat.id
            ).first()
            if not target_user_db:
                await update.message.reply_text("❌ Пользователь не найден!")
                return
            try:
                target_user = await update.effective_chat.get_member(target_user_db.user_id)
                target_user = target_user.user
            except:
                await update.message.reply_text("❌ Не удалось получить пользователя!")
                return
        else:
            target_user = user_data

        user = get_or_create_user(db, target_user.id, update.effective_chat.id, target_user.username)
        user.games_played = 0
        user.total_bets = 0
        user.total_won = 0
        user.total_lost = 0
        db.commit()

        await update.message.reply_text(
            f"✅ Статистика {target_user.mention_html()} обнулена!",
            parse_mode='HTML'
        )
    finally:
        db.close()


async def ban_user(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user

        if not is_admin(user_data.username):
            await update.message.reply_text("❌ Нет прав!")
            return

        # Парсим аргументы
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

        target_user_db = db.query(User).filter_by(
            username=username, chat_id=update.effective_chat.id
        ).first()

        if not target_user_db:
            await update.message.reply_text("❌ Пользователь не найден в чате!")
            return

        target_user_db.banned_until = datetime.utcnow() + timedelta(minutes=minutes)
        db.commit()

        await update.message.reply_text(f"🚫 @{username} забанен на {minutes} минут!")
    finally:
        db.close()


async def ban_text(update: Update, context: CallbackContext):
    """Текстовый обработчик: бан @user 60"""
    # Перенаправляем в ban_user
    parts = update.message.text.strip().split()
    context.args = parts[1:]
    await ban_user(update, context)


async def money_text(update: Update, context: CallbackContext):
    """Текстовый обработчик: мани 5000 @user"""
    parts = update.message.text.strip().split()
    context.args = parts[1:]
    await set_money(update, context)
