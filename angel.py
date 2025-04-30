import os
import asyncio
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv

# ==== WOODcraft ==== SudoR2spr ==== #
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
USER_ID = int(os.getenv("USER_ID"))
PORT = int(os.getenv("PORT", 8080))
DELAY_SECONDS = 5

# ===== WOODcraft ==== SudoR2spr ==== #

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
app = Flask(__name__)
forwarding_enabled = True  # গ্লোবাল অন/অফ স্ট্যাটাস

# ====== MongoDB সেটআপ ======= # 

MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["forwardBot"]
collection = db["forwarded_files"]

# === WOODcraft ==== SudoR2spr === #
# Message ID কে unique করতে index তৈরি
collection.create_index("message_id", unique=True)

async def is_forwarded(msg_id):
    return collection.find_one({"message_id": msg_id}) is not None

async def mark_as_forwarded(msg_id):
    try:
        collection.insert_one({"message_id": msg_id})
    except DuplicateKeyError:
        pass

async def send_without_tag(target_chat, original_msg):
    if await is_forwarded(original_msg.id):
        print(f"⏩ Skip Done (duplicate): {original_msg.id}")
        return False
    try:
        await client.forward_messages(
            entity=target_chat,
            messages=original_msg,
            silent=True
        )
        await mark_as_forwarded(original_msg.id)
        print(f"✅ Forwarded: {original_msg.id}")
        return True
    except FloodWaitError as e:
        print(f"⏳ FloodWait: {e.seconds} Wait a second.")
        await asyncio.sleep(e.seconds)
        return await send_without_tag(target_chat, original_msg)
    except Exception as e:
        print(f"🚨 Forward error: {str(e)}")
        return False

async def forward_old_messages():
    async for message in client.iter_messages(SOURCE_CHAT_ID, reverse=True):
        if forwarding_enabled:
            await send_without_tag(TARGET_CHAT_ID, message)
            await asyncio.sleep(DELAY_SECONDS)

@client.on(events.NewMessage(pattern='/status'))
async def status_handler(event):
    if event.sender_id != USER_ID: return
    status = "Active ✅" if forwarding_enabled else "inactive ❌"
    await event.reply(f"Current Status: {status}")

@client.on(events.NewMessage(pattern='/off'))
async def off_handler(event):
    global forwarding_enabled
    if event.sender_id != USER_ID: return
    forwarding_enabled = False
    await event.reply("❌ Forwarding has been disabled.")

@client.on(events.NewMessage(pattern='/on'))
async def on_handler(event):
    global forwarding_enabled
    if event.sender_id != USER_ID: return
    forwarding_enabled = True
    await event.reply("✅ Forwarding is enabled.")

@client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
async def new_message_handler(event):
    global forwarding_enabled
    if forwarding_enabled:
        await asyncio.sleep(DELAY_SECONDS)
        await send_without_tag(TARGET_CHAT_ID, event.message)
        print(f"✅ {event.message.id} Forwarded")

# === WOODcraft ==== SudoR2spr === #

@app.route("/")
def home():
    return "🤖 Activate the Angel bot!", 200

async def main():
    await client.start()
    print("✅ Bot launched successfully!")
    # পুরনো মেসেজ ফরওয়ার্ড টাস্ক শুরু করুন
    asyncio.create_task(forward_old_messages())
    await client.run_until_disconnected()

# === WOODcraft ==== SudoR2spr === #
if __name__ == "__main__":
    threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": PORT, "use_reloader": False}
    ).start()
    asyncio.run(main())
