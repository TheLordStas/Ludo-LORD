import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, PreCheckoutQueryHandler, filters
)
from config import BOT_TOKEN
from database.db import init_db
from handlers.decorators import registration_required
from handlers.basic import start, help_command, balance, profile
from handlers.donate import (
    donate_menu, donate_callback, donate_pre_checkout,
    donate_successful_payment
)
from handlers.interactions import (
    transfer_handler, fap_reply, fap_solo, grow, dig
)
from handlers.tops import top_fap, top_grow, top_money
from handlers.admin import (
    set_money, null_stats, ban_user, unban_user, vip_grant, vip_remove,
    ban_text, money_text
)
from handlers.registration import gender_callback
from handlers.shop import (
    shop_menu, shop_callback, buy_lube_text, buy_fertilizer_text,
    use_fertilizer_command, upgrade_shovel
)
from games.slots import slots, slots_text
from games.roulette import roulette, roulette_text, roulette_callback
from games.mines import mines, mines_text, mines_callback
from games.dice import dice, dice_text, dice_callback
from games.double import double, double_text
from games.trade import trade_start, trade_callback

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class FapFilter(filters.MessageFilter):
    def filter(self, message):
        if message.text:
            return message.text.lower().strip() in ['фапать', 'фап', 'fap']
        return False


fap_filter = FapFilter()


async def trade_text(update, context):
    parts = update.message.text.strip().split()
    if len(parts) >= 2:
        try:
            bet = int(parts[1])
            context.args = [str(bet)]
            await trade_start(update, context)
        except ValueError:
            await update.message.reply_text("❌ Неверная ставка! Пример: трейд 500")
    else:
        await update.message.reply_text("📈 Укажи ставку: трейд 500")


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # Базовые команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("balance", registration_required(balance)))
    app.add_handler(CommandHandler("profile", registration_required(profile)))

    # Текстовые баланс и профиль
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(баланс)$'), registration_required(balance)))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(профиль)$'), registration_required(profile)))

    # Игры (команды) с проверкой регистрации
    app.add_handler(CommandHandler("slots", registration_required(slots)))
    app.add_handler(CommandHandler("roulette", registration_required(roulette)))
    app.add_handler(CommandHandler("mines", registration_required(mines)))
    app.add_handler(CommandHandler("dice", registration_required(dice)))
    app.add_handler(CommandHandler("double", registration_required(double)))
    app.add_handler(CommandHandler("trade", registration_required(trade_start)))

    # Игры (текстовые) с проверкой регистрации
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(слоты|slots|бандит)\s+\d+$'),
                                   registration_required(slots_text)))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(рулетка|рол|roulette)\s+\d+$'),
                                   registration_required(roulette_text)))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(мины|mine)\s+\d+$'), registration_required(mines_text)))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(кубик|дуэль|дуель|duel)\s+\d+$'),
                                   registration_required(dice_text)))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(удвоение|удвоить|double)\s+\d+$'),
                                   registration_required(double_text)))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(трейд|trade)\s+\d+$'), registration_required(trade_text)))

    # Экономика с проверкой
    app.add_handler(CommandHandler("grow", registration_required(grow)))
    app.add_handler(CommandHandler("dig", registration_required(dig)))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(кактус|растить)$'), registration_required(grow)))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(копать|dig|клад)$'), registration_required(dig)))

    # Топы
    app.add_handler(CommandHandler("topfap", top_fap))
    app.add_handler(CommandHandler("topgrow", top_grow))
    app.add_handler(CommandHandler("topmoney", top_money))

    # Админка
    app.add_handler(CommandHandler("money", set_money))
    app.add_handler(CommandHandler("setnull", null_stats))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("vip", vip_grant))
    app.add_handler(CommandHandler("delvip", vip_remove))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(бан)\s+@\w+\s+\d+$'), ban_text))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(мани)\s+\d+'), money_text))

    # Интерактив с проверкой
    app.add_handler(MessageHandler(filters.REPLY & filters.Regex(r'^\+\d+$'), registration_required(transfer_handler)))
    app.add_handler(MessageHandler(filters.REPLY & fap_filter, registration_required(fap_reply)))
    app.add_handler(MessageHandler(filters.TEXT & fap_filter, registration_required(fap_solo)))

    # Магазин
    app.add_handler(CommandHandler("shop", registration_required(shop_menu)))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^магазин$'), registration_required(shop_menu)))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^купить смазку\s*\d*$'),
                                   registration_required(buy_lube_text)))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^купить удобрение\s*\d*$'),
                                   registration_required(buy_fertilizer_text)))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(удобрить|fertilize)$'),
                                   registration_required(use_fertilizer_command)))
    app.add_handler(CommandHandler("fertilize", registration_required(use_fertilizer_command)))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r'(?i)^обновить лопату$'), registration_required(upgrade_shovel)))
    app.add_handler(CallbackQueryHandler(shop_callback, pattern='^shop:'))

    # Команда /donat и текст
    app.add_handler(CommandHandler("donate", registration_required(donate_menu)))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(донат|donate)$'), registration_required(donate_menu)))

    # Колбэки доната
    app.add_handler(CallbackQueryHandler(donate_callback, pattern='^donate:'))

    # Pre-checkout и оплата
    app.add_handler(PreCheckoutQueryHandler(donate_pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, donate_successful_payment))

    # Колбэки игр и регистрации
    app.add_handler(CallbackQueryHandler(roulette_callback, pattern='^roul_'))
    app.add_handler(CallbackQueryHandler(mines_callback, pattern='^mine_'))
    app.add_handler(CallbackQueryHandler(dice_callback, pattern='^duel_'))
    app.add_handler(CallbackQueryHandler(trade_callback, pattern='^trade_'))
    app.add_handler(CallbackQueryHandler(gender_callback, pattern='^gender:'))

    logger.info("Бот v2.0 запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
