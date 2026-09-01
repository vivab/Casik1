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
            CallbackQueryHandler(dep_start, pattern=r"^deposit$"),
            CallbackQueryHandler(wd_start, pattern=r"^withdraw$"),
            CallbackQueryHandler(mines_start, pattern=r"^game_mines$"),
            CallbackQueryHandler(tower_start, pattern=r"^game_tower$"),
            CallbackQueryHandler(pyramid_start, pattern=r"^game_pyramid$"),
            CallbackQueryHandler(author_pick, pattern=r"^author:"),
        ],
        states={
            W_DEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, dep_amt)],
            W_WD: [MessageHandler(filters.TEXT & ~filters.COMMAND, wd_amt)],
            W_BET: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_bet)],
            W_MINES_CNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, mines_cnt)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(back_main_h, pattern=r"^back_main$"),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("addpartner", cmd_addpartner))
    app.add_handler(CommandHandler("delpartner", cmd_delpartner))
    app.add_handler(CommandHandler("give", cmd_give))
    app.add_handler(CommandHandler("delbalance", cmd_delbalance))

    app.add_handler(CallbackQueryHandler(back_main_h, pattern=r"^back_main$"))
    app.add_handler(CallbackQueryHandler(profile, pattern=r"^profile$"))
    app.add_handler(CallbackQueryHandler(balance_h, pattern=r"^balance$"))
    app.add_handler(CallbackQueryHandler(play_h, pattern=r"^play$"))
    app.add_handler(CallbackQueryHandler(mini_h, pattern=r"^mini_games$"))
    app.add_handler(CallbackQueryHandler(author_h, pattern=r"^author_games$"))
    app.add_handler(CallbackQueryHandler(rating_h, pattern=r"^rating$"))
    app.add_handler(CallbackQueryHandler(referral_h, pattern=r"^referral$"))
    app.add_handler(CallbackQueryHandler(owner_h, pattern=r"^owner$"))
    app.add_handler(CallbackQueryHandler(owner_partners, pattern=r"^owner_partners$"))
    app.add_handler(CallbackQueryHandler(owner_cmds, pattern=r"^owner_cmds$"))
    app.add_handler(CallbackQueryHandler(mopen, pattern=r"^mopen:"))
    app.add_handler(CallbackQueryHandler(mcash, pattern=r"^mcash$"))
    app.add_handler(CallbackQueryHandler(tpick, pattern=r"^tpick:"))
    app.add_handler(CallbackQueryHandler(tcash, pattern=r"^tcash$"))
    app.add_handler(CallbackQueryHandler(ppick, pattern=r"^ppick:"))
    app.add_handler(CallbackQueryHandler(pcash, pattern=r"^pcash$"))
    app.add_handler(CallbackQueryHandler(noop, pattern=r"^noop$"))
    app.add_handler(CallbackQueryHandler(again_game, pattern=r"^again:"))
    app.add_handler(CallbackQueryHandler(setbet_game, pattern=r"^setbet:"))


    print("JackZo casino bot started")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
