import random
from config import OWNER_ID, OWNER_WIN, PARTNER_WIN, MINES_SIZE

def is_owner(uid: int) -> bool:
    return uid == OWNER_ID

async def role_chance(uid: int):
    from database import is_partner
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
    """+2 тайных, макс +15, не больше размера поля."""
    extra = min(15, 2 + (chosen // 5) * 2)
    return min(MINES_SIZE, chosen + extra)
