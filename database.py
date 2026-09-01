import aiosqlite
from datetime import datetime, timedelta
from config import DB_NAME

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0,
                freebet REAL DEFAULT 0,
                freebet_wagered REAL DEFAULT 0,
                temp_balance REAL DEFAULT 0,
                temp_balance_expires TEXT,
                referrer_id INTEGER,
                is_partner INTEGER DEFAULT 0,
                total_deposited REAL DEFAULT 0,
                total_withdrawn REAL DEFAULT 0,
                total_wagered REAL DEFAULT 0,
                total_won REAL DEFAULT 0,
                referral_earned REAL DEFAULT 0,
                quick_cashouts INTEGER DEFAULT 0,
                is_new INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS partners (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, type TEXT, amount REAL,
                status TEXT DEFAULT 'pending', external_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, game_type TEXT, bet REAL,
                result TEXT, profit REAL, details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER, referred_id INTEGER,
                amount REAL, type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Миграции: добавляем недостающие колонки
        cols = [
            ("freebet", "REAL DEFAULT 0"),
            ("freebet_wagered", "REAL DEFAULT 0"),
            ("temp_balance", "REAL DEFAULT 0"),
            ("temp_balance_expires", "TEXT"),
            ("referrer_id", "INTEGER"),
            ("is_partner", "INTEGER DEFAULT 0"),
            ("total_deposited", "REAL DEFAULT 0"),
            ("total_withdrawn", "REAL DEFAULT 0"),
            ("total_wagered", "REAL DEFAULT 0"),
            ("total_won", "REAL DEFAULT 0"),
            ("referral_earned", "REAL DEFAULT 0"),
            ("quick_cashouts", "INTEGER DEFAULT 0"),
            ("is_new", "INTEGER DEFAULT 1"),
            ("username", "TEXT"),
            ("balance", "REAL DEFAULT 0"),
        ]
        for name, typedef in cols:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {name} {typedef}")
            except Exception:
                pass  # колонка уже есть
        await db.commit()

async def ensure_user(user_id: int, username: str = "", freebet: float = 0):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if not row:
            await db.execute(
                "INSERT INTO users (user_id, username, freebet, is_new) VALUES (?,?,?,1)",
                (user_id, username, freebet)
            )
            await db.commit()
            return True
        if username:
            await db.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
            await db.commit()
        return False

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            r = await cur.fetchone()
            return dict(r) if r else None

async def get_balance(user_id: int) -> float:
    u = await get_user(user_id)
    if not u: return 0.0
    temp = 0.0
    if u.get("temp_balance") and u.get("temp_balance_expires"):
        try:
            if datetime.fromisoformat(u["temp_balance_expires"]) > datetime.utcnow():
                temp = u["temp_balance"] or 0
        except: pass
    return (u.get("balance") or 0) + (u.get("freebet") or 0) + temp

async def get_real_balance(user_id: int) -> float:
    u = await get_user(user_id)
    return (u.get("balance") or 0) if u else 0.0

async def get_withdrawable(user_id: int) -> float:
    u = await get_user(user_id)
    if not u: return 0.0
    real = u.get("balance") or 0
    fb = u.get("freebet") or 0
    wagered = u.get("freebet_wagered") or 0
    from config import FREEBET_AMOUNT, FREEBET_MULTIPLIER_NEEDED
    if fb > 0 and wagered >= FREEBET_AMOUNT * FREEBET_MULTIPLIER_NEEDED:
        real += fb
    return real

async def add_balance(user_id: int, amount: float, is_temp=False, hours=1):
    async with aiosqlite.connect(DB_NAME) as db:
        if is_temp:
            exp = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
            await db.execute(
                "UPDATE users SET temp_balance=COALESCE(temp_balance,0)+?, temp_balance_expires=? WHERE user_id=?",
                (amount, exp, user_id))
        else:
            await db.execute("UPDATE users SET balance=COALESCE(balance,0)+? WHERE user_id=?", (amount, user_id))
        await db.commit()

async def subtract_balance(user_id: int, amount: float) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT balance, freebet, temp_balance, temp_balance_expires FROM users WHERE user_id=?",
            (user_id,)) as cur:
            row = await cur.fetchone()
        if not row: return False
        real = row["balance"] or 0
        fb = row["freebet"] or 0
        temp = 0.0
        if row["temp_balance"] and row["temp_balance_expires"]:
            try:
                if datetime.fromisoformat(row["temp_balance_expires"]) > datetime.utcnow():
                    temp = row["temp_balance"]
            except: pass
        if real + fb + temp < amount: return False
        remaining = amount
        if temp > 0 and remaining > 0:
            t = min(temp, remaining)
            await db.execute("UPDATE users SET temp_balance=temp_balance-? WHERE user_id=?", (t, user_id))
            remaining -= t
        if fb > 0 and remaining > 0:
            t = min(fb, remaining)
            await db.execute(
                "UPDATE users SET freebet=freebet-?, freebet_wagered=COALESCE(freebet_wagered,0)+? WHERE user_id=?",
                (t, t, user_id))
            remaining -= t
        if remaining > 0:
            await db.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (remaining, user_id))
        await db.execute("UPDATE users SET total_wagered=COALESCE(total_wagered,0)+? WHERE user_id=?", (amount, user_id))
        await db.commit()
        return True

async def clear_balance(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET balance=0, freebet=0, temp_balance=0, temp_balance_expires=NULL WHERE user_id=?",
            (user_id,))
        await db.commit()

async def set_partner(user_id: int, added_by: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO partners(user_id, added_by) VALUES(?,?)", (user_id, added_by))
        await db.execute("UPDATE users SET is_partner=1 WHERE user_id=?", (user_id,))
        await db.commit()

async def del_partner(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM partners WHERE user_id=?", (user_id,))
        await db.execute("UPDATE users SET is_partner=0 WHERE user_id=?", (user_id,))
        await db.commit()

async def is_partner(user_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT 1 FROM partners WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None

async def list_partners():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM partners") as cur:
            return [dict(r) for r in await cur.fetchall()]

async def set_referrer(user_id: int, ref: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET referrer_id=? WHERE user_id=? AND (referrer_id IS NULL OR referrer_id=0)",
            (ref, user_id))
        await db.commit()

async def get_referrer(user_id: int):
    u = await get_user(user_id)
    return u.get("referrer_id") if u else None

async def count_referrals(user_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id=?", (user_id,)) as cur:
            r = await cur.fetchone()
            return r[0] if r else 0

async def add_referral_earn(referrer_id, referred_id, amount, type_):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO referrals(referrer_id, referred_id, amount, type) VALUES(?,?,?,?)",
            (referrer_id, referred_id, amount, type_))
        await db.execute(
            "UPDATE users SET balance=COALESCE(balance,0)+?, referral_earned=COALESCE(referral_earned,0)+? WHERE user_id=?",
            (amount, amount, referrer_id))
        await db.commit()

async def log_game(user_id, game_type, bet, result, profit, details=""):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO games(user_id, game_type, bet, result, profit, details) VALUES(?,?,?,?,?,?)",
            (user_id, game_type, bet, result, profit, details))
        if profit > 0:
            await db.execute("UPDATE users SET total_won=COALESCE(total_won,0)+? WHERE user_id=?", (profit, user_id))
        await db.commit()

async def create_transaction(user_id, type_, amount, external_id="", status="pending"):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "INSERT INTO transactions(user_id, type, amount, status, external_id) VALUES(?,?,?,?,?)",
            (user_id, type_, amount, status, external_id))
        await db.commit()
        return cur.lastrowid

async def inc_quick(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET quick_cashouts=COALESCE(quick_cashouts,0)+1 WHERE user_id=?", (user_id,))
        await db.commit()

async def reset_quick(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET quick_cashouts=0 WHERE user_id=?", (user_id,))
        await db.commit()

async def get_quick(user_id) -> int:
    u = await get_user(user_id)
    return (u.get("quick_cashouts") or 0) if u else 0

async def get_top(limit=3, exclude_id: int = 0):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, total_won FROM users WHERE COALESCE(total_won,0) > 0 AND user_id != ? ORDER BY total_won DESC LIMIT ?",
            (exclude_id, limit)) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def mark_invoice_done(invoice_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE transactions SET status='paid' WHERE external_id=? AND status='pending'",
            (str(invoice_id),))
        await db.commit()

async def find_pending_deposit(invoice_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM transactions WHERE external_id=? AND type='deposit' AND status='pending'",
            (str(invoice_id),)) as cur:
            r = await cur.fetchone()
            return dict(r) if r else None
