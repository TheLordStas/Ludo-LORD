import random
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.economy import get_or_create_user, get_or_create_chat_member, check_ban
from database.helpers import schedule_message_deletion
from database.models import MineGame
from database.models import User
from config import (
    MINE_FIELD_SIZE, MINE_COUNT, MINE_START_MULTIPLIER,
    MINE_MULTIPLIER_FACTOR, MINE_MULTIPLIER_FACTOR_VIP,
    GAME_RESULT_DELETE_SECONDS, MENU_TIMEOUT_SECONDS
)
from datetime import datetime


def generate_mine_keyboard(field, revealed, game_over=False):
    keyboard = []
    for i in range(MINE_FIELD_SIZE):
        row = []
        for j in range(MINE_FIELD_SIZE):
            if [i, j] in revealed:
                if field[i][j] == '💣':
                    row.append(InlineKeyboardButton("💣", callback_data="mine_ignore"))
                else:
                    row.append(InlineKeyboardButton("🍎", callback_data="mine_ignore"))
            elif game_over:
                if field[i][j] == '💣':
                    row.append(InlineKeyboardButton("💣", callback_data="mine_ignore"))
                else:
                    row.append(InlineKeyboardButton("🍎", callback_data="mine_ignore"))
            else:
                row.append(InlineKeyboardButton("⬜", callback_data=f"mine_open:{i}:{j}"))
        keyboard.append(row)
    if not game_over:
        keyboard.append([InlineKeyboardButton("💰 Забрать выигрыш", callback_data="mine_cashout")])
    return InlineKeyboardMarkup(keyboard)


async def mines(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id

        if not context.args:
            await update.message.reply_text("💣 Укажи ставку: /mines 100")
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

        active_game = db.query(MineGame).filter_by(
            user_id=user_data.id, chat_id=chat_id, status='active'
        ).first()
        if active_game:
            await update.message.reply_text("У тебя уже есть активная игра в мины! Заверши её.")
            return

        # Создаём поле
        field = [['🍎' for _ in range(MINE_FIELD_SIZE)] for _ in range(MINE_FIELD_SIZE)]
        mine_positions = random.sample(range(MINE_FIELD_SIZE * MINE_FIELD_SIZE), MINE_COUNT)
        for pos in mine_positions:
            row = pos // MINE_FIELD_SIZE
            col = pos % MINE_FIELD_SIZE
            field[row][col] = '💣'

        user.balance -= bet
        member = get_or_create_chat_member(db, user_data.id, chat_id)
        member.total_bets += bet
        member.games_played += 1
        user.total_bets += bet
        user.games_played += 1

        game = MineGame(
            user_id=user_data.id,
            chat_id=chat_id,
            bet=bet,
            multiplier=MINE_START_MULTIPLIER,
            field=json.dumps(field),
            revealed=json.dumps([]),
            apples_found=0
        )
        db.add(game)
        db.commit()

        keyboard = generate_mine_keyboard(field, [])
        max_apples = MINE_FIELD_SIZE * MINE_FIELD_SIZE - MINE_COUNT
        msg = await update.message.reply_text(
            f"💣 МИНЫ\nСтавка: {bet} монет\nМножитель: x{MINE_START_MULTIPLIER:.2f}\n"
            f"Яблок: 0/{max_apples}\n\nОткрывай клетки — ищи яблоки!",
            reply_markup=keyboard
        )
        game.message_id = msg.message_id
        db.commit()

        # Таймаут
        context.job_queue.run_once(
            mines_timeout,
            MENU_TIMEOUT_SECONDS,
            data={'game_id': game.id, 'chat_id': chat_id, 'message_id': msg.message_id}
        )
    finally:
        db.close()


async def mines_timeout(context: CallbackContext):
    """Таймаут мины: удаляем сообщение, завершаем игру с возвратом ставки, если активна"""
    job_data = context.job.data
    db = SessionLocal()
    try:
        game = db.query(MineGame).filter_by(id=job_data['game_id'], status='active').first()
        if game:
            user = get_or_create_user(db, game.user_id)
            user.balance += game.bet
            game.status = 'cancelled'
            db.commit()
        try:
            await context.bot.delete_message(chat_id=job_data['chat_id'], message_id=job_data['message_id'])
        except:
            pass
    finally:
        db.close()


async def mines_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    if data == "mine_ignore":
        await query.answer()
        return

    db = SessionLocal()
    try:
        game = db.query(MineGame).filter_by(
            user_id=query.from_user.id, chat_id=query.message.chat_id, status='active'
        ).first()
        if not game:
            await query.answer("Нет активной игры! /mines [ставка]", show_alert=True)
            return
        if query.from_user.id != game.user_id:
            await query.answer("Это не твоя игра!", show_alert=True)
            return
        await query.answer()

        if data.startswith("mine_open:"):
            _, row, col = data.split(":")
            row, col = int(row), int(col)
            field = json.loads(game.field)
            revealed = json.loads(game.revealed)
            if [row, col] in revealed:
                return
            revealed.append([row, col])
            game.revealed = json.dumps(revealed)

            if field[row][col] == '💣':
                game.status = 'finished'
                user = get_or_create_user(db, query.from_user.id, query.from_user.username)
                user.total_lost += game.bet
                db.commit()
                keyboard = generate_mine_keyboard(field, revealed, game_over=True)
                max_apples = MINE_FIELD_SIZE * MINE_FIELD_SIZE - MINE_COUNT
                await query.edit_message_text(
                    f"💥 БУМ! Мина!\nПроигрыш: {game.bet} монет\n💰 Баланс: {user.balance}\nЯблок найдено: {game.apples_found}/{max_apples}",
                    reply_markup=keyboard
                )
                await schedule_message_deletion(context, game.chat_id, query.message.message_id,
                                                GAME_RESULT_DELETE_SECONDS)
            else:
                game.apples_found += 1
                is_vip = False
                user = db.query(User).filter_by(user_id=game.user_id).first()
                if user:
                    now = datetime.utcnow()
                    is_vip = user.is_vip and user.vip_until and user.vip_until > now
                factor = MINE_MULTIPLIER_FACTOR_VIP if is_vip else MINE_MULTIPLIER_FACTOR
                game.multiplier = MINE_START_MULTIPLIER * (factor ** game.apples_found)
                db.commit()
                keyboard = generate_mine_keyboard(field, revealed)
                max_apples = MINE_FIELD_SIZE * MINE_FIELD_SIZE - MINE_COUNT
                potential_win = int(game.bet * game.multiplier)
                await query.edit_message_text(
                    f"🍎 Яблоко!\nМножитель: x{game.multiplier:.2f}\nЯблок: {game.apples_found}/{max_apples}\n"
                    f"Потенциальный выигрыш: {potential_win} монет\n\nОткрывай дальше или забирай!",
                    reply_markup=keyboard
                )

        elif data == "mine_cashout":
            user = get_or_create_user(db, query.from_user.id, query.from_user.username)
            win = int(game.bet * game.multiplier)
            user.balance += win
            user.total_won += win
            game.status = 'finished'
            field = json.loads(game.field)
            revealed = json.loads(game.revealed)
            full_revealed = [[i, j] for i in range(MINE_FIELD_SIZE) for j in range(MINE_FIELD_SIZE)]
            db.commit()
            keyboard = generate_mine_keyboard(field, full_revealed, game_over=True)
            max_apples = MINE_FIELD_SIZE * MINE_FIELD_SIZE - MINE_COUNT
            await query.edit_message_text(
                f"💰 Выигрыш: +{win} монет\nМножитель: x{game.multiplier:.2f}\nЯблок: {game.apples_found}/{max_apples}\n💰 Баланс: {user.balance}",
                reply_markup=keyboard
            )
            await schedule_message_deletion(context, game.chat_id, query.message.message_id, GAME_RESULT_DELETE_SECONDS)
    finally:
        db.close()


async def mines_text(update: Update, context: CallbackContext):
    parts = update.message.text.strip().split()
    if len(parts) >= 2:
        try:
            bet = int(parts[1])
            context.args = [str(bet)]
            await mines(update, context)
        except ValueError:
            await update.message.reply_text("❌ Неверная ставка! Пример: мины 500")
    else:
        await update.message.reply_text("💣 Укажи ставку: мины 500")
