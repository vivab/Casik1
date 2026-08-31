import random
from config import OWNER_ID, OWNER_WIN_CHANCE, PARTNER_WIN_CHANCE
from database import is_partner

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

async def get_role_chance(user_id: int) -> float | None:
    """None = use game default, otherwise forced chance for owner/partner."""
    if is_owner(user_id):
        return OWNER_WIN_CHANCE
    if await is_partner(user_id):
        return PARTNER_WIN_CHANCE
    return None

def roll(chance: float) -> bool:
    return random.random() < chance

def anonymize_id(user_id: int) -> str:
    s = str(user_id)
    return (s[:4] + "***") if len(s) > 4 else s + "***"

def format_money(amount: float) -> str:
    return f"{amount:.2f}$"

def fake_rating():
    """Реалистичные фейковые записи для топа."""
    samples = [
        (1488, 11.62), (3921, 8.47), (7750, 5.13),
        (2034, 4.88), (9912, 3.21), (5567, 2.90),
    ]
    random.shuffle(samples)
    return samples[:3]
