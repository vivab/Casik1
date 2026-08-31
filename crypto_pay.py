import aiohttp
from config import CRYPTO_PAY_TOKEN, CRYPTO_ASSET
API = "https://pay.crypt.bot/api"

async def create_invoice(amount: float, user_id: int, desc="Deposit"):
    if not CRYPTO_PAY_TOKEN:
        return None
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    payload = {
        "asset": CRYPTO_ASSET,
        "amount": str(round(amount, 2)),
        "description": desc,
        "payload": str(user_id),
        "expires_in": 3600,
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{API}/createInvoice", json=payload, headers=headers) as r:
            data = await r.json()
            return data.get("result") if data.get("ok") else None
