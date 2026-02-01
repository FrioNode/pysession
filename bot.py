import os
import asyncio
from typing import Optional

from pyrogram import Client, filters
from pyromod import listen
from pyrogram.errors import MessageNotModified
from dotenv import load_dotenv
load_dotenv() 



# =========================
# CONFIG
# =========================
class Config:
    API_ID: int = int(os.getenv("API_ID", 0))
    API_HASH: str = os.getenv("API_HASH")
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")

    APP_NAME: str = os.getenv("APP_NAME")        # optional
    API_KEY: str = os.getenv("API_KEY")          # optional

    IS_HEROKU: bool = bool(API_KEY and APP_NAME)


# =========================
# HEROKU HELPERS (LAZY)
# =========================
def get_heroku_app():
    """
    Lazily fetch the Heroku app.
    Returns None if not running on Heroku or if auth fails.
    """
    if not Config.IS_HEROKU:
        return None

    try:
        from heroku3 import from_key
        return from_key(Config.API_KEY).apps()[Config.APP_NAME]
    except Exception as e:
        print(f"[WARN] Heroku integration disabled: {e}")
        return None


# =========================
# BOT
# =========================
class Bot(Client):
    def __init__(self):
        super().__init__(
            "bot_session",  # <--- persistent file-based session
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
        )
        self.hu_app = get_heroku_app()


    async def start(self):
        await super().start()
        print("🤖 Bot started")

    async def stop(self):
        await super().stop()
        print("🛑 Bot stopped")


# =========================
# COMMANDS
# =========================
bot = Bot()


@bot.on_message(filters.command("start"))
async def start_cmd(_, msg):
    await msg.reply("🦉 Bot is alive!\n\nWorks locally & on Heroku.")


@bot.on_message(filters.command("sleep"))
async def sleep_cmd(_, msg):
    await msg.reply("`Sleeping for 10 seconds...`")
    await asyncio.sleep(10)

    if bot.hu_app:
        await msg.reply("♻️ Restarting Heroku dyno...")
        bot.hu_app.restart()
    else:
        await msg.reply("⚠️ Restart skipped (not running on Heroku)")


# =========================
# ENTRYPOINT
# =========================
if __name__ == "__main__":
    if not all([Config.API_ID, Config.API_HASH, Config.BOT_TOKEN]):
        raise RuntimeError("Missing required environment variables")

    bot.run()
