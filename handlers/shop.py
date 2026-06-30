import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.economy import get_or_create_user
from database.helpers import is_registered, schedule_message_deletion, vip_mention
from config import (
    LUBE_PRICE, FERTILIZER_PRICE, SHOVEL_BASE_PRICE,
    SHOVEL_MULTIPLIER, SHOVEL_PRICE_MULTIPLIER, SHOVEL_MAX_LEVEL, FERTILIZER_COOLDOWN_REDUCTION_HOURS,
    GROW_COOLDOWN_HOURS, GROW_COOLDOWN_HOURS_VIP
)
from datetime import datetime, timedelta


async def shop_menu(update: Update, context: CallbackContext):
    """Отправляет меню магазина (команда /shop или текст 'магазин')"""
    db = SessionLocal()
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.username)
        if not is_registered(user):
            await update.message.reply_text("Сначала выбери пол!")
            return

        text = f"🛒 Магазин\n\n"
        text += f"1. Смазка (необходима для фапа) – {LUBE_PRICE} 💰/шт.\n"
        text += f"   У тебя: {user.lube_count} шт.\n\n"
        text += f"2. Удобрение (сокращает кулдаун кактуса на {FERTILIZER_COOLDOWN_REDUCTION_HOURS} ч) – {FERTILIZER_PRICE} 💰/шт.\n"
        text += f"   У тебя: {user.fertilizer_count} шт.\n\n"
        next_level = user.shovel_level + 1
        if next_level <= SHOVEL_MAX_LEVEL:
            cost = SHOVEL_BASE_PRICE * (SHOVEL_PRICE_MULTIPLIER ** (user.shovel_level - 1))
            text += f"3. Обновить лопату (уровень {user.shovel_level} → {next_level}) – {cost} 💰\n"
            text += f"   Бонус к копанию: x{SHOVEL_MULTIPLIER ** (user.shovel_level - 1):.0f}\n"
        else:
            text += "3. Лопата максимального уровня! 🏆\n"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Смазка", callback_data=f"shop:lube:{user.user_id}"),
                InlineKeyboardButton("Удобрение", callback_data=f"shop:fert:{user.user_id}"),
            ],
            [
                InlineKeyboardButton("Обновить лопату", callback_data=f"shop:shovel:{user.user_id}"),
            ]
        ])

        msg = await update.message.reply_text(text, reply_markup=keyboard)
        await schedule_message_deletion(context, msg.chat_id, msg.message_id, 300)
    finally:
        db.close()


async def shop_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    parts = query.data.split(":")
    # Ожидаем формат: shop:lube:user_id или shop:fert:user_id или shop:shovel:user_id
    data = parts[1]
    owner_id = int(parts[2]) if len(parts) > 2 else None

    # Проверка: меню принадлежит тому, кто тыкает
    if owner_id and query.from_user.id != owner_id:
        await query.answer("Это меню не для тебя! Вызови своё: /shop", show_alert=True)
        return

    db = SessionLocal()
    try:
        user = get_or_create_user(db, query.from_user.id, query.from_user.username)
        if not is_registered(user):
            await query.answer("Сначала выбери пол!", show_alert=True)
            return

        if data == "lube":
            await query.answer()
            msg = await query.message.reply_text(
                "Введи количество смазки для покупки (например: купить смазку 3):"
            )
            await schedule_message_deletion(context, msg.chat_id, msg.message_id, 60)
            return

        elif data == "fert":
            await query.answer()
            msg = await query.message.reply_text(
                "Введи количество удобрения для покупки (например: купить удобрение 2):"
            )
            await schedule_message_deletion(context, msg.chat_id, msg.message_id, 60)
            return

        elif data == "shovel":
            await query.answer()
            if user.shovel_level >= SHOVEL_MAX_LEVEL:
                await query.answer("Лопата уже максимального уровня!", show_alert=True)
                return
            cost = SHOVEL_BASE_PRICE * (SHOVEL_PRICE_MULTIPLIER ** (user.shovel_level - 1))
            if user.balance < cost:
                await query.answer(f"Недостаточно монет! Нужно {cost}", show_alert=True)
                return
            user.balance -= cost
            user.shovel_level += 1
            db.commit()
            # Используем vip_mention для красивого имени
            display_name = vip_mention(user)
            await query.message.reply_text(
                f"✅ Лопата {display_name} улучшена до уровня {user.shovel_level}! "
                f"Бонус x{SHOVEL_MULTIPLIER ** (user.shovel_level - 1):.0f}",
                parse_mode='HTML'
            )
    finally:
        db.close()

async def buy_lube_text(update: Update, context: CallbackContext):
    """Текстовая команда: купить смазку 5"""
    db = SessionLocal()
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.username)
        if not is_registered(user):
            await update.message.reply_text("Сначала выбери пол!")
            return
        match = re.search(r'\d+', update.message.text)
        if not match:
            await update.message.reply_text("Укажи количество: купить смазку 5")
            return
        count = int(match.group())
        if count <= 0:
            await update.message.reply_text("Количество должно быть положительным!")
            return
        total = count * LUBE_PRICE
        if user.balance < total:
            await update.message.reply_text(f"Недостаточно монет! Нужно {total}, у тебя {user.balance}")
            return
        user.balance -= total
        user.lube_count += count
        db.commit()
        await update.message.reply_text(f"✅ Куплено {count} смазки за {total} монет. В инвентаре: {user.lube_count}")
    finally:
        db.close()


async def buy_fertilizer_text(update: Update, context: CallbackContext):
    """Текстовая команда: купить удобрение 3"""
    db = SessionLocal()
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.username)
        if not is_registered(user):
            await update.message.reply_text("Сначала выбери пол!")
            return
        match = re.search(r'\d+', update.message.text)
        if not match:
            await update.message.reply_text("Укажи количество: купить удобрение 3")
            return
        count = int(match.group())
        if count <= 0:
            await update.message.reply_text("Количество должно быть положительным!")
            return
        total = count * FERTILIZER_PRICE
        if user.balance < total:
            await update.message.reply_text(f"Недостаточно монет! Нужно {total}, у тебя {user.balance}")
            return
        user.balance -= total
        user.fertilizer_count += count
        db.commit()
        await update.message.reply_text(f"✅ Куплено {count} удобрения за {total} монет. В инвентаре: {user.fertilizer_count}")
    finally:
        db.close()


async def use_fertilizer_command(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.username)
        if not is_registered(user):
            await update.message.reply_text("Сначала выбери пол!")
            return
        if user.fertilizer_count <= 0:
            await update.message.reply_text("У тебя нет удобрения! Купи в /shop")
            return
        if user.fertilizer_used_this_grow:
            await update.message.reply_text("Ты уже использовал удобрение в этом цикле роста!")
            return

        now = datetime.utcnow()
        is_vip = user.is_vip and user.vip_until and user.vip_until > now
        cooldown_hours = GROW_COOLDOWN_HOURS_VIP if is_vip else GROW_COOLDOWN_HOURS
        cooldown = timedelta(hours=cooldown_hours)
        reduction = timedelta(hours=FERTILIZER_COOLDOWN_REDUCTION_HOURS)

        if user.last_grow:
            user.last_grow -= reduction
            if user.last_grow < now - cooldown:
                user.last_grow = now - cooldown + timedelta(minutes=1)
        else:
            user.last_grow = now - cooldown + reduction

        user.fertilizer_count -= 1
        user.fertilizer_used_this_grow = True
        db.commit()
        await update.message.reply_text("✅ Удобрение использовано! Кулдаун роста кактуса сокращён.")
    finally:
        db.close()


# Обновить лопату
async def upgrade_shovel(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.username)
        if not is_registered(user):
            await update.message.reply_text("Сначала выбери пол!")
            return
        if user.shovel_level >= SHOVEL_MAX_LEVEL:
            await update.message.reply_text("Лопата уже максимального уровня!")
            return
        cost = SHOVEL_BASE_PRICE * (SHOVEL_MULTIPLIER ** (user.shovel_level - 1))
        if user.balance < cost:
            await update.message.reply_text(f"Недостаточно монет! Нужно {cost}")
            return
        user.balance -= cost
        user.shovel_level += 1
        db.commit()
        await update.message.reply_text(f"✅ Лопата улучшена до уровня {user.shovel_level}! Бонус x{SHOVEL_MULTIPLIER ** (user.shovel_level - 1):.0f}")
    finally:
        db.close()
