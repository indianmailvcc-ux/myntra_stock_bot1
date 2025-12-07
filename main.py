import asyncio
import os
from typing import List

from bson import ObjectId
from pyrogram import Client, idle
from aiohttp import web

from config import API_ID, API_HASH, BOT_TOKEN, CHECK_INTERVAL, OWNER_ID, MONGO_URI
from db import init_db, close_db, get_all_trackings, update_tracking_status
from myntra_checker import check_stock
from handlers import register_all_handlers


app = Client(
    "myntra_stock_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


async def _check_once():
    print(">>> Running _check_once()")
    items: List[dict] = await get_all_trackings()
    print(f">>> Found {len(items)} items in DB")
    if not items:
        return

    for item in items:
        url = item.get("product_url")
        size = item.get("size")
        last_status = item.get("last_status", "unknown")
        chat_id = item.get("chat_id")
        doc_id = item.get("_id")

        print(f">>> Checking {url} size {size}, last_status={last_status}")

        current_status = await check_stock(url, size)
        print(f">>> Current_status = {current_status}")

        if current_status == "unknown":
            continue

        if last_status != "in_stock" and current_status == "in_stock":
            try:
                text = (
                    "🎉 Good news!\n\n"
                    f"Jis product ko aap track kar rahe the, size `{size}` ab **IN STOCK** hai Myntra pe!\n\n"
                    f"Link: {url}\n\n"
                    "Jaldi order kar lo, fir se out of stock ho sakta hai. 😉"
                )
                await app.send_message(chat_id, text, disable_web_page_preview=False)
            except Exception as e:
                print(f">>> Error while sending message: {e}")

        if isinstance(doc_id, str):
            doc_id = ObjectId(doc_id)
        await update_tracking_status(doc_id, current_status)


async def scheduler_loop():
    print(">>> Scheduler loop started")
    while True:
        try:
            await _check_once()
        except Exception as e:
            print(f">>> Scheduler error: {e}")
            if OWNER_ID:
                try:
                    await app.send_message(OWNER_ID, f"Checker error: {e}")
                except Exception as e2:
                    print(f">>> Failed to send checker error to owner: {e2}")
        await asyncio.sleep(CHECK_INTERVAL)


# ----------- Tiny HTTP server for Render health check ----------

async def handle_root(request):
    return web.Response(text="OK")


async def start_web_server():
    app_web = web.Application()
    app_web.router.add_get("/", handle_root)

    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f">>> HTTP server started on port {port}")


# ------------------------------ MAIN ------------------------------

async def main():
    print(">>> main() starting")
    print(f">>> API_ID={API_ID}, BOT_TOKEN set={bool(BOT_TOKEN)}, MONGO_URI set={bool(MONGO_URI)}")

    # Init DB
    try:
        await init_db()
        print(">>> DB init OK")
    except Exception as e:
        print(f">>> DB init FAILED: {e}")
        # DB fail hone pe bhi bot start karne denge
        # return

    # Register handlers
    print(">>> Registering handlers")
    register_all_handlers(app)

    # Start Telegram bot
    print(">>> Starting Pyrogram client")
    await app.start()
    print(">>> Bot started and connected to Telegram")

    # Background tasks
    asyncio.create_task(scheduler_loop())
    asyncio.create_task(start_web_server())

    print(">>> Entering idle()")
    await idle()

    print(">>> Shutting down...")
    await close_db()
    await app.stop()
    print(">>> Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f">>> FATAL ERROR in main(): {e}")
