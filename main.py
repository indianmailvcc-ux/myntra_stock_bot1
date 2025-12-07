from pyrogram import Client, filters

import os

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = Client(
    "myntra_test_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


@app.on_message(filters.command("start"))
async def start_handler(client, message):
    print(">>> /start received from", message.from_user.id)
    await message.reply_text("✅ Simple test bot working!")


if __name__ == "__main__":
    print(">>> Starting SIMPLE bot")
    app.run()
