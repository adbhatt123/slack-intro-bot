from flask import Flask, request, jsonify
import os
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier

app = Flask(__name__)

slack_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
verifier = SignatureVerifier(signing_secret=os.environ['SLACK_SIGNING_SECRET'])

@app.route('/slack/events', methods=['POST'])
def slack_events():
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return "Invalid request", 403

    data = request.json
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    if data.get('event', {}).get('type') == 'message':
        user = data['event'].get('user')
        channel = data['event'].get('channel')
        text = data['event'].get('text')
        # Example - simple response, later you'll plug in matching logic
        slack_client.chat_postMessage(channel=channel, text=f"Hi <@{user}>! Welcome! I'll suggest some connections soon.")
    return "", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
