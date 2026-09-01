from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import *
from keyboards import *
from utils import *
from config import *
from crypto_pay import create_invoice
from games import *
import random

W_DEP, W_WD, W_BET, W_MINES_CNT = range(4)

def win_text(amount: float) -> str:
    return (
        f"🔥💰 <b>ПОБЕДА!</b> 💰🔥\n\n"
        f"🎉 Поздравляю!\n"
        f"Вы выиграли <b>{money(amount)}</b>\n\n"
        f"✨ Так держать! ✨"
    )

def lose_text() -> str:
    return "💔 <b>Проигрыш</b>\n\nНе расстраивайтесь, попробуйте снова! 🍀"


WELCOME = (
    "Привет, ты попал в <b>JackZo</b> — лучшее мини-казино в Telegram!\n\n"
    "Большие шансы на выигрыш!\n"
    "Фрибет всем новым пользователям <b>5$</b>\n\n"
    "Испытай удачу и заработай денег с нами!"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    is_new = await ensure_user(u.id, u.username or "", freebet=FREEBET_AMOUNT)

    if context.args and context.args[0].startswith("ref_"):
        try:
            rid = int(context.args[0][4:])
            if rid != u.id:
                await set_referrer(u.id, rid)
        except Exception:
            pass

    try:
        from payments import process_paid_invoices
        await process_paid_invoices(context.bot)
    except Exception:
        pass
    text = WELCOME
    if is_new:
        text += f"\n\n🎁 Тебе начислен фрибет <b>{money(FREEBET_AMOUNT)}</b>!"
    await update.message.reply_text(text, reply_markup=main_menu(is_owner(u.id)), parse_mode="HTML")

async def back_main_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.message.edit_text("🎰 JackZo — главное меню", reply_markup=main_menu(is_owner(q.from_user.id)))

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = await get_user(q.from_user.id)
    bal = await get_balance(q.from_user.id)
    refs = await count_referrals(q.from_user.id)
    earned = u.get("referral_earned") or 0
    fb = u.get("freebet") or 0
    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"Ник: @{u.get('username') or '—'}\n"
        f"ID: <code>{u['user_id']}</code>\n"
        f"Баланс: <b>{money(bal)}</b>\n"
    )
    if fb > 0:
        text += f"Фрибет: {money(fb)}\n"
    text += f"\n👥 Рефералов: <b>{refs}</b>\n💰 С рефералов: <b>{money(earned)}</b>"
    await q.message.edit_text(text, reply_markup=back_main(), parse_mode="HTML")

async def balance_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    bal = await get_balance(q.from_user.id)
    real = await get_real_balance(q.from_user.id)
    wd = await get_withdrawable(q.from_user.id)
    u = await get_user(q.from_user.id)
    fb = u.get("freebet") or 0
    text = (
        f"💰 <b>Баланс</b>\n\n"
        f"Доступно: <b>{money(bal)}</b>\n"
        f"Реальный: {money(real)}\n"
        f"К выводу: {money(wd)}\n"
    )
    if fb > 0:
        text += f"\n🎁 Фрибет: {money(fb)}\n(вывести можно после оборота x10)"
    await q.message.edit_text(text, reply_markup=balance_menu(), parse_mode="HTML")

# --- deposit / withdraw ---
async def dep_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text(f"Сумма пополнения (мин. {MIN_DEPOSIT}$):", reply_markup=back_main())
    return W_DEP

async def dep_amt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(",", ".").replace("$", ""))
    except:
        await update.message.reply_text("Число, например 1.5")
        return W_DEP
    if amount < MIN_DEPOSIT:
        await update.message.reply_text(f"Мин. {MIN_DEPOSIT}$")
        return W_DEP
    inv = await create_invoice(amount, update.effective_user.id)
    if not inv:
        await add_balance(update.effective_user.id, amount)
        # referral 5% on deposit for normal referrer
        ref = await get_referrer(update.effective_user.id)
        if ref and not await is_partner(ref):
            await add_referral_earn(ref, update.effective_user.id, amount * 0.05, "deposit")
        await update.message.reply_text(f"✅ Зачислено {money(amount)} (тест-режим без CRYPTO_PAY_TOKEN)")
        return ConversationHandler.END
    await create_transaction(update.effective_user.id, "deposit", amount, str(inv.get("invoice_id", "")))
    url = inv.get("pay_url") or inv.get("bot_invoice_url") or ""
    await update.message.reply_text(f"💳 Счёт {money(amount)}\n\n{url}", parse_mode="HTML")
    return ConversationHandler.END

async def wd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    wd = await get_withdrawable(q.from_user.id)
    if wd < MIN_WITHDRAW:
        await q.answer(f"К выводу меньше {MIN_WITHDRAW}$", show_alert=True)
        return ConversationHandler.END
    await q.message.edit_text(f"К выводу: {money(wd)}\nВведите сумму:", reply_markup=back_main())
    return W_WD

async def wd_amt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(",", ".").replace("$", ""))
    except:
        await update.message.reply_text("Число")
        return W_WD
    if amount < MIN_WITHDRAW:
        await update.message.reply_text(f"Мин. {MIN_WITHDRAW}$")
        return W_WD
    wd = await get_withdrawable(update.effective_user.id)
    if amount > wd:
        await update.message.reply_text("Недостаточно к выводу")
        return W_WD
    ok = await subtract_balance(update.effective_user.id, amount)
    if not ok:
        await update.message.reply_text("❌ Ошибка списания")
        return ConversationHandler.END
    from payments import auto_withdraw
    success, err = await auto_withdraw(update.effective_user.id, amount)
    if success:
        await update.message.reply_text(
            f"✅ <b>Вывод {money(amount)} отправлен!</b>\nПроверьте @CryptoBot",
            parse_mode="HTML"
        )
    else:
        tid = await create_transaction(update.effective_user.id, "withdraw", amount, status="pending")
        try:
            await context.bot.send_message(
                OWNER_ID,
                f"💸 Ручной вывод #{tid}\nUser: {update.effective_user.id}\n{money(amount)}\nОшибка API: {err}"
            )
        except Exception:
            pass
        await update.message.reply_text(
            f"⏳ Заявка на {money(amount)} принята.\nЕсли авто-вывод не прошёл — владелец обработает вручную."
        )
    return ConversationHandler.END

# --- rating / referral ---
async def rating_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    top = await get_top(3, exclude_id=OWNER_ID)
    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 <b>Топ игроков</b>\n\n"
    if not top:
        text += "Пока пусто"
    else:
        for i, r in enumerate(top):
            text += f"{medals[i]} {anon(r['user_id'])} — {money(r['total_won'])}\n"
    await q.message.edit_text(text, reply_markup=back_main(), parse_mode="HTML")

async def referral_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    me = await context.bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{q.from_user.id}"
    partner = await is_partner(q.from_user.id)
    desc = "20% с проигрышей приглашённых" if partner else "5% с пополнений приглашённых"
    refs = await count_referrals(q.from_user.id)
    u = await get_user(q.from_user.id)
    earned = u.get("referral_earned") or 0
    text = (
        f"👥 <b>Рефералка</b>\n\n{desc}\n\n"
        f"Рефералов: <b>{refs}</b>\nЗаработано: <b>{money(earned)}</b>\n\n"
        f"Ссылка:\n<code>{link}</code>"
    )
    await q.message.edit_text(text, reply_markup=back_main(), parse_mode="HTML")

# --- owner ---
async def owner_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_owner(q.from_user.id): return
    await q.message.edit_text("👑 Владелец", reply_markup=owner_menu())

async def owner_partners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_owner(q.from_user.id): return
    ps = await list_partners()
    text = "👥 Партнёры:\n\n" + ("\n".join(f"• <code>{p['user_id']}</code>" for p in ps) or "Пусто")
    text += "\n\n/addpartner ID\n/delpartner ID"
    await q.message.edit_text(text, reply_markup=owner_menu(), parse_mode="HTML")

async def owner_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = (
        "📋 Команды:\n\n"
        "/addpartner ID\n/delpartner ID\n"
        "/give ID сумма — временный баланс\n"
        "/delbalance ID — обнулить баланс"
    )
    await q.message.edit_text(text, reply_markup=owner_menu())

async def cmd_addpartner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("/addpartner ID"); return
    pid = int(context.args[0])
    await ensure_user(pid)
    await set_partner(pid, update.effective_user.id)
    await update.message.reply_text(f"✅ Партнёр {pid}")

async def cmd_delpartner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("/delpartner ID"); return
    await del_partner(int(context.args[0]))
    await update.message.reply_text("✅ Удалён")

async def cmd_give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    if len(context.args) < 2:
        await update.message.reply_text("/give ID сумма"); return
    uid, amt = int(context.args[0]), float(context.args[1])
    await ensure_user(uid)
    await add_balance(uid, amt, is_temp=True, hours=1)
    await update.message.reply_text(f"✅ {money(amt)} временно → {uid}")

async def cmd_delbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("/delbalance ID"); return
    await clear_balance(int(context.args[0]))
    await update.message.reply_text("✅ Баланс обнулён")

# --- play menus ---
async def play_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text("🔥 Выберите раздел:", reply_markup=play_menu())

async def mini_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text("🎮 Мини-игры:", reply_markup=mini_games_menu())

async def author_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text("🎨 Авторские игры:", reply_markup=author_games_menu())

# --- AUTHOR GAMES ---
async def author_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    key = q.data.split(":")[1]
    context.user_data["author_key"] = key
    mult, vis, _ = AUTHOR_GAMES[key]
    await q.message.edit_text(
        f"Игра <b>x{mult}</b> (шанс {vis}%)\nВведите ставку (мин. {MIN_BET}$):",
        reply_markup=back_play(), parse_mode="HTML"
    )
    context.user_data["waiting"] = "author"
    return W_BET

async def process_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bet = float(update.message.text.replace(",", ".").replace("$", ""))
    except:
        await update.message.reply_text("Число"); return W_BET
    if bet < MIN_BET:
        await update.message.reply_text(f"Мин. {MIN_BET}$"); return W_BET
    if await get_balance(update.effective_user.id) < bet:
        await update.message.reply_text(
            "❌ Недостаточно средств, пополните баланс!",
            reply_markup=need_money_kb()
        )
        return ConversationHandler.END

    w = context.user_data.get("waiting")
    if w == "setbet":
        key = context.user_data.get("setbet_for", "mines")
        context.user_data.setdefault("bets", {})[key] = bet
        await update.message.reply_text(
            f"✅ Ставка сохранена: <b>{money(bet)}</b>",
            reply_markup=bet_saved_kb(key, bet),
            parse_mode="HTML"
        )
        return ConversationHandler.END
    # remember bet for game type
    if w:
        save_key = w if w != "author" else f"author:{context.user_data.get('author_key','x2')}"
        context.user_data.setdefault("bets", {})[save_key] = bet
    if w == "author":
        return await run_author(update, context, bet)
    if w == "mines":
        return await run_mines(update, context, bet)
    if w == "tower":
        return await run_tower(update, context, bet)
    if w == "pyramid":
        return await run_pyramid(update, context, bet)
    return ConversationHandler.END

async def run_author(update, context, bet):
    uid = update.effective_user.id
    key = context.user_data.get("author_key", "x2")
    mult, vis, real_ch = AUTHOR_GAMES[key]
    await subtract_balance(uid, bet)

    rc = await role_chance(uid)
    if rc is not None:
        win = roll(rc)
    else:
        win = roll(real_ch)

    if win:
        prize = bet * mult
        await add_balance(uid, prize)
        await log_game(uid, f"author_{key}", bet, "win", prize - bet)
        await update.message.reply_text(
            win_text(prize),
            reply_markup=after_game_kb(f"author:{key}"),
            parse_mode="HTML"
        )
    else:
        await log_game(uid, f"author_{key}", bet, "lose", -bet)
        ref = await get_referrer(uid)
        if ref and await is_partner(ref):
            await add_referral_earn(ref, uid, bet * 0.20, "loss")
        await update.message.reply_text(
            lose_text(),
            reply_markup=after_game_kb(f"author:{key}"),
            parse_mode="HTML"
        )
    return ConversationHandler.END

# --- MINES ---
async def mines_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text(
        f"💣 <b>Мины</b>\n\nНапишите количество мин (1–24):",
        reply_markup=back_play(), parse_mode="HTML"
    )
    context.user_data["waiting"] = "mines_cnt"
    return W_MINES_CNT

async def mines_cnt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cnt = int(update.message.text.strip())
    except:
        await update.message.reply_text("Число от 1 до 24"); return W_MINES_CNT
    if not 1 <= cnt <= 24:
        await update.message.reply_text("От 1 до 24"); return W_MINES_CNT
    context.user_data["mines_cnt"] = cnt
    context.user_data["waiting"] = "mines"
    await update.message.reply_text(f"Мин: {cnt}. Введите ставку (мин. {MIN_BET}$):")
    return W_BET

async def run_mines(update, context, bet):
    uid = update.effective_user.id
    await subtract_balance(uid, bet)
    chosen = context.user_data.get("mines_cnt", 3)
    real_n = secret_mines(chosen)
    field = gen_field(real_n)
    # visible mines subset for display on lose
    visible = set(random.sample(list(field), min(chosen, len(field))))

    qc = await get_quick(uid)
    force = qc >= 10
    rc = await role_chance(uid)

    context.user_data["mines"] = {
        "bet": bet, "chosen": chosen, "field": field, "visible": visible,
        "opened": [], "force": force, "rc": rc
    }
    await show_mines(update, context)
    return ConversationHandler.END

async def show_mines(update, context, edit=False):
    m = context.user_data.get("mines")
    if not m: return
    rows = []
    for i in range(5):
        row = []
        for j in range(5):
            idx = i*5+j
            if idx in m["opened"]:
                row.append(InlineKeyboardButton("📦", callback_data="noop"))
            else:
                row.append(InlineKeyboardButton("📦", callback_data=f"mopen:{idx}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("✅ Забрать выигрыш", callback_data="mcash")])
    rows.append([InlineKeyboardButton("⬅️ Выход", callback_data="mini_games")])
    mult = mines_mult(m["chosen"], len(m["opened"]))
    win = m["bet"] * mult
    text = (
        f"💣 Мины ({m['chosen']})\n"
        f"Ставка: {money(m['bet'])} | Открыто: {len(m['opened'])}\n"
        f"Икс: <b>x{mult}</b> | Выигрыш: <b>{money(win)}</b>"
    )
    kb = InlineKeyboardMarkup(rows)
    if edit and update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def mopen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    m = context.user_data.get("mines")
    if not m: return
    idx = int(q.data.split(":")[1])
    if idx in m["opened"]: return

    hit = idx in m["field"]
    if m.get("force"):
        hit = True
    elif m.get("rc") is not None:
        # role override: sometimes force result
        pass

    if hit:
        # show only visible mines, ensure the hit cell is among them
        show = set(m["visible"])
        show.add(idx)
        # build field display
        rows = []
        for i in range(5):
            row = []
            for j in range(5):
                cell = i*5+j
                if cell == idx:
                    row.append(InlineKeyboardButton("💥", callback_data="noop"))
                elif cell in show:
                    row.append(InlineKeyboardButton("💣", callback_data="noop"))
                elif cell in m["opened"]:
                    row.append(InlineKeyboardButton("📦", callback_data="noop"))
                else:
                    row.append(InlineKeyboardButton("📦", callback_data="noop"))
            rows.append(row)
        await log_game(q.from_user.id, "mines", m["bet"], "lose", -m["bet"])
        ref = await get_referrer(q.from_user.id)
        if ref and await is_partner(ref):
            await add_referral_earn(ref, q.from_user.id, m["bet"]*0.20, "loss")
        context.user_data.pop("mines", None)
        await q.message.edit_text(
            f"💥 Взрыв! Ставка {money(m['bet'])} потеряна.",
            reply_markup=InlineKeyboardMarkup(rows + [[InlineKeyboardButton("⬅️ Назад", callback_data="mini_games")]])
        )
        return

    m["opened"].append(idx)
    await show_mines(update, context, edit=True)

async def mcash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    m = context.user_data.get("mines")
    if not m or not m["opened"]:
        await q.answer("Нечего забирать", show_alert=True); return
    mult = mines_mult(m["chosen"], len(m["opened"]))
    win = m["bet"] * mult
    await add_balance(q.from_user.id, win)
    await log_game(q.from_user.id, "mines", m["bet"], "win", win - m["bet"])
    if len(m["opened"]) <= 2:
        await inc_quick(q.from_user.id)
    else:
        await reset_quick(q.from_user.id)
    context.user_data.pop("mines", None)
    await q.message.edit_text(
        win_text(win),
        reply_markup=after_game_kb("mines"),
        parse_mode="HTML"
    )

# --- TOWER (horizontal row of 5) ---
async def tower_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["waiting"] = "tower"
    await q.message.edit_text(f"🗼 Башня\nСтавка (мин. {MIN_BET}$):", reply_markup=back_play())
    return W_BET

async def run_tower(update, context, bet):
    uid = update.effective_user.id
    await subtract_balance(uid, bet)
    context.user_data["tower"] = {
        "bet": bet, "level": 0,
        "force": (await get_quick(uid)) >= 6,
        "rc": await role_chance(uid)
    }
    await show_tower(update, context)
    return ConversationHandler.END

async def show_tower(update, context, edit=False):
    t = context.user_data.get("tower")
    if not t: return
    lv = t["level"]
    mult = TOWER_MULT[lv]
    win = t["bet"] * mult
    row = [InlineKeyboardButton("📦", callback_data=f"tpick:{i}") for i in range(5)]
    rows = [row]
    if lv > 0:
        rows.append([InlineKeyboardButton(f"✅ Забрать {money(win)}", callback_data="tcash")])
    rows.append([InlineKeyboardButton("⬅️ Выход", callback_data="mini_games")])
    text = (
        f"🗼 Башня — ур. {lv+1}/5\n"
        f"Ставка: {money(t['bet'])} | x{mult:.2f} → <b>{money(win)}</b>\n"
        f"Выберите клетку:"
    )
    kb = InlineKeyboardMarkup(rows)
    if edit and update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def tpick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    t = context.user_data.get("tower")
    if not t: return
    lv = t["level"]
    n_mines = tower_mines(lv)
    if t.get("force") and lv == 0:
        hit = True
    elif t.get("rc") is not None:
        hit = not roll(t["rc"])
    else:
        hit = random.random() < (n_mines / 5)

    if hit:
        await log_game(q.from_user.id, "tower", t["bet"], "lose", -t["bet"])
        ref = await get_referrer(q.from_user.id)
        if ref and await is_partner(ref):
            await add_referral_earn(ref, q.from_user.id, t["bet"]*0.20, "loss")
        context.user_data.pop("tower", None)
        # показываем только 1 видимую мину
        hit_i = int(q.data.split(":")[1]) if ":" in q.data else 0
        row = []
        for i in range(5):
            if i == hit_i:
                row.append(InlineKeyboardButton("💥", callback_data="noop"))
            else:
                row.append(InlineKeyboardButton("📦", callback_data="noop"))
        # одна "настоящая" мина в другой клетке для картинки
        other = [i for i in range(5) if i != hit_i]
        if other:
            row[other[0]] = InlineKeyboardButton("💣", callback_data="noop")
        await q.message.edit_text(
            lose_text() + "\n\n💥 Вы попали на мину!",
            reply_markup=InlineKeyboardMarkup([row] + after_game_kb("pyramid").inline_keyboard),
            parse_mode="HTML"
        )
        return

    t["level"] += 1
    if t["level"] >= 5:
        mult = TOWER_MULT[4]
        win = t["bet"] * mult
        await add_balance(q.from_user.id, win)
        await log_game(q.from_user.id, "tower", t["bet"], "win", win - t["bet"])
        await reset_quick(q.from_user.id)
        context.user_data.pop("tower", None)
        await q.message.edit_text(win_text(win), reply_markup=after_game_kb("pyramid"), parse_mode="HTML")
        return
    await show_tower(update, context, edit=True)

async def tcash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    t = context.user_data.get("tower")
    if not t or t["level"] == 0:
        await q.answer("Пройдите 1 уровень", show_alert=True); return
    mult = TOWER_MULT[t["level"]-1]
    win = t["bet"] * mult
    await add_balance(q.from_user.id, win)
    await log_game(q.from_user.id, "tower", t["bet"], "win", win - t["bet"])
    if t["level"] == 1: await inc_quick(q.from_user.id)
    else: await reset_quick(q.from_user.id)
    context.user_data.pop("tower", None)
    await q.message.edit_text(win_text(win), reply_markup=after_game_kb("tower"), parse_mode="HTML")

# --- PYRAMID ---
async def pyramid_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["waiting"] = "pyramid"
    await q.message.edit_text(f"🔺 Пирамида\nСтавка (мин. {MIN_BET}$):", reply_markup=back_play())
    return W_BET

async def run_pyramid(update, context, bet):
    uid = update.effective_user.id
    await subtract_balance(uid, bet)
    context.user_data["pyramid"] = {"bet": bet, "level": 0, "rc": await role_chance(uid)}
    await show_pyramid(update, context)
    return ConversationHandler.END

async def show_pyramid(update, context, edit=False):
    p = context.user_data.get("pyramid")
    if not p: return
    lv = p["level"]
    n = PYRAMID_BTNS[lv]
    mult = PYRAMID_MULT[lv]
    win = p["bet"] * mult
    row = [InlineKeyboardButton("📦", callback_data=f"ppick:{i}") for i in range(n)]
    rows = [row]
    if lv > 0:
        rows.append([InlineKeyboardButton(f"✅ Забрать {money(win)}", callback_data="pcash")])
    rows.append([InlineKeyboardButton("⬅️ Выход", callback_data="mini_games")])
    text = (
        f"🔺 Пирамида — ур. {lv+1}/5 ({n} клеток)\n"
        f"x{mult:.2f} → <b>{money(win)}</b>"
    )
    kb = InlineKeyboardMarkup(rows)
    if edit and update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def ppick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    p = context.user_data.get("pyramid")
    if not p: return
    lv = p["level"]
    total = pyramid_mines(lv)
    n = PYRAMID_BTNS[lv]
    if p.get("rc") is not None:
        hit = not roll(p["rc"])
    else:
        hit = random.random() < (total / n)
    if hit:
        await log_game(q.from_user.id, "pyramid", p["bet"], "lose", -p["bet"])
        ref = await get_referrer(q.from_user.id)
        if ref and await is_partner(ref):
            await add_referral_earn(ref, q.from_user.id, p["bet"]*0.20, "loss")
        context.user_data.pop("pyramid", None)
        from config import PYRAMID_VIS
        vis = PYRAMID_VIS[lv]
        hit_i = int(q.data.split(":")[1]) if ":" in q.data else 0
        row = []
        bombs_left = vis - 1
        for i in range(n):
            if i == hit_i:
                row.append(InlineKeyboardButton("💥", callback_data="noop"))
            elif bombs_left > 0:
                row.append(InlineKeyboardButton("💣", callback_data="noop"))
                bombs_left -= 1
            else:
                row.append(InlineKeyboardButton("📦", callback_data="noop"))
        await q.message.edit_text(
            lose_text() + "\n\n💥 Вы попали на мину!",
            reply_markup=InlineKeyboardMarkup([row] + after_game_kb("pyramid").inline_keyboard),
            parse_mode="HTML"
        )
        return
    p["level"] += 1
    if p["level"] >= 5:
        win = p["bet"] * PYRAMID_MULT[4]
        await add_balance(q.from_user.id, win)
        await log_game(q.from_user.id, "pyramid", p["bet"], "win", win - p["bet"])
        context.user_data.pop("pyramid", None)
        await q.message.edit_text(win_text(win), reply_markup=after_game_kb("pyramid"), parse_mode="HTML")
        return
    await show_pyramid(update, context, edit=True)

async def pcash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    p = context.user_data.get("pyramid")
    if not p or p["level"] == 0:
        await q.answer("Пройдите уровень", show_alert=True); return
    mult = PYRAMID_MULT[p["level"]-1]
    win = p["bet"] * mult
    await add_balance(q.from_user.id, win)
    await log_game(q.from_user.id, "pyramid", p["bet"], "win", win - p["bet"])
    context.user_data.pop("pyramid", None)
    await q.message.edit_text(win_text(win), reply_markup=after_game_kb("pyramid"), parse_mode="HTML")


async def again_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    key = q.data.split(":", 1)[1]
    # saved bet
    bets = context.user_data.setdefault("bets", {})
    bet = bets.get(key)
    if not bet:
        await q.message.edit_text(f"Введите ставку (мин. {MIN_BET}$):", reply_markup=back_play())
        context.user_data["waiting"] = key if key in ("mines","tower","pyramid") else "author"
        if key.startswith("author"):
            context.user_data["author_key"] = key.split(":")[-1] if ":" in key else key.replace("author","x2")
            context.user_data["waiting"] = "author"
        else:
            context.user_data["waiting"] = key
        return W_BET
    # play with saved bet
    if await get_balance(q.from_user.id) < bet:
        await q.message.edit_text("❌ Недостаточно средств, пополните баланс!", reply_markup=need_money_kb())
        return
    context.user_data["waiting"] = "author" if key.startswith("author") or key.startswith("x") else key
    if key.startswith("author"):
        context.user_data["author_key"] = key.split(":")[-1]
        # simulate message with bet
        class Fake:
            pass
        # just call run directly
        from telegram import Message
        await run_author_from_cb(q, context, bet, key)
        return
    if key == "mines":
        context.user_data["mines_cnt"] = context.user_data.get("mines_cnt", 3)
        # need message-like - use callback path
        await q.message.edit_text(f"Ставка {bet}$ — начинаем...")
        # manual start
        uid = q.from_user.id
        await subtract_balance(uid, bet)
        chosen = context.user_data.get("mines_cnt", 3)
        from games import gen_field
        from utils import secret_mines
        real_n = secret_mines(chosen)
        field = gen_field(real_n)
        visible = set(list(field)[:chosen]) if field else set()
        context.user_data["mines"] = {
            "bet": bet, "chosen": chosen, "field": field, "visible": visible,
            "opened": [], "force": (await get_quick(uid)) >= 10, "rc": await role_chance(uid)
        }
        await show_mines(update, context, edit=True)
        return
    await q.message.edit_text(f"Введите ставку или используйте сохранённую.\nМин. {MIN_BET}$", reply_markup=back_play())
    context.user_data["waiting"] = key
    return W_BET

async def setbet_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    key = q.data.split(":", 1)[1]
    context.user_data["setbet_for"] = key
    await q.message.edit_text(f"✏️ Введите новую ставку (мин. {MIN_BET}$):", reply_markup=back_play())
    context.user_data["waiting"] = "setbet"
    return W_BET

async def run_author_from_cb(q, context, bet, key):
    uid = q.from_user.id
    ak = key.split(":")[-1] if ":" in key else "x2"
    context.user_data["author_key"] = ak
    mult, vis, real_ch = AUTHOR_GAMES.get(ak, AUTHOR_GAMES["x2"])
    await subtract_balance(uid, bet)
    rc = await role_chance(uid)
    win = roll(rc if rc is not None else real_ch)
    if win:
        prize = bet * mult
        await add_balance(uid, prize)
        await log_game(uid, f"author_{ak}", bet, "win", prize - bet)
        await q.message.edit_text(win_text(prize), reply_markup=after_game_kb(f"author:{ak}"), parse_mode="HTML")
    else:
        await log_game(uid, f"author_{ak}", bet, "lose", -bet)
        ref = await get_referrer(uid)
        if ref and await is_partner(ref):
            await add_referral_earn(ref, uid, bet * 0.20, "loss")
        await q.message.edit_text(lose_text(), reply_markup=after_game_kb(f"author:{ak}"), parse_mode="HTML")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Отменено", reply_markup=main_menu(is_owner(update.effective_user.id)))
    return ConversationHandler.END

async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
