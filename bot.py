import os
import asyncio
import re
import json
from telethon import TelegramClient, events, types
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

CHANNELS_FILE = 'channels.json'

def get_channels_from_file():
    if not os.path.exists(CHANNELS_FILE):
        return set(), set()
    try:
        with open(CHANNELS_FILE, 'r') as f:
            data = json.load(f)
            sources = set(data.get('sources', []))
            destinations = set(data.get('destinations', []))
            return sources, destinations
    except (json.JSONDecodeError, FileNotFoundError):
        return set(), set()

def modify_message_text(original_text):
    if not original_text: return ""
    replacement_link = "https://broker-qx.pro/?lid=1533268"
    replacement_username = "@san1two"
    pattern = r'(\[.*?\]\((https?://[^\s]+)\))|((https?://[^\s]+))|(@\w+)'

    def replacer(match):
        md_full, md_url, sa_full, sa_url, username = match.groups()
        url_to_check = md_url or sa_url
        if url_to_check:
            if "t.me/" in url_to_check or "telegram.me/" in url_to_check:
                return replacement_username
            else:
                return replacement_link
        elif username:
            return replacement_username
        return match.group(0)
        
    return re.sub(pattern, replacer, original_text)

async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    print("User bot is starting...")

    @client.on(events.NewMessage())
    async def handle_new_message(event):
        source_channels, destination_channels = get_channels_from_file()
        if event.chat_id not in source_channels:
            return
        if not destination_channels:
            return

        print(f"\n>>> New message in source channel {event.chat_id}. Processing...")
        message = event.message
        modified_text = modify_message_text(message.text)
        
        for dest_channel in destination_channels:
            try:
                is_real_media = message.media and not isinstance(message.media, types.MessageMediaWebPage)
                if is_real_media:
                    temp_file = await client.download_media(message.media)
                    await client.send_file(dest_channel, temp_file, caption=modified_text, link_preview=False)
                    os.remove(temp_file)
                elif message.text:
                    await client.send_message(dest_channel, modified_text, link_preview=False)
                print(f"[SUCCESS] Sent message to {dest_channel}")
            except Exception as e:
                print(f"[ERROR] Failed to send to {dest_channel}: {e}")

    async with client:
        print("User bot started successfully!")
        await client.run_until_disconnected()

if __name__ == "__main__":
    if not all([API_ID, API_HASH, SESSION_STRING]):
        print("ERROR: Missing one or more required environment variables.")
    else:
        asyncio.run(main())