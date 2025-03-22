from flask import Flask, request, jsonify
import os
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier

app = Flask(__name__)

slack_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
verifier = SignatureVerifier(signing_secret=os.environ['SLACK_SIGNING_SECRET'])

def send_reply(channel, thread_ts, message):
    """Send a reply in a thread."""
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
    # ✅ Re-enable signature verification
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return "Invalid request", 403

    data = request.json
    print(f"EVENT RECEIVED: {data}")  # ✅ Log the event

    # Handle Slack URL verification challenge
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    event = data.get('event', {})
    
    # ✅ Prevent bot loops by ignoring any event that has 'bot_id'
    if event.get('type') == 'message' and not event.get('subtype') and 'bot_id' not in event:
        user = event.get('user')
        channel = event.get('channel')
        text = event.get('text')
        thread_ts = event.get('ts')  # Get the timestamp of the original message

        # ✅ Ensure the bot joins the channel before posting
        try:
            slack_client.conversations_join(channel=channel)
        except Exception as e:
            print(f"Join channel error (probably already in): {e}")

        # ✅ Send a welcome message
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
