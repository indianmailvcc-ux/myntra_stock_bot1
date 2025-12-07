from pyrogram import Client, filters
from pyrogram.types import Message

from db import add_tracking
from myntra_checker import check_stock


def register_track_handlers(app: Client):
    @app.on_message(filters.command("start"))
    async def start_handler(client: Client, message: Message):
        text = (
            "👋 Hi!\n\n"
            "Main aap ke liye Myntra products ka size stock track kar sakta hoon.\n\n"
            "Commands:\n"
            "• /track <myntra_url> <size> – specific size track karo\n"
            "• /list – aap jo track kar rahe ho wo dekho\n"
            "• /untrack <index> – kisi tracking ko hatao\n\n"
            "Example:\n"
            "/track https://www.myntra.com/tshirts/xyz  M"
        )
        await message.reply_text(text)

    @app.on_message(filters.command("track"))
    async def track_handler(client: Client, message: Message):
        """
        Usage: /track <myntra_url> <size>
        """
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
            await message.reply_text("❗ Please provide a valid URL starting with http/https.")
            return

        await message.reply_text("⏳ Checking current stock status, please wait...")

        status = await check_stock(url, size)

        if status == "unknown":
            await message.reply_text(
                "⚠ Iss product/size ka status pata nahi chal paya.\n"
                "URL ya size check karo, ya thodi der baad try karo."
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
                "✅ Currently **IN STOCK** hai ye size.\n"
                "Main fir bhi track karta rahunga, agar out/in stock change hoga to batata rahunga.\n\n"
                f"ID: `{tracking_id}`"
            )
        else:
            msg = (
                "📉 Abhi ye size **OUT OF STOCK** hai.\n"
                "Jaise hi ye available hoga, main yahi pe notify karunga. 🔔\n\n"
                f"ID: `{tracking_id}`"
            )

        await message.reply_text(msg)