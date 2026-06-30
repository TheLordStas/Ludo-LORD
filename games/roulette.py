import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.economy import get_or_create_user, get_or_create_chat_member, check_ban
from database.helpers import schedule_message_deletion
from database.models import RouletteHistory
from config import (
    RED_NUMBERS, GAME_RESULT_DELETE_SECONDS, MENU_TIMEOUT_SECONDS
)


# Клавиатуры (можно оставить как есть)
def get_roulette_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🔴 Красное x2", callback_data="roul_bet:red"),
            InlineKeyboardButton("⚫ Чёрное x2", callback_data="roul_bet:black"),
        ],
        [
            InlineKeyboardButton("📐 1-12 x3", callback_data="roul_bet:range1"),
            InlineKeyboardButton("📐 13-24 x3", callback_data="roul_bet:range2"),
            InlineKeyboardButton("📐 25-36 x3", callback_data="roul_bet:range3"),
        ],
        [
            InlineKeyboardButton("🟢 Зеро x14", callback_data="roul_bet:zero"),
            InlineKeyboardButton("🎯 Число x35", callback_data="roul_number_select"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_number_keyboard():
    keyboard = []
    keyboard.append([InlineKeyboardButton("0 🟢", callback_data="roul_number:0")])
    for i in range(1, 37, 4):
        row = []
        for j in range(4):
            num = i + j
            if num <= 36:
                color = '🔴' if num in RED_NUMBERS else '⚫'
                row.append(InlineKeyboardButton(f"{color}{num}", callback_data=f"roul_number:{num}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="roul_back")])
    return InlineKeyboardMarkup(keyboard)


def get_history_text(chat_id):
    db = SessionLocal()
    try:
        history = db.query(RouletteHistory).filter_by(chat_id=chat_id).order_by(RouletteHistory.timestamp.desc()).limit(
            5).all()
        if not history:
            return ""
        text = "\n📜 "
        for h in reversed(history):
            emoji = '🟢' if h.number == 0 else ('🔴' if h.color == 'red' else '⚫')
            text += f"{emoji}{h.number} "
        return text
    finally:
        db.close()


async def roulette(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id

        if not context.args:
            await update.message.reply_text("🎡 Укажи ставку: /roulette [ставка]")
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

        context.user_data['roulette_bet'] = bet
        history = get_history_text(chat_id)
        keyboard = get_roulette_keyboard()
        msg = await update.message.reply_text(
            f"🎡 РУЛЕТКА\nСтавка: {bet} монет\nВыбери тип ставки:{history}",
            reply_markup=keyboard
        )
        context.user_data['roulette_msg_id'] = msg.message_id

        # Таймер на 5 минут
        context.job_queue.run_once(
            roulette_timeout,
            MENU_TIMEOUT_SECONDS,
            data={'chat_id': chat_id, 'message_id': msg.message_id, 'user_id': user_data.id}
        )
    finally:
        db.close()


async def roulette_timeout(context: CallbackContext):
    """Таймаут меню рулетки: удаляем сообщение и возвращаем ставку, если не сыграно"""
    job_data = context.job.data
    try:
        await context.bot.delete_message(chat_id=job_data['chat_id'], message_id=job_data['message_id'])
    except:
        pass
    # Возврат ставки, если она ещё не использована
    if 'roulette_bet' in context.user_data:
        bet = context.user_data['roulette_bet']
        db = SessionLocal()
        try:
            user = get_or_create_user(db, job_data['user_id'])
            user.balance += bet
            db.commit()
        finally:
            db.close()
        context.user_data.pop('roulette_bet', None)


async def roulette_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    if 'roulette_bet' not in context.user_data:
        await query.answer("Сначала введи /roulette [ставка]!", show_alert=True)
        return

    bet = context.user_data['roulette_bet']
    await query.answer()

    if data == "roul_number_select":
        keyboard = get_number_keyboard()
        await query.edit_message_text(f"🎯 Выбери число от 0 до 36:\nСтавка: {bet} монет", reply_markup=keyboard)
        return
    if data == "roul_back":
        history = get_history_text(query.message.chat_id)
        keyboard = get_roulette_keyboard()
        await query.edit_message_text(f"🎡 РУЛЕТКА\nСтавка: {bet} монет\nВыбери тип ставки:{history}",
                                      reply_markup=keyboard)
        return
    if data.startswith("roul_number:"):
        chosen_number = int(data.split(":")[1])
        await process_roulette_spin(query, context, bet, 'number', chosen_number)
        return
    if data.startswith("roul_bet:"):
        bet_type = data.split(":")[1]
        await process_roulette_spin(query, context, bet, bet_type, None)
        return


async def process_roulette_spin(query, context, bet, bet_type, chosen_number):
    db = SessionLocal()
    try:
        user_data = query.from_user
        chat_id = query.message.chat_id

        user = get_or_create_user(db, user_data.id, user_data.username)
        if user.balance < bet:
            await query.answer("❌ Недостаточно монет!", show_alert=True)
            return

        # Списываем ставку
        user.balance -= bet
        member = get_or_create_chat_member(db, user_data.id, chat_id)
        member.total_bets += bet
        member.games_played += 1
        user.total_bets += bet
        user.games_played += 1

        spin = random.randint(0, 36)
        color = 'green' if spin == 0 else ('red' if spin in RED_NUMBERS else 'black')
        hist = RouletteHistory(chat_id=chat_id, number=spin, color=color)
        db.add(hist)
        old = db.query(RouletteHistory).filter_by(chat_id=chat_id).order_by(RouletteHistory.timestamp.desc()).offset(
            50).all()
        for o in old:
            db.delete(o)

        win = 0
        won = False
        if bet_type == 'red' and color == 'red':
            win = bet * 2
            won = True
        elif bet_type == 'black' and color == 'black':
            win = bet * 2
            won = True
        elif bet_type == 'zero' and spin == 0:
            win = bet * 14
            won = True
        elif bet_type == 'range1' and 1 <= spin <= 12:
            win = bet * 3
            won = True
        elif bet_type == 'range2' and 13 <= spin <= 24:
            win = bet * 3
            won = True
        elif bet_type == 'range3' and 25 <= spin <= 36:
            win = bet * 3
            won = True
        elif bet_type == 'number' and spin == chosen_number:
            win = bet * 35
            won = True

        if won:
            user.balance += win
            user.total_won += win
            member.total_won += win
        else:
            user.total_lost += bet
            member.total_lost += bet

        db.commit()
        history = get_history_text(chat_id)
        spin_emoji = '🟢' if spin == 0 else ('🔴' if color == 'red' else '⚫')
        type_names = {'red': 'красное', 'black': 'чёрное', 'zero': 'зеро', 'range1': '1-12', 'range2': '13-24',
                      'range3': '25-36'}
        bet_desc = f"число {chosen_number}" if bet_type == 'number' else type_names.get(bet_type, bet_type)

        result_text = (
            f"🎡 РУЛЕТКА\nСтавка: {bet} на {bet_desc}\n"
            f"Выпало: {spin_emoji} {spin}\n"
            f"{'🎉 ВЫИГРЫШ! +' + str(win) if won else '😢 ПРОИГРЫШ! -' + str(bet)} монет\n"
            f"💰 Баланс: {user.balance}{history}"
        )
        await query.edit_message_text(result_text)
        context.user_data.pop('roulette_bet', None)
        await schedule_message_deletion(context, chat_id, query.message.message_id, GAME_RESULT_DELETE_SECONDS)
    finally:
        db.close()


async def roulette_text(update: Update, context: CallbackContext):
    parts = update.message.text.strip().split()
    if len(parts) == 1:
        await update.message.reply_text("🎡 Укажи ставку: рулетка 500")
        return
    context.args = parts[1:]
    await roulette(update, context)
