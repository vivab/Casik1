import random
from config import TOWER_MULT, TOWER_SECRET, PYRAMID_BTNS, PYRAMID_MULT, PYRAMID_VIS, PYRAMID_SEC

def mines_mult(chosen: int, opened: int) -> float:
    # простой рост
    base = 1.0 + (chosen / 25) * 0.5
    return round(base * (1.15 ** opened), 2)

def gen_field(n_mines: int) -> set:
    return set(random.sample(range(25), min(n_mines, 25)))

def tower_mines(level: int) -> int:
    return 1 + TOWER_SECRET[level]

def pyramid_mines(level: int) -> int:
    return PYRAMID_VIS[level] + PYRAMID_SEC[level]
