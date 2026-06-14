from telegram import Update
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.models import User
from sqlalchemy import desc


async def top_fap(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        chat_id = update.effective_chat.id

        top_users = db.query(User).filter_by(chat_id=chat_id) \
            .order_by(desc(User.faps)).limit(10).all()

        if not top_users:
            await update.message.reply_text("💕 Топ фаперов пуст!")
            return

        text = "💕 ТОП-10 ФАПЕРОВ ЧАТА:\n\n"
        for i, user in enumerate(top_users, 1):
            medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, f'{i}.')
            username = user.username or f"user{user.user_id}"
            text += f"{medal} @{username} — {user.faps} фапов\n"

        await update.message.reply_text(text)
    finally:
        db.close()


async def top_grow(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        chat_id = update.effective_chat.id

        top_users = db.query(User).filter_by(chat_id=chat_id) \
            .order_by(desc(User.cactus)).limit(10).all()

        if not top_users:
            await update.message.reply_text("🌵 Топ кактусоводов пуст!")
            return

        text = "🌵 ТОП-10 КАКТУСОВОДОВ ЧАТА:\n\n"
        for i, user in enumerate(top_users, 1):
            medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, f'{i}.')
            username = user.username or f"user{user.user_id}"
            text += f"{medal} @{username} — {user.cactus:.1f} см\n"

        await update.message.reply_text(text)
    finally:
        db.close()


async def top_money(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        chat_id = update.effective_chat.id

        top_users = db.query(User).filter_by(chat_id=chat_id) \
            .order_by(desc(User.balance)).limit(10).all()

        if not top_users:
            await update.message.reply_text("💰 Топ богачей пуст!")
            return

        text = "💰 ТОП-10 БОГАЧЕЙ ЧАТА:\n\n"
        for i, user in enumerate(top_users, 1):
            medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, f'{i}.')
            username = user.username or f"user{user.user_id}"
            text += f"{medal} @{username} — {user.balance} монет\n"

        await update.message.reply_text(text)
    finally:
        db.close()