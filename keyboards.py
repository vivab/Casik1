from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu(is_owner: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🔥 Играть", callback_data="play")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton("🏆 Рейтинг", callback_data="rating")],
        [InlineKeyboardButton("👥 Рефералка", callback_data="referral")],
    ]
    if is_owner:
        rows.append([InlineKeyboardButton("👑 Владелец", callback_data="owner_menu")])
    return InlineKeyboardMarkup(rows)

def play_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💣 Мины", callback_data="game_mines")],
        [InlineKeyboardButton("🗼 Башня", callback_data="game_tower")],
        [InlineKeyboardButton("🔺 Пирамида", callback_data="game_pyramid")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
    ])

def balance_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Пополнить", callback_data="deposit")],
        [InlineKeyboardButton("➖ Вывести", callback_data="withdraw")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
    ])

def rating_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1 день", callback_data="rating_day")],
        [InlineKeyboardButton("1 месяц", callback_data="rating_month")],
        [InlineKeyboardButton("Всё время", callback_data="rating_all")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
    ])

def owner_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Партнёры", callback_data="owner_partners")],
        [InlineKeyboardButton("📊 Статистика", callback_data="owner_stats")],
        [InlineKeyboardButton("📋 Команды", callback_data="owner_commands")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
    ])

def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]])

def mines_bet_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("3 мины", callback_data="mines_count:3"),
         InlineKeyboardButton("5 мин", callback_data="mines_count:5")],
        [InlineKeyboardButton("10 мин", callback_data="mines_count:10"),
         InlineKeyboardButton("15 мин", callback_data="mines_count:15")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="play")],
    ])

def cashout_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Забрать выигрыш", callback_data="cashout")],
    ])
