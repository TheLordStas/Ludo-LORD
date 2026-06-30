from telegram import Update
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.models import User, ChatMember
from config import ADMINS
from sqlalchemy import desc


async def top_fap(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        chat_id = update.effective_chat.id
        # Фап глобальный, но топ по чату – показываем пользователей чата
        members = db.query(ChatMember).filter_by(chat_id=chat_id).all()
        user_ids = [m.user_id for m in members]
        if not user_ids:
            await update.message.reply_text("💕 Топ фаперов пуст!")
            return
        top = db.query(User).filter(User.user_id.in_(user_ids)).order_by(desc(User.faps)).limit(10).all()
        if not top:
            await update.message.reply_text("💕 Топ фаперов пуст!")
            return
        text = "💕 ТОП-10 ФАПЕРОВ ЧАТА:\n\n"
        for i, user in enumerate(top, 1):
            medal = {1:'🥇',2:'🥈',3:'🥉'}.get(i, f'{i}.')
            username = user.username or str(user.user_id)
            text += f"{medal} @{username} — {user.faps} фапов\n"
        await update.message.reply_text(text)
    finally:
        db.close()


async def top_grow(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        chat_id = update.effective_chat.id
        members = db.query(ChatMember).filter_by(chat_id=chat_id).all()
        user_ids = [m.user_id for m in members]
        if not user_ids:
            await update.message.reply_text("🌵 Топ кактусоводов пуст!")
            return
        top = db.query(User).filter(User.user_id.in_(user_ids)).order_by(desc(User.cactus)).limit(10).all()
        if not top:
            await update.message.reply_text("🌵 Топ кактусоводов пуст!")
            return
        text = "🌵 ТОП-10 КАКТУСОВОДОВ ЧАТА:\n\n"
        for i, user in enumerate(top, 1):
            medal = {1:'🥇',2:'🥈',3:'🥉'}.get(i, f'{i}.')
            username = user.username or str(user.user_id)
            text += f"{medal} @{username} — {user.cactus:.1f} см\n"
        await update.message.reply_text(text)
    finally:
        db.close()


async def top_money(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        chat_id = update.effective_chat.id
        members = db.query(ChatMember).filter_by(chat_id=chat_id).all()
        user_ids = [m.user_id for m in members]
        if not user_ids:
            await update.message.reply_text("💰 Топ богачей пуст!")
            return
        # Исключаем админов
        top = db.query(User).filter(
            User.user_id.in_(user_ids),
            User.username.notin_(ADMINS)
        ).order_by(desc(User.balance)).limit(10).all()
        if not top:
            await update.message.reply_text("💰 Топ богачей пуст!")
            return
        text = "💰 ТОП-10 БОГАЧЕЙ ЧАТА:\n\n"
        for i, user in enumerate(top, 1):
            medal = {1:'🥇',2:'🥈',3:'🥉'}.get(i, f'{i}.')
            username = user.username or str(user.user_id)
            text += f"{medal} @{username} — {user.balance} монет\n"
        await update.message.reply_text(text)
    finally:
        db.close()
