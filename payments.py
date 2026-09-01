"""Авто-пополнение и авто-вывод через CryptoBot."""
from crypto_pay import get_invoices, transfer
from database import find_pending_deposit, mark_invoice_done, add_balance, get_referrer, is_partner, add_referral_earn, create_transaction, subtract_balance, get_withdrawable
from utils import money

async def process_paid_invoices(bot=None):
    """Проверяет оплаченные инвойсы и зачисляет баланс."""
    items = await get_invoices(status="paid", count=50)
    credited = []
    for inv in items:
        inv_id = str(inv.get("invoice_id") or inv.get("id") or "")
        if not inv_id:
            continue
        pending = await find_pending_deposit(inv_id)
        if not pending:
            continue
        amount = float(pending["amount"])
        user_id = pending["user_id"]
        await add_balance(user_id, amount)
        await mark_invoice_done(inv_id)
        # реферал 5% с депозита
        ref = await get_referrer(user_id)
        if ref and not await is_partner(ref):
            bonus = round(amount * 0.05, 2)
            if bonus > 0:
                await add_referral_earn(ref, user_id, bonus, "deposit")
        credited.append((user_id, amount))
        if bot:
            try:
                await bot.send_message(user_id, f"✅ Пополнение {money(amount)} зачислено на баланс!")
            except Exception:
                pass
    return credited

async def auto_withdraw(user_id: int, amount: float) -> tuple[bool, str]:
    """Пытается отправить средства через CryptoBot transfer."""
    result = await transfer(user_id, amount)
    if result and not result.get("error"):
        await create_transaction(user_id, "withdraw", amount, status="paid")
        return True, "ok"
    err = (result or {}).get("error") or result or "unknown"
    await create_transaction(user_id, "withdraw", amount, status="failed")
    return False, str(err)
