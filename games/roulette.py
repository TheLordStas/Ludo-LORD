import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.models import RouletteHistory
from services.economy import get_or_create_user
from config import RED_NUMBERS, BLACK_NUMBERS


def get_roulette_keyboard():
    """Клавиатура выбора типа ставки"""
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
    """Клавиатура выбора числа 0-36"""
    keyboard = []
    keyboard.append([InlineKeyboardButton("0 🟢", callback_data="roul_number:0")])

    for i in range(1, 37, 4):
        row = []
        for j in range(4):
            num = i + j
            if num <= 36:
                color = '🔴' if num in RED_NUMBERS else '⚫'
                row.append(InlineKeyboardButton(
                    f"{color}{num}", callback_data=f"roul_number:{num}"
                ))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="roul_back")])
    return InlineKeyboardMarkup(keyboard)


def get_history_text(chat_id):
    db = SessionLocal()
    try:
        history = db.query(RouletteHistory).filter_by(chat_id=chat_id) \
            .order_by(RouletteHistory.timestamp.desc()).limit(5).all()

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
    """Основная команда: /roulette [ставка]"""
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id

        if not context.args:
            await update.message.reply_text(
                "🎡 Укажи ставку: /roulette [ставка]\n"
                "Пример: /roulette 500"
            )
            return

        try:
            bet = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Ставка должна быть числом!")
            return

        if bet <= 0:
            await update.message.reply_text("❌ Ставка должна быть больше 0!")
            return

        user = get_or_create_user(db, user_data.id, chat_id, user_data.username)

        if user.balance < bet:
            await update.message.reply_text(f"❌ Недостаточно монет! Баланс: {user.balance}")
            return

        # Проверка бана
        from handlers.admin import check_ban
        if check_ban(user):
            await update.message.reply_text("🚫 Ты забанен в играх!")
            return

        # Сохраняем ставку в user_data для callback'ов
        context.user_data['roulette_bet'] = bet

        history = get_history_text(chat_id)
        keyboard = get_roulette_keyboard()

        msg = await update.message.reply_text(
            f"🎡 РУЛЕТКА\nСтавка: {bet} монет\nВыбери тип ставки:{history}",
            reply_markup=keyboard
        )

        # Сохраняем message_id для автоудаления
        context.user_data['roulette_msg_id'] = msg.message_id

        # Автоудаление меню через 10 секунд
        context.job_queue.run_once(
            delete_roulette_menu,
            10,
            data={
                'chat_id': chat_id,
                'message_id': msg.message_id,
                'user_id': user_data.id
            }
        )

    finally:
        db.close()


async def delete_roulette_menu(context: CallbackContext):
    """Удаляет меню рулетки и сообщение о бездействии"""
    job_data = context.job.data
    try:
        await context.bot.delete_message(
            chat_id=job_data['chat_id'],
            message_id=job_data['message_id']
        )
    except:
        pass


async def roulette_callback(update: Update, context: CallbackContext):
    """Обработчик всех callback'ов рулетки"""
    query = update.callback_query
    data = query.data

    # Проверяем, есть ли ставка
    if 'roulette_bet' not in context.user_data:
        await query.answer("Сначала введи /roulette [ставка]!", show_alert=True)
        return

    bet = context.user_data['roulette_bet']

    await query.answer()

    # Выбор числа (показ клавиатуры)
    if data == "roul_number_select":
        keyboard = get_number_keyboard()
        await query.edit_message_text(
            f"🎯 Выбери число от 0 до 36:\nСтавка: {bet} монет",
            reply_markup=keyboard
        )
        return

    # Возврат из выбора числа
    if data == "roul_back":
        history = get_history_text(query.message.chat_id)
        keyboard = get_roulette_keyboard()
        await query.edit_message_text(
            f"🎡 РУЛЕТКА\nСтавка: {bet} монет\nВыбери тип ставки:{history}",
            reply_markup=keyboard
        )
        return

    # Выбор конкретного числа
    if data.startswith("roul_number:"):
        chosen_number = int(data.split(":")[1])
        await process_roulette_spin(query, context, bet, 'number', chosen_number)
        return

    # Ставка на тип (red/black/zero/range1/range2/range3)
    if data.startswith("roul_bet:"):
        bet_type = data.split(":")[1]
        await process_roulette_spin(query, context, bet, bet_type, None)
        return


async def process_roulette_spin(query, context, bet, bet_type, chosen_number):
    """Крутит рулетку и обрабатывает результат"""
    db = SessionLocal()
    try:
        user_data = query.from_user
        chat_id = query.message.chat_id

        user = get_or_create_user(db, user_data.id, chat_id, user_data.username)

        # Повторная проверка баланса
        if user.balance < bet:
            await query.answer("❌ Недостаточно монет!", show_alert=True)
            return

        # Списываем ставку
        user.balance -= bet
        user.total_bets += bet
        user.games_played += 1

        # Крутим
        spin = random.randint(0, 36)
        color = 'green' if spin == 0 else ('red' if spin in RED_NUMBERS else 'black')

        # История
        hist = RouletteHistory(chat_id=chat_id, number=spin, color=color)
        db.add(hist)

        old = db.query(RouletteHistory).filter_by(chat_id=chat_id) \
            .order_by(RouletteHistory.timestamp.desc()).offset(50).all()
        for o in old:
            db.delete(o)

        # Проверка выигрыша
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
        else:
            user.total_lost += bet

        db.commit()

        history = get_history_text(chat_id)
        spin_emoji = '🟢' if spin == 0 else ('🔴' if color == 'red' else '⚫')

        # Описание ставки
        type_names = {
            'red': 'красное',
            'black': 'чёрное',
            'zero': 'зеро',
            'range1': '1-12',
            'range2': '13-24',
            'range3': '25-36',
        }

        if bet_type == 'number':
            bet_desc = f"число {chosen_number}"
        else:
            bet_desc = type_names.get(bet_type, bet_type)

        result_text = (
            f"🎡 РУЛЕТКА\n"
            f"Ставка: {bet} на {bet_desc}\n"
            f"Выпало: {spin_emoji} {spin}\n"
            f"{'🎉 ВЫИГРЫШ! +' + str(win) if won else '😢 ПРОИГРЫШ! -' + str(bet)} монет\n"
            f"💰 Баланс: {user.balance}"
            f"{history}"
        )

        await query.edit_message_text(result_text)

        # Очищаем ставку
        context.user_data['roulette_bet'] = None

    finally:
        db.close()


async def roulette_text(update: Update, context: CallbackContext):
    """Обработчик текстовой команды 'рулетка [ставка]'"""
    parts = update.message.text.strip().split()

    if len(parts) == 1:
        await update.message.reply_text(
            "🎡 Укажи ставку: рулетка 500\nИли используй /roulette 500"
        )
        return

    context.args = parts[1:]
    await roulette(update, context)
