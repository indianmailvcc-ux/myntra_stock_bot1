from pyrogram import Client, filters
from pyrogram.types import Message

from db import get_user_trackings, delete_user_tracking_by_index


def register_list_untrack_handlers(app: Client):
    @app.on_message(filters.command("list"))
    async def list_handler(client: Client, message: Message):
        items = await get_user_trackings(message.from_user.id)
        if not items:
            await message.reply_text("🙈 Aap kuch bhi track nahi kar rahe ho abhi.")
            return

        lines = ["📋 Aapki current trackings:\n"]
        for idx, item in enumerate(items, start=1):
            lines.append(
                f"**{idx}.** Size: `{item.get('size')}` | Status: `{item.get('last_status', 'unknown')}`\n"
                f"URL: {item.get('product_url')}\n"
            )

        await message.reply_text("\n".join(lines), disable_web_page_preview=True)

    @app.on_message(filters.command("untrack"))
    async def untrack_handler(client: Client, message: Message):
        if len(message.command) < 2:
            await message.reply_text(
                "❗ Usage:\n`/untrack <index>`\n\n"
                "Index wo number hai jo `/list` mein dikh raha hai.",
                quote=True,
            )
            return

        try:
            index = int(message.command[1])
        except ValueError:
            await message.reply_text("❗ Index number mein hona chahiye. Example: `/untrack 2`")
            return

        ok = await delete_user_tracking_by_index(message.from_user.id, index)
        if not ok:
            await message.reply_text("❗ Invalid index. Pehle `/list` se sahi number dekho.")
        else:
            await message.reply_text("✅ Tracking hata di gayi.")