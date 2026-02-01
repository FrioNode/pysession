import os
import sys
import asyncio

from bot import Bot, Config
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    SessionPasswordNeeded,
    FloodWait,
    PhoneNumberInvalid,
    ApiIdInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired
)
from pyromod import listen
from asyncio.exceptions import TimeoutError

bot = Bot()
OWNER_ID: int = int(os.getenv("OWNER_ID", 0))

API_TEXT = """Hi {}
Welcome to Pyrogram's SESSION_STRING generator Bot.

`Send your API_ID to Continue.`"""

HASH_TEXT = "`Send your API_HASH to Continue.`\n\nPress /cancel to Cancel."

PHONE_NUMBER_TEXT = (
    "`Now send your Phone number to Continue"
    " include Country code. eg. +12345678910`\n\n"
    "Press /cancel to Cancel."
)


async def is_cancel(msg: Message, text: str):
    if text and text.startswith("/cancel"):
        await msg.reply("`Process Cancelled.`")
        return True
    return False


@bot.on_message(filters.private & filters.command("start"))
async def genStr(bot: Bot, msg: Message):
    chat = msg.chat

    # API_ID
    api = await bot.ask(chat.id, API_TEXT.format(msg.from_user.mention))
    if await is_cancel(msg, api.text):
        return

    try:
        api_id = int(api.text)
    except ValueError:
        await api.delete()
        await msg.reply("`API ID Invalid.`\nPress /start to create again.")
        return

    await api.delete()

    # API_HASH
    hash_msg = await bot.ask(chat.id, HASH_TEXT)
    if await is_cancel(msg, hash_msg.text):
        return

    api_hash = hash_msg.text.strip()
    await hash_msg.delete()

    # Create temp client
    try:
        client = Client(":memory:", api_id=api_id, api_hash=api_hash)
    except Exception as e:
        await msg.reply(f"**ERROR:** `{e}`\nPress /start to create again.")
        return

    try:
        await client.connect()
    except Exception:
        await client.disconnect()
        await client.connect()

    await msg.reply("`Successfully Connected to your Client.`")

    # Phone number
    while True:
        number = await bot.ask(chat.id, PHONE_NUMBER_TEXT)
        if await is_cancel(msg, number.text):
            await client.disconnect()
            return

        phone = number.text.strip()
        await number.delete()

        confirm = await bot.ask(
            chat.id,
            f'`Is "{phone}" correct? (y/n):`\n\ntype: `y` (If Yes)\ntype: `n` (If No)'
        )
        if await is_cancel(msg, confirm.text):
            await client.disconnect()
            return

        if confirm.text.lower().startswith("y"):
            await confirm.delete()
            break

        await confirm.delete()

    # Send OTP
    try:
        sent = await client.send_code(phone)
        await asyncio.sleep(1)
    except FloodWait as e:
        await msg.reply(f"`You have floodwait of {e.x} Seconds`")
        return
    except ApiIdInvalid:
        await msg.reply("`Api Id and Api Hash are Invalid.`\nPress /start to create again.")
        return
    except PhoneNumberInvalid:
        await msg.reply("`Your Phone Number is Invalid.`\nPress /start to create again.")
        return

    # OTP loop (spaced only)
    attempts = 0
    max_attempts = 3

    while True:
        if attempts >= max_attempts:
            await msg.reply("`Max attempts reached.\nPress /start to create again.`")
            await client.disconnect()
            return

        try:
            otp = await bot.ask(
                chat.id,
                (
                    "`Enter the OTP sent to your telegram account:`\n"
                    "`Format: 1 2 3 4 5`\n\n"
                    "OTP must be spaced...!"
                    "Press /cancel to Cancel."
                ),
                timeout=300
            )
        except TimeoutError:
            await msg.reply("`Time limit reached of 5 min.\nPress /start to create again.`")
            await client.disconnect()
            return

        if await is_cancel(msg, otp.text):
            await client.disconnect()
            return

        otp_code = otp.text.strip()
        await otp.delete()

        try:
            await client.sign_in(
                phone,
                sent.phone_code_hash,
                phone_code=otp_code
            )
            break

        except PhoneCodeInvalid:
            attempts += 1
            await msg.reply(f"`Invalid Code. Attempts left: {max_attempts - attempts}`")

        except PhoneCodeExpired:
            await msg.reply("`Code Expired. Sending a new code...`")
            sent = await client.send_code(phone)
            attempts = 0
            await asyncio.sleep(1)

        except SessionPasswordNeeded:
            try:
                pwd = await bot.ask(
                    chat.id,
                    "`This account has two-step verification enabled.\nPlease enter your second factor authentication code.`\nPress /cancel to Cancel.",
                    timeout=300
                )
            except TimeoutError:
                await msg.reply("`Time limit reached of 5 min.\nPress /start to create again.`")
                await client.disconnect()
                return

            if await is_cancel(msg, pwd.text):
                await client.disconnect()
                return

            await client.check_password(pwd.text.strip())
            await pwd.delete()
            break

    # Export session
    session_string = await client.export_session_string()

    await client.send_message(
        "me",
        f"#PYROGRAM #SESSION_STRING\n\n{session_string}",
        parse_mode=None
    )

    text = "`String Session is Successfully Generated.\nClick on Button Below.`"
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="Click Me", url=f"tg://openmessage?user_id={chat.id}")]]
    )

    await bot.send_message(chat.id, text, reply_markup=reply_markup)
    await asyncio.sleep(1)
    await client.disconnect()


@bot.on_message(filters.private & filters.user(OWNER_ID) & filters.command("restart"))
async def restart(bot: Bot, msg: Message):
    await msg.reply("✅")
    await msg.reply("`Bot: Restarting...`")

    if bot.hu_app:
        bot.hu_app.restart()
    else:
        python = sys.executable
        os.execv(python, [python] + sys.argv)


@bot.on_message(filters.private & filters.command("help"))
async def help_cmd(_, msg: Message):
    out = f"""
Hello {msg.from_user.mention}, this is Pyrogram Session String Generator Bot \
which gives you `SESSION_STRING` for your UserBot.

It needs `API_ID`, `API_HASH`, `PHONE_NUMBER` and One-time Verification Code \
which will be sent to your `PHONE_NUMBER`.

You must enter OTP in spaced format: `1 2 3 4 5`

(C) Author: [frionode](https://t.me/frionode) and [Krakinzlab](https://t.me/krakinzlab)
Give a Star ⭐️ to [REPO](https://github.com/frionode/pysession) if you like this Bot.
"""
    await msg.reply(out, disable_web_page_preview=True)


if __name__ == "__main__":
    bot.run()