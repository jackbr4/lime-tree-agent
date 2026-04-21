"""
webhook.py — On-demand agent trigger via HTTP webhook

Runs a lightweight Flask server that listens for POST requests
from Home Assistant. When a valid request is received, it runs
the agent and returns the briefing.

Start manually:  python webhook.py
Started on deploy via the GitHub Actions workflow.
"""
import os
import threading
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN")
if not WEBHOOK_TOKEN:
    raise ValueError("WEBHOOK_TOKEN is not set in .env")


def run_agent_background():
    """
    Run the agent in a background thread so the webhook
    returns immediately without waiting for the full run.
    """
    try:
        from agent import run_agent, deliver_briefing
        briefing = run_agent()
        deliver_briefing(briefing)
        print("On-demand agent run complete.")
    except Exception as e:
        print(f"On-demand agent run failed: {e}")


@app.route("/lime-tree-webhook", methods=["POST"])
def webhook():
    """
    Trigger an on-demand agent run.

    Expects a POST request with:
    - Header: X-Webhook-Token: <your token>

    Returns 200 immediately and runs the agent in the background.
    Returns 401 if the token is missing or wrong.
    """
    token = request.headers.get("X-Webhook-Token", "")

    if token != WEBHOOK_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

    # Run agent in background thread so we return 200 immediately
    # HA doesn't need to wait for the full agent run to complete
    thread = threading.Thread(target=run_agent_background)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "Agent run triggered"}), 200


@app.route("/lime-tree-webhook/health", methods=["GET"])
def health():
    """Simple health check endpoint — no auth required."""
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.getenv("WEBHOOK_PORT", 8900))
    print(f"Starting webhook server on port {port}...")
    app.run(host="127.0.0.1", port=port)
