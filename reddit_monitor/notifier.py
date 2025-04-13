"""Notification service for sending alerts about posts."""
import logging
import base64
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
            "Tags": self.config.NTFY_TAGS,
        }

        # Add link if provided
        if link:
            headers["Click"] = link

        # Add authentication if credentials are provided
        if self.config.NTFY_USERNAME and self.config.NTFY_PASSWORD:
            auth_str = f"{self.config.NTFY_USERNAME}:{self.config.NTFY_PASSWORD}"
            encoded_auth = base64.b64encode(auth_str.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_auth}"
            logger.debug("Added Basic authentication to ntfy request")

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
        """Send notification through Twilio voice and SMS as a backup."""
        if not self.twilio_client:
            logger.error("Twilio client not initialized, cannot send SMS")
            return False

        success = False

        # Voice call is now the primary backup notification method
        if self.config.TWILIO_VOICE_ENABLED:
            try:
                # Create a TwiML response for the call
                # Create a more detailed voice message that includes key info
                voice_message = f"Alert! New Reddit post detected by {self.config.TARGET_USERNAME} in {self.config.TARGET_SUBREDDIT}. {title}."

                call = self.twilio_client.calls.create(
                    twiml=f'<Response><Say>{voice_message}</Say><Pause length="1"/><Say>Check notifications for details.</Say></Response>',
                    from_=self.config.TWILIO_FROM_NUMBER,
                    to=self.config.TWILIO_TO_NUMBER
                )
                logger.info(
                    "Successfully initiated Twilio voice call: %s", call.sid)
                success = True
            except Exception as call_error:
                logger.error("Error making Twilio voice call: %s", call_error)

        # Still attempt SMS if enabled, but don't make overall success dependent on it
        # SMS messages will be held until verification is complete
        if self.config.TWILIO_SMS_ENABLED:
            # Format SMS message
            sms_message = f"{title}\n\n{message}"
            if link:
                sms_message += f"\n\nLink: {link}"

            try:
                # Attempt to send SMS
                sms = self.twilio_client.messages.create(
                    body=sms_message,
                    from_=self.config.TWILIO_FROM_NUMBER,
                    to=self.config.TWILIO_TO_NUMBER
                )
                logger.info(
                    "Successfully sent Twilio SMS notification: %s", sms.sid)
                # Don't set success=True here since we're treating SMS as secondary
            except Exception as e:
                logger.error(
                    "Error sending Twilio SMS notification (expected if not verified): %s", e)
                # We don't consider this a failure since SMS is secondary

        return success
