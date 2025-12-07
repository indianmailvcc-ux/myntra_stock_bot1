import asyncio
import os
from typing import List, Literal

from bson import ObjectId
from pyrogram import Client, filters, idle
from pyrogram.types import Message

from config import API_ID, API_HASH, BOT_TOKEN, CHECK_INTERVAL
from db import (
    init_db,
    close_db,
    add_tracking,
    get_user_trackings,
    delete_user_tracking_by_index,
    get_all_trackings,
    update_tracking_status,
)
from myntra_checker import check_stock


StockStatus = Literal["in_stock", "out_of_stock", "unknown"]

# ===================== TELEGRAM BOT CLIENT ===================== #

app = Client(
    "myntra_stock_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# ======================== BASIC HANDLERS ======================= #

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    print(">>> /start from", message.from_user.id)
    txt = (
        "👋 *Myntra Stock Tracker Bot*\n\n"
        "Main aapke liye Myntra products ka specific *size* track karta hoon.\n"
        "Jaise hi wo size `OUT OF STOCK` se `IN STOCK` hoga, main aapko notify karunga.\n\n"
        "Commands:\n"
        "• `/track <myntra_url> <size>` – tracking start\n"
        "• `/list` – jo product track ho rahe hain unki list\n"
        "• `/untrack <index>` – list me se ek tracking delete\n\n"
        "Example:\n"
        "`/track https://www.myntra.com/men-tshirts/xyz  M`"
    )
    await message.reply_text(txt, quote=True)


@app.on_message(filters.command("track"))
async def track_handler(client: Client, message: Message):
    """
    Usage: /track <myntra_url> <size>
    """
    print(">>> /track from", message.from_user.id, "->", message.text)

    if len(message.command) < 3:
        await message.reply_text(
            "❗ Usage:\n`/track <myntra_url> <size>`\n\n"
            "Example:\n`/track https://www.myntra.com/...  M`",
            quote=True,
        )
        return

    _, url, size = message.command[0], message.command[1], " ".join(message.command[2:])
    size = size.strip()

    if not url.startswith("http"):
        await message.reply_text("❗ Please provide a valid Myntra URL starting with http/https.")
        return

    await message.reply_text("⏳ Checking current stock status, wait...", quote=True)

    status: StockStatus = await check_stock(url, size)

    if status == "unknown":
        await message.reply_text(
            "⚠ Iss product/size ka status pata nahi chal paya.\n"
            "URL ya size check karo, ya thodi der baad try karo.",
            quote=True,
        )
        return

    tracking_id = await add_tracking(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        product_url=url,
        size=size,
        initial_status=status,
    )

    if status == "in_stock":
        msg = (
            "✅ Abhi ye size **IN STOCK** hai.\n"
            "Main fir bhi track karta rahunga. Agar status change hua to notify karunga. 🔔\n\n"
            f"`ID: {tracking_id}`"
        )
    else:
        msg = (
            "📉 Abhi ye size **OUT OF STOCK** hai.\n"
            "Jaise hi ye available hoga, main yahi batata rahunga. 🔔\n\n"
            f"`ID: {tracking_id}`"
        )

    await message.reply_text(msg, quote=True)


@app.on_message(filters.command("list"))
async def list_handler(client: Client, message: Message):
    print(">>> /list from", message.from_user.id)
    items = await get_user_trackings(message.from_user.id)

    if not items:
        await message.reply_text("🙈 Aap abhi koi bhi product track nahi kar rahe ho.")
        return

    lines = ["📋 *Your current trackings:*\n"]
    for idx, item in enumerate(items, start=1):
        url = item.get("product_url")
        size = item.get("size")
        status = item.get("last_status", "unknown")
        lines.append(
            f"`{idx}.` Size: `{size}` | Status: `{status}`\n{url}\n"
        )

    await message.reply_text("\n".join(lines), disable_web_page_preview=True)


@app.on_message(filters.command("untrack"))
async def untrack_handler(client: Client, message: Message):
    print(">>> /untrack from", message.from_user.id, "->", message.text)

    if len(message.command) < 2:
        await message.reply_text(
            "❗ Usage:\n`/untrack <index>`\n\n"
            "Index wo number hai jo `/list` me dikh raha hai.",
            quote=True,
        )
        return

    try:
        index = int(message.command[1])
    except ValueError:
        await message.reply_text("❗ Index number hona chahiye. Example: `/untrack 2`")
        return

    ok = await delete_user_tracking_by_index(message.from_user.id, index)
    if not ok:
        await message.reply_text("❗ Invalid index. Pehle `/list` se sahi number dekho.")
    else:
        await message.reply_text("✅ Tracking delete kar diya.")


# ===================== BACKGROUND CHECKER ====================== #

async def _check_once():
    print(">>> [LOOP] Checking all tracked items...")
    items: List[dict] = await get_all_trackings()
    print(f">>> [DB] {len(items)} items found")

    if not items:
        return

    for item in items:
        url = item.get("product_url")
        size = item.get("size")
        last_status = item.get("last_status", "unknown")
        chat_id = item.get("chat_id")
        doc_id = item.get("_id")

        current_status: StockStatus = await check_stock(url, size)
        print(f">>> [CHECK] URL={url}, SIZE={size}, STATUS={current_status}")

        if current_status == "unknown":
            continue

        if last_status != "in_stock" and current_status == "in_stock":
            text = (
                "🎉 *Good news!*\n\n"
                f"Jis product ko aap track kar rahe the, size `{size}` ab **IN STOCK** hai Myntra pe!\n\n"
                f"{url}\n\n"
                "Jaldi order kar lo, fir se out of stock ho sakta hai. 😉"
            )
            try:
                await app.send_message(chat_id, text)
            except Exception as e:
                print(">>> [ERROR] while sending in-stock message:", e)

        if isinstance(doc_id, str):
            doc_id = ObjectId(doc_id)
        await update_tracking_status(doc_id, current_status)


async def scheduler_loop():
    print(">>> [SCHEDULER] Started with interval =", CHECK_INTERVAL, "seconds")
    while True:
        try:
            await _check_once()
        except Exception as e:
            print(">>> [SCHEDULER ERROR]", e)
        await asyncio.sleep(CHECK_INTERVAL)


# ========================== MAIN =============================== #

async def main():
    print("===== BOOTING FULL MYNTRA BOT =====")
    print("API_ID =", API_ID, " BOT_TOKEN set =", bool(BOT_TOKEN))

    # Init DB
    from config import MONGO_URI
    print("MONGO_URI set =", bool(MONGO_URI))
    try:
        await init_db()
        print(">>> [DB] init OK")
    except Exception as e:
        print(">>> [DB ERROR]", e)

    # Start bot
    print(">>> [BOT] starting client...")
    await app.start()
    print(">>> [BOT] LIVE ✔")

    # Start scheduler
    asyncio.create_task(scheduler_loop())

    print(">>> [SYSTEM] idle()...")
    await idle()

    print(">>> [SYSTEM] stopping...")
    await close_db()
    await app.stop()
    print(">>> [SYSTEM] stopped.")


if __name__ == "__main__":
    asyncio.run(main())
