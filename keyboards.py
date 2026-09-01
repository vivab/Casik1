from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu(owner=False):
    rows = [
        [InlineKeyboardButton("🔥 Играть", callback_data="play")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton("🏆 Рейтинг", callback_data="rating")],
        [InlineKeyboardButton("👥 Рефералка", callback_data="referral")],
    ]
    if owner:
        rows.append([InlineKeyboardButton("👑 Владелец", callback_data="owner")])
    return InlineKeyboardMarkup(rows)

def play_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Мини-игры", callback_data="mini_games")],
        [InlineKeyboardButton("🎨 Авторские игры", callback_data="author_games")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
    ])

def mini_games_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💣 Мины", callback_data="game_mines")],
        [InlineKeyboardButton("🗼 Башня", callback_data="game_tower")],
        [InlineKeyboardButton("🔺 Пирамида", callback_data="game_pyramid")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="play")],
    ])

def author_games_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 x2 (50%)", callback_data="author:x2")],
        [InlineKeyboardButton("💧 x3 (33%)", callback_data="author:x3")],
        [InlineKeyboardButton("🥬 x4 (25%)", callback_data="author:x4")],
        [InlineKeyboardButton("🐠 x5 (20%)", callback_data="author:x5")],
        [InlineKeyboardButton("🏴‍☠️ x10 (10%)", callback_data="author:x10")],
        [InlineKeyboardButton("👑 x100 (1%)", callback_data="author:x100")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="play")],
    ])

def balance_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Пополнить", callback_data="deposit")],
        [InlineKeyboardButton("➖ Вывести", callback_data="withdraw")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
    ])

def need_money_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Пополнить", callback_data="deposit")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
    ])

def after_game_kb(game_cb: str):
    """Сыграть снова / Изменить ставку / В меню"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Сыграть снова", callback_data=f"again:{game_cb}")],
        [InlineKeyboardButton("✏️ Изменить ставку", callback_data=f"setbet:{game_cb}")],
        [InlineKeyboardButton("🏠 В меню", callback_data="back_main")],
    ])

def bet_saved_kb(game_cb: str, bet: float):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💵 Ставка: {bet:.2f}$ — Играть!", callback_data=f"go:{game_cb}")],
        [InlineKeyboardButton("✏️ Изменить ставку", callback_data=f"setbet:{game_cb}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="play")],
    ])

def back_main():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]])

def back_play():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="play")]])

def owner_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Партнёры", callback_data="owner_partners")],
        [InlineKeyboardButton("📋 Команды", callback_data="owner_cmds")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
    ])
