import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
CRYPTO_PAY_TOKEN = os.getenv("CRYPTO_PAY_TOKEN", "")
CRYPTO_ASSET = os.getenv("CRYPTO_ASSET", "USDT")
MIN_BET = float(os.getenv("MIN_BET", "0.1"))
MIN_DEPOSIT = float(os.getenv("MIN_DEPOSIT", "0.1"))
MIN_WITHDRAW = float(os.getenv("MIN_WITHDRAW", "0.1"))
DB_NAME = os.getenv("DB_NAME", "casino.db")

OWNER_WIN = 0.92
PARTNER_WIN = 0.65
FREEBET_AMOUNT = 5.0
FREEBET_MULTIPLIER_NEEDED = 10  # нужно x10 от фрибета чтобы вывести

# Авторские игры: (множитель, видимый_шанс, реальный_шанс_выйгрыша)
AUTHOR_GAMES = {
    "x2":   (2,   50, 0.40),
    "x3":   (3,   33, 0.25),
    "x4":   (4,   25, 0.20),
    "x5":   (5,   20, 0.10),
    "x10":  (10,  10, 0.03),
    "x100": (100, 1,  0.00),
}

TOWER_MULT = [1.11, 1.33, 1.77, 2.22, 2.78]
TOWER_SECRET = [0, 1, 1, 2, 2]

PYRAMID_BTNS = [7, 5, 4, 3, 2]
PYRAMID_MULT = [1.14, 1.55, 1.88, 2.11, 2.34]
PYRAMID_VIS = [2, 2, 1, 1, 1]
PYRAMID_SEC = [0, 0, 1, 1, 0]
