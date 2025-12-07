import asyncio
import os
from typing import List, Literal

from bson import ObjectId
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from aiohttp import web

from config import API_ID, API_HASH, BOT_TOKEN, CHECK_INTERVAL, MONGO_URI
from db import init_db, close_db, add_tracking, get_user_trackings, delete_user_tracking_by_index, get_all_trackings, update_tracking_status
from myntra_checker import check_stock

Status = Literal["in_stock","out_of_stock","unknown"]


# ================= BOT ================= #

app = Client(
    "myntra_stock_web_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# ========= /start handler working guaranteed ========= #

@app.on_message(filters.command("start"))
async def start_handler(client, msg: Message):
    await msg.reply_text(
        "👕 *Myntra Stock Tracker Active*\n\n"
        "Track product size availability on Myntra:\n\n"
        "/track <url> <size>\n"
        "/list\n"
        "/untrack <id>\n"
        "\nBot is running on Web-Service (free)."
    )


@app.on_message(filters.command("track"))
async def track_handler(client, msg: Message):

    if len(msg.command) < 3:
        return await msg.reply_text("Usage:\n`/track <myntra_url> <size>`")

    url = msg.command[1]
    size = " ".join(msg.command[2:])
    await msg.reply_text("⏳ Checking...")

    status: Status = await check_stock(url,size)
    tracking_id = await add_tracking(msg.from_user.id,msg.chat.id,url,size,status)

    await msg.reply_text(
        f"Tracking Started 🔍\nSize: `{size}`\nStatus: `{status}`\nID: `{tracking_id}`"
    )


@app.on_message(filters.command("list"))
async def list_handler(client,msg: Message):

    items = await get_user_trackings(msg.from_user.id)
    if not items:
        return await msg.reply_text("No active trackings!")

    text="📃 Active:\n\n"
    for i,x in enumerate(items,1):
        text+=f"**{i}.** {x['size']} | {x['last_status']}\n{x['product_url']}\n\n"
    await msg.reply_text(text,disable_web_page_preview=True)


@app.on_message(filters.command("untrack"))
async def untrack_handler(client,msg: Message):

    if len(msg.command) < 2: return await msg.reply_text("Usage:\n/untrack <id>")
    ok=await delete_user_tracking_by_index(msg.from_user.id,int(msg.command[1]))
    await msg.reply_text("Deleted ✔" if ok else "Invalid ID ❌")


# ================= BACKGROUND STOCK CHECK ================= #

async def checker():
    print("🔁 Stock check started")

    while True:
        items = await get_all_trackings()
        print(f"Checking {len(items)} items")

        for item in items:
            status=await check_stock(item["product_url"],item["size"])
            if status=="in_stock" and item["last_status"]!="in_stock":
                await app.send_message(
                    item["chat_id"],
                    f"🟢 BACK IN STOCK!\n{item['product_url']}\nSize `{item['size']}`"
                )
            await update_tracking_status(item["_id"],status)

        await asyncio.sleep(CHECK_INTERVAL)


# ================= WEB SERVER (IMPORTANT!!!) ================= #

async def web_index(request):
    return web.Response(text="BOT_RUNNING_OK",status=200)

async def start_webserver():
    PORT=int(os.getenv("PORT","10000"))
    app_web = web.Application()
    app_web.router.add_get("/",web_index)
    runner=web.AppRunner(app_web)
    await runner.setup()
    site=web.TCPSite(runner,"0.0.0.0",PORT)
    await site.start()
    print(f"🌍 Web-server running @ {PORT}")


# ================= MAIN ================= #

async def main():
    print("🚀 Bot starting Web-Service Mode")

    await init_db()
    await app.start()
    asyncio.create_task(checker())
    asyncio.create_task(start_webserver())   # THIS keeps bot alive!
    await idle()

    await close_db()
    await app.stop()


if __name__=="__main__":
    asyncio.run(main())
