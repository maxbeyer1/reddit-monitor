"""Configuration settings module."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Reddit API credentials
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "RedditMonitor/1.0")
# Target Reddit entities to monitor
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TARGET_SUBREDDIT = os.environ.get("TARGET_SUBREDDIT")
# Polling interval in seconds
POLLING_INTERVAL = int(os.environ.get("POLLING_INTERVAL", "60"))

# Primary notification (ntfy.sh)
NTFY_URL = os.environ.get("NTFY_URL", "https://notify.maxbeyer.dev")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "reddit-monitor")
NTFY_PRIORITY = int(os.environ.get("NTFY_PRIORITY", "5")
                    )  # Urgent priority by default
NTFY_TAGS = os.environ.get("NTFY_TAGS", "red_circle,warning")
NTFY_USERNAME = os.environ.get("NTFY_USERNAME")
NTFY_PASSWORD = os.environ.get("NTFY_PASSWORD")

# Backup notification (Twilio)
TWILIO_ENABLED = os.environ.get("TWILIO_ENABLED", "true").lower() == "true"
TWILIO_VOICE_ENABLED = os.environ.get(
    "TWILIO_VOICE_ENABLED", "true").lower() == "true"
TWILIO_SMS_ENABLED = os.environ.get(
    "TWILIO_SMS_ENABLED", "false").lower() == "true"
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")
TWILIO_TO_NUMBER = os.environ.get("TWILIO_TO_NUMBER")

# State management
DATABASE_PATH = os.environ.get("DATABASE_PATH", "/data/seen_posts.db")

# Acknowledgment webhook server
WEBHOOK_ENABLED = os.environ.get("WEBHOOK_ENABLED", "true").lower() == "true"
WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "0.0.0.0")  # Listen on all interfaces by default
WEBHOOK_PORT = int(os.environ.get("WEBHOOK_PORT", "5000"))
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/acknowledge")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")  # Secret key for webhook authentication
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # Public URL for callbacks (must be set in .env)
NOTIFICATION_FOLLOWUP_MINUTES = int(os.environ.get("NOTIFICATION_FOLLOWUP_MINUTES", "3"))

# Debugging
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
