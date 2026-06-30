import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.economy import get_or_create_user, get_or_create_chat_member, check_ban
from database.helpers import is_registered, schedule_message_deletion
from database.models import TradeGame
from config import TRADE_TIMES, GAME_RESULT_DELETE_SECONDS, MENU_TIMEOUT_SECONDS


async def trade_start(update: Update, context: CallbackContext):
    """Начало игры: команда /trade или текст 'трейд 500'"""
    db = SessionLocal()
    try:
        user_data = update.effective_user
        chat_id = update.effective_chat.id

        if not context.args:
            await update.message.reply_text("📈 Укажи ставку: /trade 500")
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
        if not is_registered(user):
            await update.message.reply_text("Сначала выбери пол!")
            return
        if check_ban(user):
            await update.message.reply_text("🚫 Ты забанен в играх!")
            return
        if user.balance < bet:
            await update.message.reply_text(f"❌ Недостаточно монет! Баланс: {user.balance}")
            return

        # Проверка на активный трейд
        active_trade = db.query(TradeGame).filter_by(
            user_id=user_data.id, status='active'
        ).first()
        if active_trade:
            await update.message.reply_text("⏳ У тебя уже есть активный трейд! Дождись его завершения.")
            return

        user.balance -= bet
        member = get_or_create_chat_member(db, user_data.id, chat_id)
        member.total_bets += bet
        member.games_played += 1
        user.total_bets += bet
        user.games_played += 1
        db.commit()

        context.user_data['trade_bet'] = bet

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⏱ {t} сек", callback_data=f"trade_start:{t}") for t in TRADE_TIMES]
        ])

        msg = await update.message.reply_text(
            f"📈Pepe Трейд\nСтавка: {bet} 💰\nВыбери время:",
            reply_markup=keyboard
        )

        context.job_queue.run_once(
            cancel_trade_menu,
            MENU_TIMEOUT_SECONDS,
            data={'chat_id': chat_id, 'message_id': msg.message_id, 'user_id': user_data.id}
        )
    finally:
        db.close()


async def trade_callback(update: Update, context: CallbackContext):
    """Обработчик колбэка выбора времени трейда"""
    query = update.callback_query
    data = query.data
    if data.startswith("trade_start:"):
        duration = int(data.split(":")[1])
        await start_trade_game(update, context, duration)


async def start_trade_game(update, context, duration):
    """Запускает фоновую задачу трейда и не блокирует бота"""
    query = update.callback_query
    user_data = query.from_user
    chat_id = query.message.chat_id

    db = SessionLocal()
    try:
        bet = context.user_data.get('trade_bet')
        if not bet:
            await query.answer("Ставка не найдена. Начни заново /trade", show_alert=True)
            return

        try:
            await query.message.delete()
        except:
            pass

        trade = TradeGame(
            user_id=user_data.id, chat_id=chat_id,
            bet=bet, duration=duration, status='active'
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)

        msg = await context.bot.send_message(chat_id, "📈 График запущен...")
        trade.message_id = msg.message_id
        db.commit()

        # Запускаем фоновую корутину, чтобы не блокировать бота
        context.application.create_task(
            _trade_graph_loop(
                bot=context.bot,
                chat_id=chat_id,
                message_id=msg.message_id,
                trade_id=trade.id,
                bet=bet,
                user_id=user_data.id,
                duration=duration,
                context=context
            )
        )

    finally:
        db.close()


async def _trade_graph_loop(bot, chat_id, message_id, trade_id, bet, user_id, duration, context):
    """Фоновая корутина: имитирует график и завершает трейд"""
    end_time = asyncio.get_event_loop().time() + duration
    price = 1.0
    volatility = 0.15
    bar_chars = '▁▂▃▄▅▆▇█'

    while asyncio.get_event_loop().time() < end_time:
        change = random.uniform(-volatility, volatility * 1.3)
        price += change
        if price < 0.1:
            price = 0.1
        if price > 7.0:
            price = 7.0

        idx = min(int(price * 1.2), 7)
        idx = max(0, min(idx, 7))
        graph = bar_chars[idx]
        arrow = "📈" if change >= 0 else "📉"

        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{arrow} {graph} Коэф: x{price:.2f}"
            )
        except:
            pass

        await asyncio.sleep(3.0)

    # Финал
    noise = random.uniform(-0.05, 0.05)
    final_multiplier = price + noise
    if final_multiplier < 0.01:
        final_multiplier = 0.01
    if final_multiplier > 7.0:
        final_multiplier = 7.0

    db = SessionLocal()
    try:
        trade = db.query(TradeGame).filter_by(id=trade_id).first()
        if trade:
            trade.result_multiplier = final_multiplier
            trade.status = 'finished'
            db.commit()

        win = int(bet * final_multiplier)
        user = get_or_create_user(db, user_id)
        user.balance += win
        if win >= bet:
            user.total_won += win - bet
        else:
            user.total_lost += bet - win
        db.commit()

        if win > bet:
            result_icon = "🎉"
            result_text = f"ВЫИГРЫШ! +{win} монет"
        elif win < bet:
            result_icon = "😢"
            result_text = f"ПРОИГРЫШ! -{bet - win} монет"
        else:
            result_icon = "🤝"
            result_text = "В своих! Ставка возвращена"

        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=(
                    f"{result_icon} Pepe Трейд завершён!\n"
                    f"Ставка: {bet} 💰\n"
                    f"Итоговый коэффициент: x{final_multiplier:.2f}\n"
                    f"{result_text}\n"
                    f"💰 Баланс: {user.balance}"
                )
            )
        except:
            pass

        await schedule_message_deletion(context, chat_id, message_id, GAME_RESULT_DELETE_SECONDS)

    finally:
        db.close()


async def cancel_trade_menu(context: CallbackContext):
    """Таймаут меню: удаляет сообщение и возвращает ставку"""
    job_data = context.job.data
    try:
        await context.bot.delete_message(
            chat_id=job_data['chat_id'],
            message_id=job_data['message_id']
        )
    except:
        pass

    db = SessionLocal()
    try:
        trade = db.query(TradeGame).filter_by(
            user_id=job_data['user_id'],
            chat_id=job_data['chat_id'],
            status='active'
        ).first()
        if trade:
            user = get_or_create_user(db, trade.user_id)
            user.balance += trade.bet
            trade.status = 'cancelled'
            db.commit()
    finally:
        db.close()
