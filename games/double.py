import random, asyncio
from telegram import Update
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.economy import get_or_create_user, get_or_create_chat_member, check_ban
from database.helpers import schedule_message_deletion
from config import DOUBLE_WIN_CHANCE, DOUBLE_WIN_CHANCE_VIP, GAME_RESULT_DELETE_SECONDS
from datetime import datetime


async def double(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id

        if not context.args:
            await update.message.reply_text("🎯 Укажи ставку: удвоение 500")
            return

        try:
            bet = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Ставка должна быть числом!")
            return

        if bet <= 0:
            await update.message.reply_text("❌ Ставка должна быть больше 0!")
            return

        user = get_or_create_user(db, user_data.id, user_data.username)
        if check_ban(user):
            await update.message.reply_text("🚫 Ты забанен в играх!")
            return
        if user.balance < bet:
            await update.message.reply_text(f"❌ Недостаточно монет! Баланс: {user.balance}")
            return

        is_vip = user.is_vip and user.vip_until and user.vip_until > datetime.utcnow()
        chance = DOUBLE_WIN_CHANCE_VIP if is_vip else DOUBLE_WIN_CHANCE

        user.balance -= bet
        member = get_or_create_chat_member(db, user_data.id, chat_id)
        member.total_bets += bet
        member.games_played += 1
        user.total_bets += bet
        user.games_played += 1

        msg = await update.message.reply_text("🎯 Испытываем удачу...")
        await asyncio.sleep(2)

        if random.random() < chance:
            win = bet * 2
            user.balance += win
            user.total_won += bet
            member.total_won += bet
            db.commit()
            await msg.edit_text(f"🎉 Удвоение! +{win} монет\n💰 Баланс: {user.balance}")
        else:
            user.total_lost += bet
            member.total_lost += bet
            db.commit()
            await msg.edit_text(f"😢 Не повезло! -{bet} монет\n💰 Баланс: {user.balance}")

        await schedule_message_deletion(context, chat_id, msg.message_id, GAME_RESULT_DELETE_SECONDS)
    finally:
        db.close()


async def double_text(update: Update, context: CallbackContext):
    parts = update.message.text.strip().split()
    if len(parts) >= 2:
        try:
            bet = int(parts[1])
            context.args = [str(bet)]
            await double(update, context)
        except ValueError:
            await update.message.reply_text("❌ Неверная ставка! Пример: удвоение 500")
    else:
        await update.message.reply_text("🎯 Укажи ставку: удвоение 500")
