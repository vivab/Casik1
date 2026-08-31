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
                temp_balance REAL DEFAULT 0,
                temp_balance_expires TEXT,
                referrer_id INTEGER,
                is_partner INTEGER DEFAULT 0,
                total_deposited REAL DEFAULT 0,
                total_withdrawn REAL DEFAULT 0,
                total_wagered REAL DEFAULT 0,
                total_won REAL DEFAULT 0,
                quick_cashouts INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS partners (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount REAL,
                status TEXT DEFAULT 'pending',
                external_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_type TEXT,
                bet REAL,
                result TEXT,
                profit REAL,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                amount REAL,
                type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()

async def ensure_user(user_id: int, username: str = ""):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        if username:
            await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_balance(user_id: int) -> float:
    user = await get_user(user_id)
    if not user:
        return 0.0
    temp = 0.0
    if user.get("temp_balance") and user.get("temp_balance_expires"):
        try:
            if datetime.fromisoformat(user["temp_balance_expires"]) > datetime.utcnow():
                temp = user["temp_balance"]
        except Exception:
            pass
    return (user.get("balance") or 0) + temp

async def get_real_balance(user_id: int) -> float:
    user = await get_user(user_id)
    return (user.get("balance") or 0) if user else 0.0

async def add_balance(user_id: int, amount: float, is_temp: bool = False, hours: int = 1):
    async with aiosqlite.connect(DB_NAME) as db:
        if is_temp:
            expires = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
            await db.execute(
                "UPDATE users SET temp_balance = COALESCE(temp_balance,0) + ?, temp_balance_expires = ? WHERE user_id = ?",
                (amount, expires, user_id)
            )
        else:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def subtract_balance(user_id: int, amount: float) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT balance, temp_balance, temp_balance_expires FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return False
        real = row["balance"] or 0
        temp = 0.0
        if row["temp_balance"] and row["temp_balance_expires"]:
            try:
                if datetime.fromisoformat(row["temp_balance_expires"]) > datetime.utcnow():
                    temp = row["temp_balance"]
            except Exception:
                pass
        if real + temp < amount:
            return False
        remaining = amount
        if temp > 0:
            take = min(temp, remaining)
            await db.execute("UPDATE users SET temp_balance = temp_balance - ? WHERE user_id = ?", (take, user_id))
            remaining -= take
        if remaining > 0:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (remaining, user_id))
        await db.commit()
        return True

async def set_partner(user_id: int, added_by: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO partners (user_id, added_by) VALUES (?, ?)", (user_id, added_by))
        await db.execute("UPDATE users SET is_partner = 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def is_partner(user_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT 1 FROM partners WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone() is not None

async def list_partners():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM partners ORDER BY added_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]

async def set_referrer(user_id: int, referrer_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET referrer_id = ? WHERE user_id = ? AND (referrer_id IS NULL OR referrer_id = 0)",
            (referrer_id, user_id)
        )
        await db.commit()

async def get_referrer(user_id: int):
    user = await get_user(user_id)
    return user.get("referrer_id") if user else None

async def add_referral_earn(referrer_id: int, referred_id: int, amount: float, type_: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO referrals (referrer_id, referred_id, amount, type) VALUES (?,?,?,?)",
            (referrer_id, referred_id, amount, type_)
        )
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, referrer_id))
        await db.commit()

async def log_game(user_id: int, game_type: str, bet: float, result: str, profit: float, details: str = ""):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO games (user_id, game_type, bet, result, profit, details) VALUES (?,?,?,?,?,?)",
            (user_id, game_type, bet, result, profit, details)
        )
        await db.execute("UPDATE users SET total_wagered = total_wagered + ? WHERE user_id = ?", (bet, user_id))
        if profit > 0:
            await db.execute("UPDATE users SET total_won = total_won + ? WHERE user_id = ?", (profit, user_id))
        await db.commit()

async def create_transaction(user_id: int, type_: str, amount: float, external_id: str = "", status: str = "pending") -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "INSERT INTO transactions (user_id, type, amount, status, external_id) VALUES (?,?,?,?,?)",
            (user_id, type_, amount, status, external_id)
        )
        await db.commit()
        return cur.lastrowid

async def inc_quick_cashout(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET quick_cashouts = quick_cashouts + 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def reset_quick_cashout(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET quick_cashouts = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_quick_cashouts(user_id: int) -> int:
    user = await get_user(user_id)
    return user.get("quick_cashouts", 0) if user else 0

async def get_top_players(period: str = "all", limit: int = 3):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT user_id, total_won FROM users WHERE total_won > 0 ORDER BY total_won DESC LIMIT ?"
        async with db.execute(q, (limit,)) as cur:
            return [dict(r) for r in await cur.fetchall()]
