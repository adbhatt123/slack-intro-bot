import os
import json
import gspread
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier
from google.oauth2.service_account import Credentials
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# ---------- Slack Setup ----------
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')
SLACK_CHANNEL_ID = "C013KH3JS3T"  # Your Slack channel ID

slack_client = WebClient(token=SLACK_BOT_TOKEN)
verifier = SignatureVerifier(signing_secret=SLACK_SIGNING_SECRET)

# ---------- Google Sheets Setup ----------
# Load service account credentials from an environment variable
SERVICE_ACCOUNT_JSON = os.environ.get("SERVICE_ACCOUNT_JSON")
if not SERVICE_ACCOUNT_JSON:
    raise Exception("SERVICE_ACCOUNT_JSON environment variable is not set.")

service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
SHEET_NAME = "CC Intros"  # Your Google Sheet name
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

sheet_client = gspread.authorize(creds)
sheet = sheet_client.open(SHEET_NAME).sheet1

def write_to_sheet(user_name, user_id, message_text, email):
    sheet.append_row([
        user_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        message_text,
        user_id,
        email
    ])
    print(f"✅ Saved to Google Sheet: {user_name} | Email: {email}")

def send_reply(channel, thread_ts, message):
    try:
        response = slack_client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=message
        )
        return response
    except Exception as e:
        print(f"Error sending reply: {str(e)}")
        return None

@app.route('/slack/events', methods=['POST'])
def slack_events():
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return "Invalid request", 403

    data = request.json
    print(f"EVENT RECEIVED: {data}")

    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    event = data.get('event', {})

    if event.get('type') == 'message' and not event.get('subtype') and 'bot_id' not in event:
        user = event.get('user')
        channel = event.get('channel')
        text = event.get('text')
        thread_ts = event.get('ts')

        # Only attempt to join if the channel is not a private channel ("group")
        if event.get('channel_type') != 'group':
            try:
                slack_client.conversations_join(channel=channel)
            except Exception as e:
                print(f"Join channel error: {e}")
        else:
            print("Skipping join for private channel.")

        try:
            user_info = slack_client.users_info(user=user)
            user_name = user_info['user']['real_name']
            email = user_info['user']['profile'].get('email', 'No email')
        except Exception as e:
            print(f"❌ Error fetching user info for {user}: {e}")
            user_name = f"<Unknown:{user}>"
            email = 'No email'

        write_to_sheet(user_name, user, text, email)

        # Optional: Reply to Slack
        if "introduce" in text.lower():
            reply = f"Sure <@{user}>, I'll help with that introduction!"
            send_reply(channel, thread_ts, reply)
        else:
            reply = f"Hi <@{user}>! I saw your intro: \"{text}\". I'll suggest some connections soon!"
            send_reply(channel, thread_ts, reply)

    return "", 200

# ---------- Additional Endpoints ----------

@app.route('/health', methods=['GET'])
def health():
    return "App is running!", 200

@app.route('/channels', methods=['GET'])
def list_channels():
    try:
        response = slack_client.conversations_list(types="public_channel,private_channel")
        channels = response.get("channels", [])
        channels_info = [{"id": ch.get("id"), "name": ch.get("name")} for ch in channels]
        return jsonify(channels_info), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
