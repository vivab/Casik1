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

OWNER_WIN_CHANCE = 0.92
PARTNER_WIN_CHANCE = 0.65
