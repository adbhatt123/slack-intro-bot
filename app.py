from flask import Flask, request, jsonify
import os
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier

app = Flask(__name__)

slack_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
verifier = SignatureVerifier(signing_secret=os.environ['SLACK_SIGNING_SECRET'])

@app.route('/slack/events', methods=['POST'])
def slack_events():
    # ✅ Re-enable signature verification
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return "Invalid request", 403

    data = request.json
    print(f"EVENT RECEIVED: {data}")  # ✅ Log the event

    # Handle Slack URL verification challenge
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    event = data.get('event', {})
    
    # ✅ Process only user messages (filter out bot messages and joins)
    if event.get('type') == 'message' and not event.get('subtype'):
        user = event.get('user')
        channel = event.get('channel')
        text = event.get('text')

        # ✅ Ensure the bot joins the channel before posting
        try:
            slack_client.conversations_join(channel=channel)
        except Exception as e:
            print(f"Join channel error (probably already in): {e}")

        # ✅ Send a welcome message
        slack_client.chat_postMessage(
            channel=channel,
            text=f"Hi <@{user}>! I saw your intro: \"{text}\". I'll suggest some connections soon!"
        )

    return "", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
