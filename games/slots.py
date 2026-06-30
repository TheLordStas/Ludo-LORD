import random
import asyncio
from telegram import Update
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.economy import get_or_create_user, get_or_create_chat_member, check_ban
from database.helpers import schedule_message_deletion
from config import (
    SLOT_EMOJIS, SLOT_WEIGHTS, SLOT_WEIGHTS_VIP, SLOT_PAYOUTS,
    GAME_RESULT_DELETE_SECONDS
)
from datetime import datetime


async def slots(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id

        if not context.args:
            await update.message.reply_text("🎰 Укажи ставку: слоты 100")
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

        # VIP-веса
        is_vip = user.is_vip and user.vip_until and user.vip_until > datetime.utcnow()
        weights = SLOT_WEIGHTS_VIP if is_vip else SLOT_WEIGHTS

        user.balance -= bet
        member = get_or_create_chat_member(db, user_data.id, chat_id)
        member.total_bets += bet
        member.games_played += 1
        user.total_bets += bet
        user.games_played += 1

        result = random.choices(SLOT_EMOJIS, weights=weights, k=3)

        msg = await update.message.reply_text("🎰 Крутим барабаны...")
        for i in range(3):
            await asyncio.sleep(0.8)
            display = ' | '.join(result[:i + 1])
            await msg.edit_text(f"🎰 {display}")

        await asyncio.sleep(0.5)

        if '💀' in result:
            user.total_lost += bet
            db.commit()
            await msg.edit_text(
                f"🎰 {' | '.join(result)}\n\n"
                f"💀 Череп! Проигрыш: {bet} монет\n"
                f"💰 Баланс: {user.balance}"
            )
        elif result[0] == result[1] == result[2]:
            multiplier = SLOT_PAYOUTS.get(result[0], 3)
            win = bet * multiplier
            user.balance += win
            user.total_won += win
            member.total_won += win
            db.commit()
            await msg.edit_text(
                f"🎰 {' | '.join(result)}\n\n"
                f"🎉 ДЖЕКПОТ x{multiplier}! +{win} монет\n"
                f"💰 Баланс: {user.balance}"
            )
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            win = bet * 2
            user.balance += win
            user.total_won += win
            member.total_won += win
            db.commit()
            await msg.edit_text(
                f"🎰 {' | '.join(result)}\n\n"
                f"✨ Пара! x2! +{win} монет\n"
                f"💰 Баланс: {user.balance}"
            )
        else:
            user.total_lost += bet
            member.total_lost += bet
            db.commit()
            await msg.edit_text(
                f"🎰 {' | '.join(result)}\n\n"
                f"😢 Мимо! -{bet} монет\n"
                f"💰 Баланс: {user.balance}"
            )

        await schedule_message_deletion(context, chat_id, msg.message_id, GAME_RESULT_DELETE_SECONDS)
    finally:
        db.close()


async def slots_text(update: Update, context: CallbackContext):
    parts = update.message.text.strip().split()
    if len(parts) >= 2:
        try:
            bet = int(parts[1])
            context.args = [str(bet)]
            await slots(update, context)
        except ValueError:
            await update.message.reply_text("❌ Неверная ставка! Пример: слоты 500")
    else:
        await update.message.reply_text("🎰 Укажи ставку: слоты 500")
