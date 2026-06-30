BOT_TOKEN = "8455176099:AAG-3Us20Nj43fjr5ecxQ37-2-HE7Ns0Qsc"

ADMINS = ["TheLordStas", "Valkinez6666"]  # без @

# Эмодзи для слотов
SLOT_EMOJIS = ['🍒', '🍋', '🍊', '🍇', '💎', '🔔', '7️⃣', '💀']

# Веса для слотов (шанс выпадения)
SLOT_WEIGHTS = [15, 20, 18, 25, 10, 5, 1, 6]  # сумма 100

# Шанс выпадения VIP
SLOT_WEIGHTS_VIP = [10, 12, 18, 23, 15, 10, 6, 6]  # VIP

# Выплаты за три одинаковых
SLOT_PAYOUTS = {
    '7️⃣': 50,
    '💎': 25,
    '🔔': 10,
    '🍒': 5,
    '🍋': 4,
    '🍊': 4,
    '🍇': 3,
}

# Рулетка
RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

# Мины
MINE_FIELD_SIZE = 5
MINE_COUNT = 5
MINE_START_MULTIPLIER = 0.8
MINE_MULTIPLIER_FACTOR = 1.2
MINE_MULTIPLIER_FACTOR_VIP = 1.35  # VIP бонус

# Double
DOUBLE_WIN_CHANCE = 0.4  # 40%
DOUBLE_WIN_CHANCE_VIP = 0.6  # 60% для VIP

# Кулдауны
GROW_COOLDOWN_HOURS = 24
DIG_COOLDOWN_HOURS = 4
FAP_COOLDOWN_MINUTES = 15
FAP_MAX_PER_DAY = 10

# Кулдауны VIP
GROW_COOLDOWN_HOURS_VIP = 12
DIG_COOLDOWN_HOURS_VIP = 2
FAP_COOLDOWN_MINUTES_VIP = 10
FAP_MAX_PER_DAY_VIP = 15

# Стартовые значения
START_BALANCE = 5000

# Донат (в рублях)
VIP_PRICE_1DAY_RUB = 99
VIP_PRICE_7DAYS_RUB = 349
VIP_PRICE_30DAYS_RUB = 899

# VIP в звёздах Telegram
VIP_1DAY_STARS = 100
VIP_7DAYS_STARS = 350
VIP_30DAYS_STARS = 900

# VIP в BTC
VIP_1DAY_BTC = 0.000022
VIP_7DAYS_BTC = 0.000076
VIP_30DAYS_BTC = 0.00020

# Монеты за рубли
COINS_50000_RUB = 49
COINS_300000_RUB = 229
COINS_1000000_RUB = 449
COINS_2500000_RUB = 999
COINS_10000000_RUB = 3499

# Монеты за звёзды Telegram (⭐)
COINS_50000_STARS = 50
COINS_300000_STARS = 230
COINS_1000000_STARS = 450
COINS_2500000_STARS = 1000
COINS_10000000_STARS = 3500

# Крипта (BTC)
BTC_ADDRESS = "bc1qw95mgrc75x7gdtc8zzkxx2fmfqna80e0kkdxy4"
COINS_50000_BTC = 0.000011
COINS_300000_BTC = 0.000050
COINS_1000000_BTC = 0.000097
COINS_2500000_BTC = 0.00022
COINS_10000000_BTC = 0.00076

# Магазин
LUBE_PRICE = 5000
SHOVEL_BASE_PRICE = 10000
SHOVEL_MULTIPLIER = 2          # Каждое улучшение удваивает награду /dig
SHOVEL_PRICE_MULTIPLIER = 3
SHOVEL_MAX_LEVEL = 10
FERTILIZER_PRICE = 25000
FERTILIZER_COOLDOWN_REDUCTION_HOURS = 4

# Трейд
TRADE_TIMES = [15, 30, 60]     # секунды на выбор

# Таймеры удаления сообщений
GAME_RESULT_DELETE_SECONDS = 30
MENU_TIMEOUT_SECONDS = 300     # 5 минут

# Реквизиты для доната
DONATE_CARD = "2202 2085 4171 2288"
DONATE_PHONE = "+79790796861"
DONATE_BANK = "Сбер"
DONATE_NAME = "Станислав С."
ADMIN_CONTACT = "@TheLordStas"
