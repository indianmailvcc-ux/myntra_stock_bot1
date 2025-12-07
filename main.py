import asyncio
import os
from typing import List

from bson import ObjectId
from pyrogram import Client, idle, filters
from pyrogram.types import Message
from aiohttp import web

from config import API_ID, API_HASH, BOT_TOKEN, CHECK_INTERVAL, OWNER_ID, MONGO_URI
from db import init_db, close_db, get_all_trackings, update_tracking_status
from myntra_checker import check_stock
from handlers import register_all_handlers


# ===================== TELEGRAM BOT CLIENT ===================== #

app = Client(
    "myntra_stock_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# ========== DEBUG /start HANDLER (VERY FLEXIBLE) ========== #

@app.on_message(
    filters.command(["start", "Start", "START"], prefixes=["/", "!", "."])
)
async def debug_start_handler(client: Client, message: Message):
    print(f"[OK] /start received -> User: {message.from_user.id}, Chat: {message.chat.id}")
    await message.reply_text(
        "🟢 *Bot is live and responding!*\n"
        "Yeh reply `main.py` ke direct handler se aa raha hai.\n\n"
        "Commands:\n"
        "• `/track <myntra_url> <size>`\n"
        "• `/list`\n"
        "• `/untrack 1`\n\n"
        "_Agar yeh message dikh raha hai = backend 100% OK._",
        quote=True
    )


# ======================== STOCK CHECKER ======================== #

async def _check_once():
    print("[LOOP] Checking Myntra items…")

    items: List[dict] = await get_all_trackings()
    print(f"[DB] {len(items)} items found")

    if not items:
        return

    for item in items:
        url = item.get("product_url")
        size = item.get("size")
        last_status = item.get("last_status", "unknown")
        chat_id = item.get("chat_id")
        doc_id = item.get("_id")

        current_status = await check_stock(url, size)
        print(f"[CHECK] URL={url} SIZE={size} STATUS={current_status}")

        if current_status == "unknown":
            continue

        # notify if status changes Out => In
        if last_status != "in_stock" and current_status == "in_stock":
            txt = (
                "🎉 *Back in Stock!*\n"
                f"Size `{size}` is now **IN STOCK** on Myntra.\n\n"
                f"{url}"
            )
            try:
                await app.send_message(chat_id, txt)
            except Exception as e:
                print("[ERROR] while sending stock message:", e)

        if isinstance(doc_id, str):
            doc_id = ObjectId(doc_id)
        await update_tracking_status(doc_id, current_status)


async def scheduler_loop():
    print("[SCHEDULER] Loop active")
    while True:
        try:
            await _check_once()
        except Exception as e:
            print("[ERROR] Checker failed:", e)
            if OWNER_ID:
                try:
                    await app.send_message(OWNER_ID, f"⚠ Checker Error: {e}")
                except Exception as e2:
                    print("[ERROR] failed to send checker error:", e2)
        await asyncio.sleep(CHECK_INTERVAL)


# ========================= WEB SERVER ========================== #

async def http_index(_):
    return web.Response(text="Myntra bot running OK")

async def start_web():
    app_web = web.Application()
    app_web.router.add_get("/", http_index)

    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[WEB] Server running on {port}")


# ============================= MAIN ============================ #

async def main():
    print("\n===== BOOTING BOT =====")
    print("API_ID=", API_ID, " BOT_TOKEN set=", bool(BOT_TOKEN), " MONGO_URI set=", bool(MONGO_URI))

    # DB init
    try:
        await init_db()
        print("[DB] Connected")
    except Exception as e:
        print("[DB ERR]", e)

    # Load handlers from handlers/ folder
    print("[HANDLERS] Loading...")
    register_all_handlers(app)

    # Connect to Telegram
    print("[BOT] Connecting to Telegram...")
    await app.start()
    print("[BOT] LIVE ✔")

    # Notify owner on restart
    if OWNER_ID:
        try:
            await app.send_message(OWNER_ID, "🟢 Bot restarted on Render. (/start debug enabled)")
        except Exception as e:
            print("[WARN] Could not DM owner:", e)

    # Start background jobs
    asyncio.create_task(scheduler_loop())
    asyncio.create_task(start_web())

    print("[SYSTEM] Idle mode (waiting for updates)")
    await idle()

    print("[SYSTEM] Shutting down...")
    await close_db()
    await app.stop()
    print("[SYSTEM] Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("[FATAL]", e)
