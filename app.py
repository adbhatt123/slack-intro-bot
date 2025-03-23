from flask import Flask, request, jsonify
import os
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

app = Flask(__name__)

# ✅ Slack Setup
slack_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
verifier = SignatureVerifier(signing_secret=os.environ['SLACK_SIGNING_SECRET'])

# ✅ Google Sheets Setup
SERVICE_ACCOUNT_FILE = 'service_account.json'
SHEET_NAME = "CC Intros"  # Your Google Sheet name
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
sheet_client = gspread.authorize(creds)
sheet = sheet_client.open(SHEET_NAME).sheet1

# ✅ Write to Google Sheet
def write_intro_to_sheet(user_name, user_id, message_text, email):
    sheet.append_row([
        user_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        message_text,
        user_id,
        email
    ])
    print(f"✅ Saved to Google Sheet: {user_name} | Email: {email}")

# ✅ Optional Slack Reply Function (can delete if not needed)
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
    # ✅ Verify Slack signature
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return "Invalid request", 403

    data = request.json
    print(f"EVENT RECEIVED: {data}")

    # ✅ Handle Slack URL verification
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    event = data.get('event', {})

    # ✅ Process only clean user messages
    if event.get('type') == 'message' and not event.get('subtype') and 'bot_id' not in event:
        user = event.get('user')
        channel = event.get('channel')
        text = event.get('text')
        thread_ts = event.get('ts')

        # ✅ Ensure the bot joins the channel (safe fallback)
        try:
            slack_client.conversations_join(channel=channel)
        except Exception as e:
            print(f"Join channel error (probably already in): {e}")

        # ✅ Fetch Slack user info (real name and email)
        try:
            user_info = slack_client.users_info(user=user)
            user_name = user_info['user']['real_name']
            email = user_info['user']['profile'].get('email', 'No email')
        except Exception as e:
            print(f"❌ Error fetching user info for {user}: {e}")
            user_name = f"<Unknown:{user}>"
            email = 'No email'

        # ✅ Immediately write to Google Sheet
        write_intro_to_sheet(user_name, user, text, email)

        # ✅ Optional: Reply to Slack (remove if not needed)
        if "introduce" in text.lower():
            reply = f"Sure <@{user}>, I'll help with that introduction!"
            send_reply(channel, thread_ts, reply)
        else:
            reply = f"Hi <@{user}>! I saw your intro: \"{text}\". I'll suggest some connections soon!"
            send_reply(channel, thread_ts, reply)

    return "", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
