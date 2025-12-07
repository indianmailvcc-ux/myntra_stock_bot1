import asyncio
import os
from typing import List

from bson import ObjectId
from pyrogram import Client, idle

from config import API_ID, API_HASH, BOT_TOKEN, CHECK_INTERVAL, OWNER_ID
from db import init_db, close_db, get_all_trackings, update_tracking_status
from myntra_checker import check_stock
from handlers import register_all_handlers

from aiohttp import web  # NEW


app = Client(
    "myntra_stock_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


async def _check_once():
    items: List[dict] = await get_all_trackings()
    if not items:
        return

    for item in items:
        url = item.get("product_url")
        size = item.get("size")
        last_status = item.get("last_status", "unknown")
        chat_id = item.get("chat_id")
        doc_id = item.get("_id")

        current_status = await check_stock(url, size)

        if current_status == "unknown":
            continue

        # Only notify when going from NOT in_stock to in_stock
        if last_status != "in_stock" and current_status == "in_stock":
            try:
                text = (
                    "🎉 Good news!\n\n"
                    f"Jis product ko aap track kar rahe the, size `{size}` ab **IN STOCK** hai Myntra pe!\n\n"
                    f"Link: {url}\n\n"
                    "Jaldi order kar lo, fir se out of stock ho sakta hai. 😉"
                )
                await app.send_message(chat_id, text, disable_web_page_preview=False)
            except Exception:
                # ignore send errors silently
                pass

        # Update stored status
        if isinstance(doc_id, str):
            doc_id = ObjectId(doc_id)
        await update_tracking_status(doc_id, current_status)


async def scheduler_loop():
    """
    Simple loop with asyncio.sleep instead of external scheduler.
    """
    while True:
        try:
            await _check_once()
        except Exception as e:
            if OWNER_ID:
                try:
                    await app.send_message(OWNER_ID, f"Checker error: {e}")
                except Exception:
                    pass
        await asyncio.sleep(CHECK_INTERVAL)


# ---------- Tiny HTTP server for Render (health check) ----------

async def handle_root(request):
    return web.Response(text="OK")


async def start_web_server():
    app_web = web.Application()
    app_web.router.add_get("/", handle_root)

    port = int(os.getenv("PORT", "10000"))  # Render PORT env
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"HTTP server started on port {port}")


# --------------------------- MAIN ---------------------------

async def main():
    await init_db()

    register_all_handlers(app)

    await app.start()
    print("Bot started.")

    # Background Myntra checker
    asyncio.create_task(scheduler_loop())

    # Start tiny HTTP server so Render web service is happy
    asyncio.create_task(start_web_server())

    # Keep running until stopped
    await idle()

    await close_db()
    await app.stop()
    print("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())

