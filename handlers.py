from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import *
from keyboards import *
from utils import *
from config import *
from crypto_pay import create_invoice
from games import *
import random

WAITING_DEPOSIT, WAITING_WITHDRAW, WAITING_BET = range(3)

# ========== START / MENU ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await ensure_user(u.id, u.username or "")
    if context.args and context.args[0].startswith("ref_"):
        try:
            rid = int(context.args[0][4:])
            if rid != u.id:
                await set_referrer(u.id, rid)
        except Exception:
            pass
    await update.message.reply_text(
        "🎰 Добро пожаловать!\n\nВыберите действие:",
        reply_markup=main_menu(is_owner(u.id))
    )

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.message.edit_text("🎰 Главное меню", reply_markup=main_menu(is_owner(q.from_user.id)))

# ========== PROFILE / BALANCE ==========
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = await get_user(q.from_user.id)
    bal = await get_balance(q.from_user.id)
    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"Ник: @{user.get('username') or '—'}\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Баланс: <b>{format_money(bal)}</b>"
    )
    await q.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")

async def balance_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    bal = await get_balance(q.from_user.id)
    real = await get_real_balance(q.from_user.id)
    await q.message.edit_text(
        f"💰 <b>Баланс</b>\n\nДоступно: <b>{format_money(bal)}</b>\nРеальный: {format_money(real)}",
        reply_markup=balance_menu(), parse_mode="HTML"
    )

# ========== DEPOSIT ==========
async def deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text(f"Введите сумму пополнения (мин. {MIN_DEPOSIT}$):", reply_markup=back_kb())
    return WAITING_DEPOSIT

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(",", ".").replace("$", "").strip())
    except Exception:
        await update.message.reply_text("Введите число, например 1.5")
        return WAITING_DEPOSIT
    if amount < MIN_DEPOSIT:
        await update.message.reply_text(f"Минимум {MIN_DEPOSIT}$")
        return WAITING_DEPOSIT

    inv = await create_invoice(amount, update.effective_user.id)
    if not inv:
        # Fallback: сразу зачисляем для теста если нет токена
        await add_balance(update.effective_user.id, amount)
        await update.message.reply_text(
            f"✅ (тест) Зачислено {format_money(amount)}\n"
            f"Для реальных платежей укажи CRYPTO_PAY_TOKEN"
        )
        return ConversationHandler.END

    await create_transaction(update.effective_user.id, "deposit", amount, str(inv.get("invoice_id", "")))
    url = inv.get("pay_url") or inv.get("bot_invoice_url") or ""
    await update.message.reply_text(
        f"💳 Счёт на <b>{format_money(amount)}</b>\n\nОплатите:\n{url}\n\nПосле оплаты баланс придёт автоматически.",
        parse_mode="HTML"
    )
    return ConversationHandler.END

# ========== WITHDRAW ==========
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    real = await get_real_balance(q.from_user.id)
    if real < MIN_WITHDRAW:
        await q.answer(f"Минимум {MIN_WITHDRAW}$ на реальном балансе", show_alert=True)
        return
    await q.message.edit_text(
        f"Реальный баланс: {format_money(real)}\nВведите сумму вывода (мин. {MIN_WITHDRAW}$):",
        reply_markup=back_kb()
    )
    return WAITING_WITHDRAW

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(",", ".").replace("$", "").strip())
    except Exception:
        await update.message.reply_text("Введите число")
        return WAITING_WITHDRAW
    if amount < MIN_WITHDRAW:
        await update.message.reply_text(f"Минимум {MIN_WITHDRAW}$")
        return WAITING_WITHDRAW
    real = await get_real_balance(update.effective_user.id)
    if amount > real:
        await update.message.reply_text("Недостаточно средств на реальном балансе")
        return WAITING_WITHDRAW

    ok = await subtract_balance(update.effective_user.id, amount)
    if not ok:
        await update.message.reply_text("Ошибка списания")
        return ConversationHandler.END

    tid = await create_transaction(update.effective_user.id, "withdraw", amount, status="pending")
    # Уведомляем владельца
    try:
        await context.bot.send_message(
            OWNER_ID,
            f"💸 Заявка на вывод #{tid}\nUser: {update.effective_user.id}\nСумма: {format_money(amount)}"
        )
    except Exception:
        pass
    await update.message.reply_text(
        f"✅ Заявка на вывод <b>{format_money(amount)}</b> создана.\nОжидайте обработки.",
        parse_mode="HTML"
    )
    return ConversationHandler.END

# ========== RATING ==========
async def rating_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text("🏆 Рейтинг — выберите период:", reply_markup=rating_menu())

async def rating_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    real = await get_top_players(limit=3)
    fake = fake_rating()
    # смешиваем
    combined = [(anonymize_id(r["user_id"]), r["total_won"]) for r in real] + [(anonymize_id(f[0]), f[1]) for f in fake]
    random.shuffle(combined)
    combined = sorted(combined, key=lambda x: -x[1])[:3]
    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 <b>Топ-3</b>\n\n"
    for i, (uid, won) in enumerate(combined):
        text += f"{medals[i]} {uid} — {format_money(won)}\n"
    await q.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")

# ========== REFERRAL ==========
async def referral_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    bot_info = await context.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{q.from_user.id}"
    partner = await is_partner(q.from_user.id)
    if partner:
        desc = "Партнёр: вы получаете <b>20%</b> с проигрышей приглашённых."
    else:
        desc = "Вы получаете <b>5%</b> с пополнений приглашённых."
    text = (
        f"👥 <b>Рефералка</b>\n\n{desc}\n\n"
        f"Ваша ссылка:\n<code>{link}</code>"
    )
    await q.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")

# ========== OWNER ==========
async def owner_menu_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_owner(q.from_user.id):
        return
    await q.message.edit_text("👑 Меню владельца", reply_markup=owner_menu())

async def owner_partners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_owner(q.from_user.id):
        return
    partners = await list_partners()
    text = "👥 <b>Партнёры</b>\n\n"
    if not partners:
        text += "Пусто"
    else:
        for p in partners:
            text += f"• <code>{p['user_id']}</code>\n"
    text += "\n/addpartner ID"
    await q.message.edit_text(text, reply_markup=owner_menu(), parse_mode="HTML")

async def owner_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = (
        "📋 <b>Команды</b>\n\n"
        "/addpartner ID — партнёр (65%)\n"
        "/give ID сумма — временный баланс (1ч)\n"
        "/pay ID — подтвердить вывод\n"
    )
    await q.message.edit_text(text, reply_markup=owner_menu(), parse_mode="HTML")

async def addpartner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("/addpartner ID")
        return
    pid = int(context.args[0])
    await ensure_user(pid)
    await set_partner(pid, update.effective_user.id)
    await update.message.reply_text(f"✅ Партнёр {pid} добавлен")

async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    if len(context.args) < 2:
        await update.message.reply_text("/give ID сумма")
        return
    uid, amount = int(context.args[0]), float(context.args[1])
    await ensure_user(uid)
    await add_balance(uid, amount, is_temp=True, hours=1)
    await update.message.reply_text(f"✅ {format_money(amount)} временно выдано {uid}")

# ========== PLAY ==========
async def play_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text("🔥 Выберите игру:", reply_markup=play_menu())

# ========== MINES ==========
async def mines_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text(
        f"💣 <b>Мины</b>\n\nВыберите количество мин:\nМин. ставка {MIN_BET}$",
        reply_markup=mines_bet_kb(), parse_mode="HTML"
    )

async def mines_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    count = int(q.data.split(":")[1])
    context.user_data["mines_count"] = count
    await q.message.edit_text(
        f"Выбрано мин: {count}\nВведите ставку (мин. {MIN_BET}$):",
        reply_markup=back_kb()
    )
    context.user_data["waiting_bet"] = "mines"
    return WAITING_BET

async def process_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bet = float(update.message.text.replace(",", ".").replace("$", "").strip())
    except Exception:
        await update.message.reply_text("Введите число")
        return WAITING_BET
    if bet < MIN_BET:
        await update.message.reply_text(f"Минимум {MIN_BET}$")
        return WAITING_BET

    bal = await get_balance(update.effective_user.id)
    if bal < bet:
        await update.message.reply_text("Недостаточно средств")
        return ConversationHandler.END

    game = context.user_data.get("waiting_bet")
    if game == "mines":
        return await start_mines_game(update, context, bet)
    if game == "tower":
        return await start_tower_game(update, context, bet)
    if game == "pyramid":
        return await start_pyramid_game(update, context, bet)
    return ConversationHandler.END

async def start_mines_game(update, context, bet):
    uid = update.effective_user.id
    await subtract_balance(uid, bet)
    chosen = context.user_data.get("mines_count", 3)
    real_cnt = secret_mines_count(chosen)

    # Анти-абуз
    qc = await get_quick_cashouts(uid)
    force_lose = qc >= 10

    role_chance = await get_role_chance(uid)
    if force_lose:
        will_win = False
    elif role_chance is not None:
        will_win = roll(role_chance)
    else:
        will_win = True  # обычный игрок играет по полю

    field = generate_mines_field(real_cnt)
    context.user_data["mines"] = {
        "bet": bet,
        "chosen": chosen,
        "field": field,
        "opened": [],
        "will_win": will_win,
        "force_lose": force_lose,
        "mult": 1.0,
    }
    await show_mines_field(update, context)
    return ConversationHandler.END

async def show_mines_field(update, context, edit=False):
    m = context.user_data.get("mines")
    if not m:
        return
    buttons = []
    for i in range(5):
        row = []
        for j in range(5):
            idx = i * 5 + j
            if idx in m["opened"]:
                row.append(InlineKeyboardButton("✅", callback_data="mines_open:done"))
            else:
                row.append(InlineKeyboardButton("🟦", callback_data=f"mines_open:{idx}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("✅ Забрать выигрыш", callback_data="mines_cashout")])
    buttons.append([InlineKeyboardButton("⬅️ Выход", callback_data="play")])
    mult = mines_multiplier(m["chosen"], len(m["opened"]))
    win = m["bet"] * mult
    text = (
        f"💣 <b>Мины</b> ({m['chosen']} мин)\n"
        f"Ставка: {format_money(m['bet'])}\n"
        f"Открыто: {len(m['opened'])}\n"
        f"Множитель: <b>x{mult:.2f}</b>\n"
        f"Выигрыш: <b>{format_money(win)}</b>"
    )
    kb = InlineKeyboardMarkup(buttons)
    if edit and update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def mines_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    m = context.user_data.get("mines")
    if not m:
        await q.answer("Игра не найдена", show_alert=True)
        return
    if q.data == "mines_open:done":
        return
    idx = int(q.data.split(":")[1])
    if idx in m["opened"]:
        return

    # Проверка мины
    hit = idx in m["field"]
    if m.get("force_lose") and len(m["opened"]) >= 0:
        # можно форсировать на первом же ходе иногда
        if random.random() < 0.7:
            hit = True

    if hit:
        # показываем только chosen количество мин
        show = list(m["field"])[:m["chosen"]]
        if idx not in show:
            show[0] = idx
        text = f"💥 <b>Взрыв!</b>\nВы попали на мину.\nСтавка {format_money(m['bet'])} потеряна."
        await log_game(q.from_user.id, "mines", m["bet"], "lose", -m["bet"])
        # рефералка партнёру с проигрыша
        ref = await get_referrer(q.from_user.id)
        if ref and await is_partner(ref):
            earn = m["bet"] * 0.20
            await add_referral_earn(ref, q.from_user.id, earn, "loss")
        context.user_data.pop("mines", None)
        await q.message.edit_text(text, reply_markup=play_menu(), parse_mode="HTML")
        return

    m["opened"].append(idx)
    m["mult"] = mines_multiplier(m["chosen"], len(m["opened"]))
    await show_mines_field(update, context, edit=True)

async def mines_cashout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    m = context.user_data.get("mines")
    if not m or not m["opened"]:
        await q.answer("Нечего забирать", show_alert=True)
        return
    mult = mines_multiplier(m["chosen"], len(m["opened"]))
    win = m["bet"] * mult
    profit = win - m["bet"]
    await add_balance(q.from_user.id, win)
    await log_game(q.from_user.id, "mines", m["bet"], "win", profit)
    if len(m["opened"]) <= 2:
        await inc_quick_cashout(q.from_user.id)
    else:
        await reset_quick_cashout(q.from_user.id)
    context.user_data.pop("mines", None)
    await q.message.edit_text(
        f"✅ Забрано <b>{format_money(win)}</b> (x{mult:.2f})",
        reply_markup=play_menu(), parse_mode="HTML"
    )

# ========== TOWER ==========
async def tower_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["waiting_bet"] = "tower"
    await q.message.edit_text(
        f"🗼 <b>Башня</b>\n\n5 уровней. Введите ставку (мин. {MIN_BET}$):",
        reply_markup=back_kb(), parse_mode="HTML"
    )
    return WAITING_BET

async def start_tower_game(update, context, bet):
    uid = update.effective_user.id
    await subtract_balance(uid, bet)
    qc = await get_quick_cashouts(uid)
    force = qc >= 6
    role = await get_role_chance(uid)
    context.user_data["tower"] = {
        "bet": bet, "level": 0, "force": force, "role": role
    }
    await show_tower(update, context)
    return ConversationHandler.END

async def show_tower(update, context, edit=False):
    t = context.user_data.get("tower")
    if not t:
        return
    level = t["level"]
    mult = TOWER_MULT[level] if level < 5 else TOWER_MULT[-1]
    win = t["bet"] * mult
    buttons = [[InlineKeyboardButton(f"⬜ {i+1}", callback_data=f"tower_pick:{i}")] for i in range(5)]
    buttons.append([InlineKeyboardButton("✅ Забрать выигрыш", callback_data="tower_cashout")])
    buttons.append([InlineKeyboardButton("⬅️ Выход", callback_data="play")])
    text = (
        f"🗼 <b>Башня</b> — уровень {level+1}/5\n"
        f"Ставка: {format_money(t['bet'])}\n"
        f"Множитель: <b>x{mult:.2f}</b>\n"
        f"Выигрыш: <b>{format_money(win)}</b>\n\n"
        f"Выберите клетку:"
    )
    kb = InlineKeyboardMarkup(buttons)
    if edit and update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def tower_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    t = context.user_data.get("tower")
    if not t:
        return
    level = t["level"]
    total_mines = tower_mines_on_level(level)
    # 5 cells, total_mines mines
    safe = 5 - total_mines
    # decide hit
    if t.get("force") and level == 0:
        hit = True
    elif t.get("role") is not None:
        hit = not roll(t["role"])
    else:
        hit = random.random() < (total_mines / 5)

    if hit:
        await log_game(q.from_user.id, "tower", t["bet"], "lose", -t["bet"])
        ref = await get_referrer(q.from_user.id)
        if ref and await is_partner(ref):
            await add_referral_earn(ref, q.from_user.id, t["bet"] * 0.20, "loss")
        context.user_data.pop("tower", None)
        await q.message.edit_text("💥 Мина! Вы проиграли.", reply_markup=play_menu())
        return

    t["level"] += 1
    if t["level"] >= 5:
        mult = TOWER_MULT[4]
        win = t["bet"] * mult
        await add_balance(q.from_user.id, win)
        await log_game(q.from_user.id, "tower", t["bet"], "win", win - t["bet"])
        await reset_quick_cashout(q.from_user.id)
        context.user_data.pop("tower", None)
        await q.message.edit_text(f"🏆 Прошли все уровни! Выигрыш {format_money(win)}", reply_markup=play_menu())
        return
    await show_tower(update, context, edit=True)

async def tower_cashout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    t = context.user_data.get("tower")
    if not t or t["level"] == 0:
        await q.answer("Сначала пройдите 1 уровень", show_alert=True)
        return
    mult = TOWER_MULT[t["level"] - 1]
    win = t["bet"] * mult
    await add_balance(q.from_user.id, win)
    await log_game(q.from_user.id, "tower", t["bet"], "win", win - t["bet"])
    if t["level"] == 1:
        await inc_quick_cashout(q.from_user.id)
    else:
        await reset_quick_cashout(q.from_user.id)
    context.user_data.pop("tower", None)
    await q.message.edit_text(f"✅ Забрано {format_money(win)} (x{mult:.2f})", reply_markup=play_menu())

# ========== PYRAMID ==========
async def pyramid_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["waiting_bet"] = "pyramid"
    await q.message.edit_text(
        f"🔺 <b>Пирамида</b>\n\nВведите ставку (мин. {MIN_BET}$):",
        reply_markup=back_kb(), parse_mode="HTML"
    )
    return WAITING_BET

async def start_pyramid_game(update, context, bet):
    uid = update.effective_user.id
    await subtract_balance(uid, bet)
    context.user_data["pyramid"] = {"bet": bet, "level": 0}
    await show_pyramid(update, context)
    return ConversationHandler.END

async def show_pyramid(update, context, edit=False):
    p = context.user_data.get("pyramid")
    if not p:
        return
    level = p["level"]
    n = PYRAMID_BUTTONS[level]
    mult = PYRAMID_MULT[level]
    win = p["bet"] * mult
    row = [InlineKeyboardButton("⬜", callback_data=f"pyramid_pick:{i}") for i in range(n)]
    buttons = [row]
    if level > 0:
        buttons.append([InlineKeyboardButton("✅ Забрать выигрыш", callback_data="pyramid_cashout")])
    buttons.append([InlineKeyboardButton("⬅️ Выход", callback_data="play")])
    text = (
        f"🔺 <b>Пирамида</b> — уровень {level+1}/5\n"
        f"Кнопок: {n}\n"
        f"Множитель: <b>x{mult:.2f}</b>\n"
        f"Выигрыш: <b>{format_money(win)}</b>"
    )
    kb = InlineKeyboardMarkup(buttons)
    if edit and update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def pyramid_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    p = context.user_data.get("pyramid")
    if not p:
        return
    level = p["level"]
    total = pyramid_total_mines(level)
    n = PYRAMID_BUTTONS[level]
    role = await get_role_chance(q.from_user.id)
    if role is not None:
        hit = not roll(role)
    else:
        hit = random.random() < (total / n)

    if hit:
        await log_game(q.from_user.id, "pyramid", p["bet"], "lose", -p["bet"])
        ref = await get_referrer(q.from_user.id)
        if ref and await is_partner(ref):
            await add_referral_earn(ref, q.from_user.id, p["bet"] * 0.20, "loss")
        context.user_data.pop("pyramid", None)
        await q.message.edit_text("💥 Мина! Проигрыш.", reply_markup=play_menu())
        return

    p["level"] += 1
    if p["level"] >= 5:
        mult = PYRAMID_MULT[4]
        win = p["bet"] * mult
        await add_balance(q.from_user.id, win)
        await log_game(q.from_user.id, "pyramid", p["bet"], "win", win - p["bet"])
        context.user_data.pop("pyramid", None)
        await q.message.edit_text(f"🏆 Вершина! {format_money(win)}", reply_markup=play_menu())
        return
    await show_pyramid(update, context, edit=True)

async def pyramid_cashout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    p = context.user_data.get("pyramid")
    if not p or p["level"] == 0:
        await q.answer("Сначала пройдите уровень", show_alert=True)
        return
    mult = PYRAMID_MULT[p["level"] - 1]
    win = p["bet"] * mult
    await add_balance(q.from_user.id, win)
    await log_game(q.from_user.id, "pyramid", p["bet"], "win", win - p["bet"])
    context.user_data.pop("pyramid", None)
    await q.message.edit_text(f"✅ Забрано {format_money(win)}", reply_markup=play_menu())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Отменено", reply_markup=main_menu(is_owner(update.effective_user.id)))
    return ConversationHandler.END
