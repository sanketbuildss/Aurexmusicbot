import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, Update
from yt_dlp import YoutubeDL

from config import API_ID, API_HASH, BOT_TOKEN, SESSION_STRING, SUDO_USERS

# ---------- Clients ----------
bot = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("music_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
calls = PyTgCalls(userbot)

# ---------- Per-chat state ----------
queues = {}        # chat_id -> list of tracks
current = {}       # chat_id -> current track info
paused = {}        # chat_id -> bool

# ---------- yt-dlp helper ----------
def search_yt(query: str):
    """Search karke best audio URL + title return karta hai"""
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch",
        "noplaylist": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)
        if "entries" in info:
            info = info["entries"][0]
        return {
            "url": info["url"],
            "title": info.get("title", query),
            "duration": info.get("duration", 0),
        }

# ---------- Play next in queue ----------
async def play_next(chat_id: int):
    if chat_id not in queues or not queues[chat_id]:
        current.pop(chat_id, None)
        try:
            await calls.leave_call(chat_id)
        except Exception:
            pass
        await bot.send_message(chat_id, "✅ Queue khatam! Voice chat se leave kar diya.")
        return

    track = queues[chat_id].pop(0)
    current[chat_id] = track
    paused[chat_id] = False

    await calls.play(chat_id, MediaStream(track["url"]))
    await bot.send_message(
        chat_id,
        f"▶️ **Now Playing:** {track['title']}\n"
        f"⏱ Duration: {track['duration']}s\n"
        f"📋 Queue mein: {len(queues[chat_id])} aur"
    )

# ---------- /play command ----------
@bot.on_message(filters.command("play") & filters.group)
async def play_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("❓ Usage: `/play <song name>`")

    query = " ".join(message.command[1:])
    msg = await message.reply(f"🔍 Searching: `{query}`...")

    try:
        track = await asyncio.to_thread(search_yt, query)
    except Exception as e:
        return await msg.edit(f"❌ Search fail: `{e}`")

    chat_id = message.chat.id
    queues.setdefault(chat_id, [])

    # Agar already kuch chal raha hai → queue mein add
    if chat_id in current:
        queues[chat_id].append(track)
        return await msg.edit(
            f"➕ **Queued:** {track['title']}\n"
            f"📍 Position: {len(queues[chat_id])}"
        )

    # Naya play
    await msg.edit(f"⏳ Joining voice chat & playing: {track['title']}")
    current[chat_id] = track
    queues[chat_id] = queues.get(chat_id, [])

    try:
        await calls.play(chat_id, MediaStream(track["url"]))
        await msg.edit(f"▶️ **Now Playing:** {track['title']}")
    except Exception as e:
        current.pop(chat_id, None)
        await msg.edit(f"❌ Play fail: `{e}`\n\nMake sure voice chat active hai & userbot admin hai.")

# ---------- /skip ----------
@bot.on_message(filters.command("skip") & filters.group)
async def skip_cmd(client, message):
    chat_id = message.chat.id
    if chat_id not in current:
        return await message.reply("❌ Kuch play nahi ho raha.")
    await message.reply("⏭ Skipping...")
    await play_next(chat_id)

# ---------- /pause & /resume ----------
@bot.on_message(filters.command("pause") & filters.group)
async def pause_cmd(client, message):
    chat_id = message.chat.id
    if chat_id not in current:
        return await message.reply("❌ Kuch play nahi ho raha.")
    await calls.pause(chat_id)
    paused[chat_id] = True
    await message.reply("⏸ Paused.")

@bot.on_message(filters.command("resume") & filters.group)
async def resume_cmd(client, message):
    chat_id = message.chat.id
    if not paused.get(chat_id):
        return await message.reply("❌ Paused nahi hai.")
    await calls.resume(chat_id)
    paused[chat_id] = False
    await message.reply("▶️ Resumed.")

# ---------- /stop ----------
@bot.on_message(filters.command("stop") & filters.group)
async def stop_cmd(client, message):
    chat_id = message.chat.id
    queues[chat_id] = []
    current.pop(chat_id, None)
    try:
        await calls.leave_call(chat_id)
    except Exception:
        pass
    await message.reply("⏹ Stopped & left voice chat.")

# ---------- /queue ----------
@bot.on_message(filters.command("queue") & filters.group)
async def queue_cmd(client, message):
    chat_id = message.chat.id
    if not queues.get(chat_id) and chat_id not in current:
        return await message.reply("📭 Queue khaali hai.")

    text = ""
    if chat_id in current:
        text += f"▶️ **Now:** {current[chat_id]['title']}\n\n"
    if queues.get(chat_id):
        text += "**Up Next:**\n"
        for i, t in enumerate(queues[chat_id][:10], 1):
            text += f"{i}. {t['title']}\n"
    await message.reply(text or "📭 Khaali")

# ---------- Stream end handler → auto next ----------
@calls.on_update()
async def stream_handler(client, update: Update):
    if update.__class__.__name__ == "StreamEnded":
        await play_next(update.chat_id)

# ---------- Startup ----------
async def main():
    await bot.start()
    await userbot.start()
    await calls.start()
    print("✅ Bot + Userbot + PyTgCalls ready!")
    await asyncio.Event().wait()  # forever

if __name__ == "__main__":
    asyncio.run(main())
