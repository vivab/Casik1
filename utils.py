import random
from config import OWNER_ID, OWNER_WIN, PARTNER_WIN
from database import is_partner

def is_owner(uid: int) -> bool:
    return uid == OWNER_ID

async def role_chance(uid: int):
    if is_owner(uid): return OWNER_WIN
    if await is_partner(uid): return PARTNER_WIN
    return None

def roll(chance: float) -> bool:
    return random.random() < chance

def anon(uid: int) -> str:
    s = str(uid)
    return s[:4] + "***" if len(s) > 4 else s + "***"

def money(a: float) -> str:
    return f"{a:.2f}$"

def secret_mines(chosen: int) -> int:
    """Тайные мины: +2, максимум +15 дополнительных."""
    extra = min(15, 2 + (chosen // 5) * 2)
    return min(24, chosen + extra)
