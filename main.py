import os
import asyncio
import re
import json
import threading
from flask import Flask, render_template, request, redirect, url_for
from telethon import TelegramClient, events, types
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

# --- Credentials from Environment ---
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

# --- Flask Web App Setup ---
app = Flask(__name__)

# --- JSON File Storage Setup ---
DATA_DIR = 'data'
CHANNELS_FILE = os.path.join(DATA_DIR, 'channels.json')

def get_channels_from_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CHANNELS_FILE):
        return {"sources": [], "destinations": []}
    try:
        with open(CHANNELS_FILE, 'r') as f:
            data = json.load(f)
            if 'sources' not in data: data['sources'] = []
            if 'destinations' not in data: data['destinations'] = []
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return {"sources": [], "destinations": []}

def save_channels(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CHANNELS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- Web Interface Routes ---
@app.route('/')
def index():
    channels = get_channels_from_file()
    return render_template('index.html', source_channels=channels['sources'], destination_channels=channels['destinations'])

@app.route('/add_channel', methods=['POST'])
def add_channel():
    channel_id_str = request.form.get('channel_id')
    channel_type = request.form.get('channel_type')
    if channel_id_str and channel_type:
        channel_id = int(channel_id_str)
        channels = get_channels_from_file()
        target_list = channels['sources'] if channel_type == 'source' else channels['destinations']
        if channel_id not in target_list:
            target_list.append(channel_id)
        save_channels(channels)
    return redirect(url_for('index'))

# --- THIS IS THE CORRECTED DELETE ROUTE ---
# It now accepts the channel_id as a string from the URL to handle negative numbers.
@app.route('/delete_channel/<string:channel_type>/<path:channel_id_str>')
def delete_channel(channel_type, channel_id_str):
    try:
        # We manually convert the string ID to an integer here.
        channel_id = int(channel_id_str)
    except ValueError:
        # If something goes wrong, just go back to the main page.
        return redirect(url_for('index'))
        
    channels = get_channels_from_file()
    target_list = channels.get('sources', []) if channel_type == 'source' else channels.get('destinations', [])
    if channel_id in target_list:
        target_list.remove(channel_id)
    save_channels(channels)
    return redirect(url_for('index'))

# --- Telethon Bot Logic ---
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

async def run_telethon_bot():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    print("User bot is starting...")

    @client.on(events.NewMessage())
    async def handle_new_message(event):
        channels = get_channels_from_file()
        source_channels = set(channels['sources'])
        destination_channels = set(channels['destinations'])

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

    await client.start()
    print("User bot started successfully!")
    await client.run_until_disconnected()

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting Telethon bot in a background thread...")
    bot_thread = threading.Thread(target=lambda: asyncio.run(run_telethon_bot()), daemon=True)
    bot_thread.start()
    
    print("Starting Flask web server...")
    # For local testing, use debug=True. For Render, it should be False.
    app.run(host='0.0.0.0', port=5000, debug=True)