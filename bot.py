from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)
from config import BOT_TOKEN
from database import init_db
from handlers import *
import asyncio

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set")
    asyncio.get_event_loop().run_until_complete(init_db())

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(deposit_start, pattern=r"^deposit$"),
            CallbackQueryHandler(withdraw_start, pattern=r"^withdraw$"),
            CallbackQueryHandler(mines_count, pattern=r"^mines_count:\d+$"),
            CallbackQueryHandler(tower_start, pattern=r"^game_tower$"),
            CallbackQueryHandler(pyramid_start, pattern=r"^game_pyramid$"),
        ],
        states={
            WAITING_DEPOSIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_amount)],
            WAITING_WITHDRAW: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
            WAITING_BET: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_bet)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(back_main, pattern=r"^back_main$"),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("addpartner", addpartner_cmd))
    app.add_handler(CommandHandler("give", give_cmd))

    app.add_handler(CallbackQueryHandler(back_main, pattern=r"^back_main$"))
    app.add_handler(CallbackQueryHandler(profile, pattern=r"^profile$"))
    app.add_handler(CallbackQueryHandler(balance_h, pattern=r"^balance$"))
    app.add_handler(CallbackQueryHandler(play_h, pattern=r"^play$"))
    app.add_handler(CallbackQueryHandler(rating_h, pattern=r"^rating$"))
    app.add_handler(CallbackQueryHandler(rating_show, pattern=r"^rating_(day|month|all)$"))
    app.add_handler(CallbackQueryHandler(referral_h, pattern=r"^referral$"))
    app.add_handler(CallbackQueryHandler(owner_menu_h, pattern=r"^owner_menu$"))
    app.add_handler(CallbackQueryHandler(owner_partners, pattern=r"^owner_partners$"))
    app.add_handler(CallbackQueryHandler(owner_commands, pattern=r"^owner_commands$"))
    app.add_handler(CallbackQueryHandler(mines_start, pattern=r"^game_mines$"))
    app.add_handler(CallbackQueryHandler(mines_open, pattern=r"^mines_open:"))
    app.add_handler(CallbackQueryHandler(mines_cashout, pattern=r"^mines_cashout$"))
    app.add_handler(CallbackQueryHandler(tower_pick, pattern=r"^tower_pick:"))
    app.add_handler(CallbackQueryHandler(tower_cashout, pattern=r"^tower_cashout$"))
    app.add_handler(CallbackQueryHandler(pyramid_pick, pattern=r"^pyramid_pick:"))
    app.add_handler(CallbackQueryHandler(pyramid_cashout, pattern=r"^pyramid_cashout$"))

    print("Casino bot started")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
