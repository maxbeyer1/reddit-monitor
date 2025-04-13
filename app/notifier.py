"""Notification service for sending alerts about posts."""
import logging
import requests
from twilio.rest import Client

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles sending notifications through various channels."""

    def __init__(self, config):
        """Initialize the notification service with configuration."""
        self.config = config
        self.twilio_client = None

        # Initialize Twilio client if enabled
        if self.config.TWILIO_ENABLED:
            try:
                self.twilio_client = Client(
                    self.config.TWILIO_ACCOUNT_SID,
                    self.config.TWILIO_AUTH_TOKEN
                )
                logger.info("Twilio client initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize Twilio client: %s", e)

    def send_notification(self, title, message, link=None):
        """Send notification through primary and potentially backup channels."""
        success = self._send_ntfy_notification(title, message, link)

        # If ntfy fails and Twilio is enabled, try SMS as backup
        if not success and self.config.TWILIO_ENABLED and self.twilio_client:
            self._send_twilio_notification(title, message, link)

        return success

    def _send_ntfy_notification(self, title, message, link=None):
        """Send notification through ntfy.sh."""
        ntfy_url = f"{self.config.NTFY_URL}/{self.config.NTFY_TOPIC}"

        headers = {
            "Title": title,
            "Priority": str(self.config.NTFY_PRIORITY),
            "Tags": self.config.NTFY_TAGS
        }

        # Add link if provided
        if link:
            headers["Click"] = link

        try:
            response = requests.post(
                ntfy_url, data=message, headers=headers, timeout=10)
            if response.status_code == 200:
                logger.info("Successfully sent ntfy notification: %s", title)
                return True
            else:
                logger.error(
                    "Failed to send ntfy notification. Status code: %s, Response: %s",
                    response.status_code, response.text)
                return False
        except Exception as e:
            logger.error("Error sending ntfy notification: %s", e)
            return False

    def _send_twilio_notification(self, title, message, link=None):
        """Send notification through Twilio SMS as a backup."""
        if not self.twilio_client:
            logger.error("Twilio client not initialized, cannot send SMS")
            return False

        # Format SMS message
        sms_message = f"{title}\n\n{message}"
        if link:
            sms_message += f"\n\nLink: {link}"

        try:
            # Attempt to send SMS
            message = self.twilio_client.messages.create(
                body=sms_message,
                from_=self.config.TWILIO_FROM_NUMBER,
                to=self.config.TWILIO_TO_NUMBER
            )
            logger.info(
                "Successfully sent Twilio SMS notification: %s", message.sid)
            return True
        except Exception as e:
            logger.error("Error sending Twilio SMS notification: %s", e)

            # Try a phone call as a last resort for truly critical alerts
            try:
                # Create a TwiML response for the call
                call = self.twilio_client.calls.create(
                    twiml=f'<Response><Say>Alert! {title}. Check your phone for details.</Say></Response>',
                    from_=self.config.TWILIO_FROM_NUMBER,
                    to=self.config.TWILIO_TO_NUMBER
                )
                logger.info(
                    "Successfully initiated Twilio voice call: %s", call.sid)
                return True
            except Exception as call_error:
                logger.error("Error making Twilio voice call: %s", call_error)
                return False
