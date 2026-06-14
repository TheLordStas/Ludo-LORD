import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.models import DiceDuel, User
from services.economy import get_or_create_user


async def dice(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id

        if not update.message.reply_to_message:
            await update.message.reply_text("🎲 Ответь на сообщение соперника! Пример: дуэль 500")
            return

        if not context.args:
            await update.message.reply_text("🎲 Укажи ставку: /dice 500 или дуэль 500")
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

        user = get_or_create_user(db, user_data.id, chat_id, user_data.username)
        opp_user = get_or_create_user(db, opponent.id, chat_id, opponent.username)

        # Проверка бана
        from handlers.admin import check_ban
        if check_ban(user):
            await update.message.reply_text("🚫 Ты забанен в играх!")
            return

        if user.balance < bet:
            await update.message.reply_text(f"❌ Недостаточно монет! Баланс: {user.balance}")
            return

        if opp_user.balance < bet:
            await update.message.reply_text(f"❌ У соперника недостаточно монет!")
            return

        # Списываем ставку у вызывающего
        user.balance -= bet
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
            [
                InlineKeyboardButton("⚔️ Принять", callback_data=f"duel_accept:{duel.id}"),
                InlineKeyboardButton("❌ Отказаться", callback_data=f"duel_decline:{duel.id}")
            ]
        ])

        msg = await update.message.reply_text(
            f"⚔️ {user_data.mention_html()} вызывает на дуэль {opponent.mention_html()}!\n"
            f"Ставка: {bet} монет\n"
            f"Нажать кнопку может только {opponent.mention_html()}",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

        duel.message_id = msg.message_id
        db.commit()
    finally:
        db.close()


async def dice_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    db = SessionLocal()
    try:
        parts = data.split(":")
        action = parts[0]
        duel_id = int(parts[1])

        duel = db.query(DiceDuel).filter_by(id=duel_id, status='pending').first()

        if not duel:
            await query.answer("Дуэль уже завершена!", show_alert=True)
            return

        # Проверка что нажимает именно оппонент
        if query.from_user.id != duel.opponent_id:
            await query.answer("Только вызванный игрок может принять или отклонить!", show_alert=True)
            return

        await query.answer()

        if action == "duel_decline":
            duel.status = 'declined'

            # Возвращаем деньги вызывающему
            challenger = db.query(User).filter_by(
                user_id=duel.challenger_id, chat_id=duel.chat_id
            ).first()
            if challenger:
                challenger.balance += duel.amount
                challenger.total_bets -= duel.amount
                challenger.games_played -= 1

            db.commit()
            await query.edit_message_text("❌ Дуэль отклонена!")
            return

        if action == "duel_accept":
            opponent = db.query(User).filter_by(
                user_id=duel.opponent_id, chat_id=duel.chat_id
            ).first()

            if not opponent:
                await query.answer("Соперник не найден!", show_alert=True)
                return

            if opponent.balance < duel.amount:
                # Возвращаем вызывающему
                challenger = db.query(User).filter_by(
                    user_id=duel.challenger_id, chat_id=duel.chat_id
                ).first()
                if challenger:
                    challenger.balance += duel.amount
                    challenger.total_bets -= duel.amount
                    challenger.games_played -= 1
                duel.status = 'cancelled'
                db.commit()
                await query.edit_message_text("❌ У соперника недостаточно монет! Дуэль отменена.")
                return

            # Списываем у оппонента
            opponent.balance -= duel.amount
            opponent.total_bets += duel.amount
            opponent.games_played += 1

            challenger = db.query(User).filter_by(
                user_id=duel.challenger_id, chat_id=duel.chat_id
            ).first()

            # Кидаем кубики
            dice1 = random.randint(1, 6)
            dice2 = random.randint(1, 6)

            await query.edit_message_text(f"🎲 Бросаем кубики...\n🎲 🎲")
            await asyncio.sleep(2)

            total_pot = duel.amount * 2

            # Получаем имена
            try:
                member1 = await query.message.chat.get_member(duel.challenger_id)
                member2 = await query.message.chat.get_member(duel.opponent_id)
                name1 = member1.user.mention_html()
                name2 = member2.user.mention_html()
            except:
                name1 = f"Игрок 1"
                name2 = f"Игрок 2"

            if dice1 > dice2:
                winner = challenger
                winner_name = name1
                loser_name = name2
            elif dice2 > dice1:
                winner = opponent
                winner_name = name2
                loser_name = name1
            else:
                # Ничья — возвращаем обоим
                challenger.balance += duel.amount
                opponent.balance += duel.amount
                challenger.total_bets -= duel.amount
                opponent.total_bets -= duel.amount
                challenger.games_played -= 1
                opponent.games_played -= 1
                duel.status = 'draw'
                db.commit()
                await query.edit_message_text(
                    f"🎲 {dice1} vs {dice2} 🎲\n🤝 Ничья! Ставки возвращены.",
                    parse_mode='HTML'
                )
                return

            winner.balance += total_pot
            winner.total_won += duel.amount

            # Проигравший
            if winner == challenger:
                opponent.total_lost += duel.amount
            else:
                challenger.total_lost += duel.amount

            duel.status = 'finished'
            db.commit()

            await query.edit_message_text(
                f"🎲 {dice1} vs {dice2} 🎲\n"
                f"🏆 {winner_name} победил и забирает {duel.amount} монет!\n"
                f"💰 Выигрыш: +{duel.amount}",
                parse_mode='HTML'
            )
    finally:
        db.close()


async def dice_text(update: Update, context: CallbackContext):
    """Текстовая команда: дуэль 500"""
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
