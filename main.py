import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import BOT_TOKEN
from database.db import init_db
from handlers.basic import start, help_command, balance
from handlers.interactions import transfer_handler, fap_reply, fap_solo, profile, grow, dig
from handlers.tops import top_fap, top_grow, top_money
from handlers.admin import set_money, null_stats, ban_user, ban_text, money_text
from games.slots import slots, slots_text
from games.roulette import roulette, roulette_text, roulette_callback
from games.mines import mines, mines_text, mines_callback
from games.dice import dice, dice_text, dice_callback
from games.double import double, double_text

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


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # ============ БАЗОВЫЕ КОМАНДЫ ============
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("balance", balance))

    # Текстовые: баланс, all
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)^(баланс)$'),
        balance
    ))

    # ============ ИГРЫ (КОМАНДЫ) ============
    app.add_handler(CommandHandler("slots", slots))
    app.add_handler(CommandHandler("roulette", roulette))
    app.add_handler(CommandHandler("mines", mines))
    app.add_handler(CommandHandler("dice", dice))
    app.add_handler(CommandHandler("double", double))

    # ============ ИГРЫ (ТЕКСТОВЫЕ КОМАНДЫ) ============
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)^(слоты|слот|бандит)\s+\d+$'),
        slots_text
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)^(рулетка|рол)\s+\d+$'),
        roulette_text
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)^(мины|mine)\s+\d+$'),
        mines_text
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)^(кубик|дуэль|дуель|duel)\s+\d+$'),
        dice_text
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)^(удвоение|удвоить|double)\s+\d+$'),
        double_text
    ))

    # ============ ЭКОНОМИКА И ПРОФИЛЬ ============
    app.add_handler(CommandHandler("grow", grow))
    app.add_handler(CommandHandler("dig", dig))
    app.add_handler(CommandHandler("profile", profile))

    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)^(кактус|растить)$'),
        grow
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)^(копать|коп|раскопки)$'),
        dig
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)^(профиль)$'),
        profile
    ))

    # ============ ТОПЫ ============
    app.add_handler(CommandHandler("topfap", top_fap))
    app.add_handler(CommandHandler("topgrow", top_grow))
    app.add_handler(CommandHandler("topmoney", top_money))

    # ============ АДМИНКА ============
    app.add_handler(CommandHandler("money", set_money))
    app.add_handler(CommandHandler("setnull", null_stats))
    app.add_handler(CommandHandler("ban", ban_user))

    # Текстовые админские команды
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)^(бан)\s+@\w+\s+\d+$'),
        ban_text
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)^(мани)\s+\d+'),
        money_text
    ))

    # ============ ИНТЕРАКТИВ ============
    app.add_handler(MessageHandler(
        filters.REPLY & filters.Regex(r'^\+\d+$'),
        transfer_handler
    ))
    app.add_handler(MessageHandler(
        filters.REPLY & fap_filter,
        fap_reply
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & fap_filter,
        fap_solo
    ))

    # ============ CALLBACK QUERY ============
    app.add_handler(CallbackQueryHandler(roulette_callback, pattern='^roul_'))
    app.add_handler(CallbackQueryHandler(mines_callback, pattern='^mine_'))
    app.add_handler(CallbackQueryHandler(dice_callback, pattern='^duel_'))

    logger.info("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
