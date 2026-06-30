from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import CallbackContext
from database.db import SessionLocal
from database.economy import get_or_create_user
from database.helpers import is_registered
from config import *

OWNER_ID = 616344869  # Eведомления о донатах, Telegram ID владельца


async def donate_menu(update: Update, context: CallbackContext):
    """Главное меню доната (/donat, 'донат')"""
    db = SessionLocal()
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.username)
        if not is_registered(user):
            await update.message.reply_text("Сначала выбери пол! /start")
            return

        uid = user.user_id
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 VIP", callback_data=f"donate:vip_menu:{uid}")],
            [InlineKeyboardButton("💰 Монеты", callback_data=f"donate:coins_menu:{uid}")],
            [InlineKeyboardButton("⭐ Оплата звёздами", callback_data=f"donate:stars:{uid}")],
            [InlineKeyboardButton("💳 Рубли / Карта", callback_data=f"donate:rub:{uid}")],
            [InlineKeyboardButton("₿ Криптовалюта", callback_data=f"donate:crypto:{uid}")],
        ])

        vip_status = "✅ Активен" if (
                    user.is_vip and user.vip_until and user.vip_until > datetime.utcnow()) else "❌ Не активен"
        vip_until = f" до {user.vip_until.strftime('%d.%m.%Y')}" if (
                    user.vip_until and user.vip_until > datetime.utcnow()) else ""

        await update.message.reply_text(
            f"💎 ДОНАТ-МЕНЮ\n\n"
            f"💎 VIP: {vip_status}{vip_until}\n"
            f"💰 Баланс: {user.balance} монет\n\n"
            f"Выбери категорию:",
            reply_markup=keyboard
        )
    finally:
        db.close()


# ==================== ОБРАБОТЧИКИ КОЛБЭКОВ ====================

async def donate_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split(":")
    action = data[1]
    owner_id = int(data[2])

    # Проверка: меню принадлежит тому, кто тыкает
    if query.from_user.id != owner_id:
        await query.answer("Это меню не для тебя! Вызови своё: /donat", show_alert=True)
        return

    await query.answer()

    if action == "vip_menu":
        await show_vip_menu(query, owner_id)
    elif action == "coins_menu":
        await show_coins_menu(query, owner_id)
    elif action == "stars":
        await show_stars_menu(query, owner_id)
    elif action == "rub":
        await show_rub_details(query, owner_id)
    elif action == "crypto":
        await show_crypto_details(query, owner_id)
    # ===== VIP: выбор срока и инвойс =====
    elif action == "vip_buy":
        days = int(data[3])
        await send_vip_invoice(query, owner_id, days)
    # ===== Монеты: инвойс =====
    elif action == "coins_buy":
        coins = int(data[3])
        stars = int(data[4])
        await send_coins_invoice(query, owner_id, coins, stars)
    elif action == "back":
        await show_main_menu(query, owner_id)


# ==================== VIP ====================

async def show_vip_menu(query, uid):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⭐ 1 день — {VIP_1DAY_STARS}⭐", callback_data=f"donate:vip_buy:{uid}:1")],
        [InlineKeyboardButton(f"⭐ 7 дней — {VIP_7DAYS_STARS}⭐", callback_data=f"donate:vip_buy:{uid}:7")],
        [InlineKeyboardButton(f"⭐ 30 дней — {VIP_30DAYS_STARS}⭐", callback_data=f"donate:vip_buy:{uid}:30")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"donate:stars:{uid}")],
    ])
    await query.edit_message_text(
        "💎 VIP через звёзды\n\nВыбери срок подписки:",
        reply_markup=keyboard
    )


async def send_vip_invoice(query, uid, days):
    if days == 1:
        stars = VIP_1DAY_STARS
        title = "VIP на 1 день"
    elif days == 7:
        stars = VIP_7DAYS_STARS
        title = "VIP на 7 дней"
    else:
        stars = VIP_30DAYS_STARS
        title = "VIP на 30 дней"

    await query.message.delete()
    await query.message.chat.send_invoice(
        title=title,
        description=f"Повышенные шансы, ускоренные кулдауны, значок 💎\nДля ID: {uid}",
        payload=f"donate_vip:{uid}:{days}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(title, stars)],
        start_parameter="donate_vip"
    )


# ==================== МОНЕТЫ ====================

async def show_coins_menu(query, uid):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"50,000 монет — {COINS_50000_STARS}⭐",
                              callback_data=f"donate:coins_buy:{uid}:50000:{COINS_50000_STARS}")],
        [InlineKeyboardButton(f"300,000 монет — {COINS_300000_STARS}⭐",
                              callback_data=f"donate:coins_buy:{uid}:300000:{COINS_300000_STARS}")],
        [InlineKeyboardButton(f"1,000,000 монет — {COINS_1000000_STARS}⭐",
                              callback_data=f"donate:coins_buy:{uid}:1000000:{COINS_1000000_STARS}")],
        [InlineKeyboardButton(f"2,500,000 монет — {COINS_2500000_STARS}⭐",
                              callback_data=f"donate:coins_buy:{uid}:2500000:{COINS_2500000_STARS}")],
        [InlineKeyboardButton(f"10,000,000 монет — {COINS_10000000_STARS}⭐",
                              callback_data=f"donate:coins_buy:{uid}:10000000:{COINS_10000000_STARS}")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"donate:stars:{uid}")],
    ])
    await query.edit_message_text(
        "💰 Монеты через звёзды\n\nВыбери пакет:",
        reply_markup=keyboard
    )


async def send_coins_invoice(query, uid, coins, stars):
    title = f"{coins:,} монет".replace(",", " ")
    await query.message.delete()
    await query.message.chat.send_invoice(
        title=title,
        description=f"Покупка {coins:,} игровых монет\nДля ID: {uid}".replace(",", " "),
        payload=f"donate_coins:{uid}:{coins}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(title, stars)],
        start_parameter="donate_coins"
    )


# ==================== ЗВЁЗДЫ (общее меню) ====================

async def show_stars_menu(query, uid):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 VIP", callback_data=f"donate:vip_menu:{uid}")],
        [InlineKeyboardButton("💰 Монеты", callback_data=f"donate:coins_menu:{uid}")],
        [InlineKeyboardButton("💳 Рубли / Карта", callback_data=f"donate:rub:{uid}")],
        [InlineKeyboardButton("₿ Криптовалюта", callback_data=f"donate:crypto:{uid}")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"donate:back:{uid}")],
    ])
    await query.edit_message_text(
        "⭐ Оплата звёздами Telegram\n\nВыбери категорию:",
        reply_markup=keyboard
    )


# ==================== РУБЛИ ====================

async def show_rub_details(query, uid):
    text = (
        "💳 ДОНАТ В РУБЛЯХ\n\n"
        f"💎 VIP:\n"
        f"• 1 день — {VIP_PRICE_1DAY_RUB}₽\n"
        f"• 7 дней — {VIP_PRICE_7DAYS_RUB}₽\n"
        f"• 30 дней — {VIP_PRICE_30DAYS_RUB}₽\n\n"
        f"💰 МОНЕТЫ:\n"
        f"• 50,000 — {COINS_50000_RUB}₽\n"
        f"• 300,000 — {COINS_300000_RUB}₽\n"
        f"• 1,000,000 — {COINS_1000000_RUB}₽\n"
        f"• 2,500,000 — {COINS_2500000_RUB}₽\n"
        f"• 10,000,000 — {COINS_10000000_RUB}₽\n\n"
        f"💳 Реквизиты:\n"
        f"Банк: {DONATE_BANK}\n"
        f"Карта: <code>{DONATE_CARD}</code>\n"
        f"Получатель: {DONATE_NAME}\n\n"
        f"📝 После перевода напиши {ADMIN_CONTACT}\n"
        f"Укажи свой ID: <code>{uid}</code> и сумму"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data=f"donate:back:{uid}")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')


# ==================== КРИПТА ====================
def format_btc(value: float) -> str:
    """Форматирует BTC без экспоненты: 0.000022 вместо 2.2e-05"""
    return f"{value:.8f}".rstrip('0').rstrip('.')


async def show_crypto_details(query, uid):
    text = (
        "₿ ДОНАТ ЧЕРЕЗ КРИПТУ\n\n"
        f"💎 VIP:\n"
        f"• 1 день — {format_btc(VIP_1DAY_BTC)} BTC\n"
        f"• 7 дней — {format_btc(VIP_7DAYS_BTC)} BTC\n"
        f"• 30 дней — {format_btc(VIP_30DAYS_BTC)} BTC\n\n"
        f"💰 МОНЕТЫ:\n"
        f"• 50,000 — {format_btc(COINS_50000_BTC)} BTC\n"
        f"• 300,000 — {format_btc(COINS_300000_BTC)} BTC\n"
        f"• 1,000,000 — {format_btc(COINS_1000000_BTC)} BTC\n"
        f"• 2,500,000 — {format_btc(COINS_2500000_BTC)} BTC\n"
        f"• 10,000,000 — {format_btc(COINS_10000000_BTC)} BTC\n\n"
        f"📥 Кошелёк:\n"
        f"<code>{BTC_ADDRESS}</code>\n\n"
        f"📝 После перевода напиши {ADMIN_CONTACT}\n"
        f"Укажи свой ID: <code>{uid}</code> и хеш транзакции"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data=f"donate:back:{uid}")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')


# ==================== PRE-CHECKOUT И УСПЕШНАЯ ОПЛАТА ====================

async def donate_pre_checkout(update: Update, context: CallbackContext):
    query = update.pre_checkout_query
    if not query.invoice_payload.startswith("donate_"):
        await query.answer(ok=False, error_message="Неверный платёж")
        return
    await query.answer(ok=True)


async def donate_successful_payment(update: Update, context: CallbackContext):
    msg = update.message
    if not msg.successful_payment:
        return

    payload = msg.successful_payment.invoice_payload
    parts = payload.split(":")

    if len(parts) < 3:
        return

    action = parts[0]  # donate_vip или donate_coins
    uid = int(parts[1])
    value = int(parts[2])

    db = SessionLocal()
    try:
        user = get_or_create_user(db, uid, msg.from_user.username)

        if action == "donate_vip":
            now = datetime.utcnow()
            if user.vip_until and user.vip_until > now:
                user.vip_until += timedelta(days=value)
            else:
                user.vip_until = now + timedelta(days=value)
            user.is_vip = True
            db.commit()
            await msg.reply_text(f"💎 VIP-статус продлён на {value} дн. Спасибо!")

        elif action == "donate_coins":
            user.balance += value
            db.commit()
            await msg.reply_text(f"✅ +{value:,} монет!\n💰 Баланс: {user.balance}".replace(",", " "))

        # Уведомление владельцу (опционально)
        if OWNER_ID:
            await context.bot.send_message(
                OWNER_ID,
                f"💰 Новый донат!\n"
                f"Пользователь: @{user.username} ({uid})\n"
                f"Тип: {'VIP' if action == 'donate_vip' else 'Монеты'}\n"
                f"Сумма/Срок: {value}"
            )

    finally:
        db.close()


# ==================== КОМАНДА НАЗАД ====================

async def show_main_menu(query, uid):
    db = SessionLocal()
    try:
        user = get_or_create_user(db, uid)
        vip_status = "✅ Активен" if (user.is_vip and user.vip_until and user.vip_until > datetime.utcnow()) else "❌ Не активен"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 VIP", callback_data=f"donate:vip_menu:{uid}")],
            [InlineKeyboardButton("💰 Монеты", callback_data=f"donate:coins_menu:{uid}")],
            [InlineKeyboardButton("⭐ Оплата звёздами", callback_data=f"donate:stars:{uid}")],
            [InlineKeyboardButton("💳 Рубли / Карта", callback_data=f"donate:rub:{uid}")],
            [InlineKeyboardButton("₿ Криптовалюта", callback_data=f"donate:crypto:{uid}")],
        ])
        await query.edit_message_text(
            f"💎 ДОНАТ-МЕНЮ\n\n💎 VIP: {vip_status}\n💰 Баланс: {user.balance} монет\n\nВыбери категорию:",
            reply_markup=keyboard
        )
    finally:
        db.close()
