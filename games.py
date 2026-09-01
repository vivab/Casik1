import random
from config import TOWER_MULT, TOWER_SECRET, PYRAMID_BTNS, PYRAMID_MULT, PYRAMID_VIS, PYRAMID_SEC, MINES_SIZE

def mines_mult(chosen: int, opened: int) -> float:
    """Более мягкий рост икса."""
    if opened <= 0:
        return 1.0
    # чем больше мин — тем выше рост, но умеренно
    factor = 1.08 + (chosen / 100)
    return round(1.0 * (factor ** opened), 2)

def gen_field(n_mines: int) -> set:
    return set(random.sample(range(MINES_SIZE), min(n_mines, MINES_SIZE)))

def tower_mines(level: int) -> int:
    return 1 + TOWER_SECRET[level]

def pyramid_mines(level: int) -> int:
    return PYRAMID_VIS[level] + PYRAMID_SEC[level]
