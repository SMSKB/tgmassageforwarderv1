import os
import json
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# The JSON file is the single source of truth
CHANNELS_FILE = 'channels.json'

def get_channels():
    if not os.path.exists(CHANNELS_FILE):
        return {"sources": [], "destinations": []}
    try:
        with open(CHANNELS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"sources": [], "destinations": []}

def save_channels(data):
    with open(CHANNELS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def index():
    channels = get_channels()
    return render_template('index.html', source_channels=channels.get('sources', []), destination_channels=channels.get('destinations', []))

@app.route('/add_channel', methods=['POST'])
def add_channel():
    channel_id_str = request.form.get('channel_id')
    channel_type = request.form.get('channel_type')
    if channel_id_str and channel_type:
        channel_id = int(channel_id_str)
        channels = get_channels()
        target_list = channels.get('sources', []) if channel_type == 'source' else channels.get('destinations', [])
        if channel_id not in target_list:
            target_list.append(channel_id)
        if channel_type == 'source':
            channels['sources'] = target_list
        else:
            channels['destinations'] = target_list
        save_channels(channels)
    return redirect(url_for('index'))

@app.route('/delete_channel/<string:channel_type>/<path:channel_id_str>')
def delete_channel(channel_type, channel_id_str):
    try:
        channel_id = int(channel_id_str)
    except ValueError:
        return redirect(url_for('index'))
    channels = get_channels()
    target_list = channels.get('sources', []) if channel_type == 'source' else channels.get('destinations', [])
    if channel_id in target_list:
        target_list.remove(channel_id)
    if channel_type == 'source':
        channels['sources'] = target_list
    else:
        channels['destinations'] = target_list
    save_channels(channels)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)