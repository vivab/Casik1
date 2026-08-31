"""Игровая логика: Мины, Башня, Пирамида."""
import random
from utils import get_role_chance, roll

# --- MINES ---
MINES_MULT = {
    3: [1.0, 1.1, 1.25, 1.45, 1.7, 2.0, 2.4, 2.9, 3.5, 4.3],
    5: [1.0, 1.2, 1.5, 1.9, 2.5, 3.3, 4.5, 6.0],
    10: [1.0, 1.4, 2.1, 3.2, 5.0, 8.0],
    15: [1.0, 1.7, 3.0, 5.5, 10.0],
}

def secret_mines_count(chosen: int) -> int:
    """Тайно больше мин."""
    return {3: 6, 5: 9, 10: 14, 15: 18}.get(chosen, chosen + 3)

def generate_mines_field(real_mines: int) -> set:
    cells = list(range(25))
    return set(random.sample(cells, min(real_mines, 25)))

def mines_multiplier(chosen: int, opened: int) -> float:
    arr = MINES_MULT.get(chosen, MINES_MULT[3])
    if opened < len(arr):
        return arr[opened]
    return arr[-1] * (1.2 ** (opened - len(arr) + 1))

# --- TOWER ---
TOWER_MULT = [1.11, 1.33, 1.77, 2.22, 2.78]
TOWER_SECRET = [0, 1, 1, 2, 2]  # extra mines per level

def tower_mines_on_level(level: int) -> int:
    # visible 1 + secret
    return 1 + TOWER_SECRET[level]

# --- PYRAMID ---
PYRAMID_BUTTONS = [7, 5, 4, 3, 2]
PYRAMID_MULT = [1.14, 1.55, 1.88, 2.11, 2.34]
PYRAMID_VISIBLE = [2, 2, 1, 1, 1]
PYRAMID_SECRET = [0, 0, 1, 1, 0]

def pyramid_total_mines(level: int) -> int:
    return PYRAMID_VISIBLE[level] + PYRAMID_SECRET[level]
