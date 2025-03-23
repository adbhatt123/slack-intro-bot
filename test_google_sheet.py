import gspread
import os
from slack_sdk import WebClient
from google.oauth2.service_account import Credentials
from datetime import datetime

# ✅ CONFIGURATION
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = "C013KH3JS3T"  # Replace with your Slack Channel ID
SERVICE_ACCOUNT_FILE = 'service_account.json'
SHEET_NAME = "CC Intros"  # Replace with your Google Sheet name

# ✅ Initialize Slack client
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# ✅ FIXED: Correct scope for Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
sheet_client = gspread.authorize(creds)

# ✅ Open the sheet
sheet = sheet_client.open(SHEET_NAME).sheet1

# ✅ Write a row to Google Sheets
def write_to_sheet(user_name, user_id, message_text, email):
    sheet.append_row([
        user_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        message_text,
        user_id,
        email
    ])
    print(f"✅ Saved: {user_name} | Email: {email}")

# ✅ Fetch messages, resolve user info, and write to sheet if not duplicate
def fetch_and_store_intros():
    response = slack_client.conversations_history(channel=SLACK_CHANNEL_ID, limit=500)
    messages = response['messages']
    print(f"✅ Pulled {len(messages)} messages from Slack")

    # ✅ Get existing Slack User IDs from the Sheet (Column 4 = Slack User ID)
    existing_user_ids = sheet.col_values(4)  # Adjust if your user_id column changes
    print(f"✅ Existing user IDs in sheet: {existing_user_ids}")

    for msg in reversed(messages):  # oldest first
        if 'subtype' not in msg and 'user' in msg:
            user_id = msg['user']
            text = msg.get('text', '')

            if user_id in existing_user_ids:
                print(f"⚠️ Skipping duplicate user {user_id}")
                continue  # ✅ Skip duplicates

            try:
                user_info = slack_client.users_info(user=user_id)
                user_name = user_info['user']['real_name']
                email = user_info['user']['profile'].get('email', 'No email')
            except Exception as e:
                print(f"❌ Error fetching user info for {user_id}: {e}")
                user_name = f"<Unknown:{user_id}>"
                email = 'No email'

            write_to_sheet(user_name, user_id, text, email)

if __name__ == "__main__":
    fetch_and_store_intros()
