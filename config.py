BOT_TOKEN = "8455176099:AAG-3Us20Nj43fjr5ecxQ37-2-HE7Ns0Qsc"

ADMINS = ["TheLordStas", "Valkinez6666"]  # без @

# Эмодзи для слотов
SLOT_EMOJIS = ['🍒', '🍋', '🍊', '🍇', '💎', '🔔', '7️⃣', '💀']

# Веса для слотов (шанс выпадения)
SLOT_WEIGHTS = [15, 20, 18, 25, 10, 5, 1, 6]  # сумма 100

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

# Кулдауны
GROW_COOLDOWN_HOURS = 24
DIG_COOLDOWN_HOURS = 4
FAP_COOLDOWN_MINUTES = 15
FAP_MAX_PER_DAY = 20

# Стартовые значения
START_BALANCE = 5000
