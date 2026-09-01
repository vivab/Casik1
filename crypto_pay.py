import aiohttp
import uuid
from config import CRYPTO_PAY_TOKEN, CRYPTO_ASSET

API = "https://pay.crypt.bot/api"

def _headers():
    return {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}

async def create_invoice(amount: float, user_id: int, desc: str = "Deposit"):
    if not CRYPTO_PAY_TOKEN:
        return None
    payload = {
        "asset": CRYPTO_ASSET,
        "amount": str(round(amount, 2)),
        "description": desc,
        "payload": str(user_id),
        "expires_in": 3600,
        "allow_comments": False,
        "allow_anonymous": False,
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{API}/createInvoice", json=payload, headers=_headers()) as r:
            data = await r.json()
            return data.get("result") if data.get("ok") else None

async def get_invoices(status: str = "paid", count: int = 100):
    if not CRYPTO_PAY_TOKEN:
        return []
    params = {"status": status, "count": count}
    async with aiohttp.ClientSession() as s:
        async with s.get(f"{API}/getInvoices", params=params, headers=_headers()) as r:
            data = await r.json()
            if data.get("ok"):
                return data["result"].get("items") or data["result"] or []
            return []

async def transfer(telegram_user_id: int, amount: float) -> dict | None:
    """Авто-вывод пользователю в CryptoBot."""
    if not CRYPTO_PAY_TOKEN:
        return None
    payload = {
        "user_id": telegram_user_id,
        "asset": CRYPTO_ASSET,
        "amount": str(round(amount, 2)),
        "spend_id": str(uuid.uuid4()),
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{API}/transfer", json=payload, headers=_headers()) as r:
            data = await r.json()
            if data.get("ok"):
                return data["result"]
            return {"error": data.get("error", data)}
