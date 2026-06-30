import random, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.economy import get_or_create_user, get_or_create_chat_member, check_ban
from database.helpers import vip_mention, schedule_message_deletion
from database.models import DiceDuel, User
from config import GAME_RESULT_DELETE_SECONDS, MENU_TIMEOUT_SECONDS


async def dice(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id

        if not update.message.reply_to_message:
            await update.message.reply_text("🎲 Ответь на сообщение соперника! Пример: дуэль 500")
            return
        if not context.args:
            await update.message.reply_text("🎲 Укажи ставку: /dice 500")
            return

        try:
            bet = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Ставка должна быть числом!")
            return

        if bet <= 0:
            await update.message.reply_text("❌ Ставка должна быть больше 0!")
            return

        opponent = update.message.reply_to_message.from_user
        if opponent.id == user_data.id:
            await update.message.reply_text("❌ Нельзя вызвать самого себя!")
            return
        if opponent.is_bot:
            await update.message.reply_text("❌ Боты не играют!")
            return

        user = get_or_create_user(db, user_data.id, user_data.username)
        opp_user = get_or_create_user(db, opponent.id, opponent.username)

        if check_ban(user):
            await update.message.reply_text("🚫 Ты забанен в играх!")
            return
        if user.balance < bet:
            await update.message.reply_text(f"❌ Недостаточно монет! Баланс: {user.balance}")
            return
        if opp_user.balance < bet:
            await update.message.reply_text(f"❌ У соперника недостаточно монет!")
            return

        user.balance -= bet
        member = get_or_create_chat_member(db, user_data.id, chat_id)
        member.total_bets += bet
        member.games_played += 1
        user.total_bets += bet
        user.games_played += 1

        duel = DiceDuel(
            chat_id=chat_id,
            challenger_id=user_data.id,
            opponent_id=opponent.id,
            amount=bet
        )
        db.add(duel)
        db.commit()

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Принять", callback_data=f"duel_accept:{duel.id}"),
             InlineKeyboardButton("❌ Отказаться", callback_data=f"duel_decline:{duel.id}")]
        ])

        name1 = vip_mention(user)
        name2 = vip_mention(opp_user)
        msg = await update.message.reply_text(
            f"⚔️ {name1} вызывает на дуэль {name2}!\nСтавка: {bet} монет\nНажать может только {name2}",
            reply_markup=keyboard, parse_mode='HTML'
        )
        duel.message_id = msg.message_id
        db.commit()

        context.job_queue.run_once(
            duel_timeout,
            MENU_TIMEOUT_SECONDS,
            data={'duel_id': duel.id, 'chat_id': chat_id, 'message_id': msg.message_id}
        )
    finally:
        db.close()


async def duel_timeout(context: CallbackContext):
    """Таймаут дуэли: удаляем, возвращаем ставку вызывающему"""
    job_data = context.job.data
    db = SessionLocal()
    try:
        duel = db.query(DiceDuel).filter_by(id=job_data['duel_id'], status='pending').first()
        if duel:
            challenger = db.query(User).filter_by(user_id=duel.challenger_id).first()
            if challenger:
                challenger.balance += duel.amount
            duel.status = 'cancelled'
            db.commit()
        try:
            await context.bot.delete_message(chat_id=job_data['chat_id'], message_id=job_data['message_id'])
        except:
            pass
    finally:
        db.close()


async def dice_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    parts = data.split(":")
    action = parts[0]
    duel_id = int(parts[1])

    db = SessionLocal()
    try:
        duel = db.query(DiceDuel).filter_by(id=duel_id, status='pending').first()
        if not duel:
            await query.answer("Дуэль уже завершена!", show_alert=True)
            return
        if query.from_user.id != duel.opponent_id:
            await query.answer("Только вызванный игрок может принять или отклонить!", show_alert=True)
            return
        await query.answer()

        if action == "duel_decline":
            duel.status = 'declined'
            challenger = db.query(User).filter_by(user_id=duel.challenger_id).first()
            if challenger:
                challenger.balance += duel.amount
            db.commit()
            await query.edit_message_text("❌ Дуэль отклонена!")
            return

        elif action == "duel_accept":
            opponent = db.query(User).filter_by(user_id=duel.opponent_id).first()
            if not opponent or opponent.balance < duel.amount:
                challenger = db.query(User).filter_by(user_id=duel.challenger_id).first()
                if challenger:
                    challenger.balance += duel.amount
                duel.status = 'cancelled'
                db.commit()
                await query.edit_message_text("❌ У соперника недостаточно монет! Дуэль отменена.")
                return

            opponent.balance -= duel.amount
            opponent_member = get_or_create_chat_member(db, duel.opponent_id, duel.chat_id)
            opponent_member.total_bets += duel.amount
            opponent_member.games_played += 1
            opponent.total_bets += duel.amount
            opponent.games_played += 1

            challenger = db.query(User).filter_by(user_id=duel.challenger_id).first()

            dice1 = random.randint(1, 6)
            dice2 = random.randint(1, 6)

            await query.edit_message_text(f"🎲 Бросаем кубики...\n🎲 🎲")
            await asyncio.sleep(2)

            total_pot = duel.amount * 2
            name1 = vip_mention(challenger) if challenger else "Игрок 1"
            name2 = vip_mention(opponent)

            if dice1 > dice2:
                winner = challenger
                winner_name = name1
                loser_name = name2
            elif dice2 > dice1:
                winner = opponent
                winner_name = name2
                loser_name = name1
            else:
                challenger.balance += duel.amount
                opponent.balance += duel.amount
                duel.status = 'draw'
                db.commit()
                await query.edit_message_text(f"🎲 {dice1} vs {dice2} 🎲\n🤝 Ничья! Ставки возвращены.")
                return

            winner.balance += total_pot
            winner.total_won += duel.amount
            if winner == challenger:
                opponent.total_lost += duel.amount
            else:
                challenger.total_lost += duel.amount

            duel.status = 'finished'
            db.commit()
            await query.edit_message_text(
                f"🎲 {dice1} vs {dice2} 🎲\n🏆 {winner_name} победил и забирает {duel.amount} монет!\n💰 Выигрыш: +{duel.amount}",
                parse_mode='HTML'
            )
            await schedule_message_deletion(context, duel.chat_id, query.message.message_id, GAME_RESULT_DELETE_SECONDS)
    finally:
        db.close()


async def dice_text(update: Update, context: CallbackContext):
    if not update.message.reply_to_message:
        await update.message.reply_text("🎲 Ответь на сообщение соперника! Пример: дуэль 500")
        return
    parts = update.message.text.strip().split()
    if len(parts) >= 2:
        try:
            bet = int(parts[1])
            context.args = [str(bet)]
            await dice(update, context)
        except ValueError:
            await update.message.reply_text("❌ Неверная ставка! Пример: дуэль 500")
    else:
        await update.message.reply_text("🎲 Укажи ставку: дуэль 500")
