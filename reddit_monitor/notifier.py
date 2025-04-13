"""Notification service for sending alerts about posts."""
import logging
import base64
import requests
import time
import threading
from twilio.rest import Client

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles sending notifications through various channels."""

    def __init__(self, config, state_manager=None):
        """Initialize the notification service with configuration."""
        self.config = config
        self.state_manager = state_manager
        self.twilio_client = None
        self.running = False
        self.followup_thread = None

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

    def send_notification(self, title, message, link=None, post_id=None):
        """Send notification through primary and potentially backup channels."""
        notification_id = None

        # If state_manager and post_id are provided, create a pending notification
        if self.state_manager and post_id:
            notification_id = self.state_manager.create_pending_notification(
                post_id, title, message, link)
            logger.info("Created pending notification %s for post %s",
                        notification_id, post_id)

        # Send ntfy notification
        success = self._send_ntfy_notification(
            title, message, link, notification_id)

        # If ntfy fails and Twilio is enabled, try Twilio as immediate backup
        if not success and self.config.TWILIO_ENABLED and self.twilio_client:
            self._send_twilio_notification(title, message, link)

            # If we had created a pending notification, mark it as acknowledged
            # since we've already sent the backup notification
            if notification_id:
                self.state_manager.mark_notification_acknowledged(
                    notification_id)

        return success

    def _send_ntfy_notification(self, title, message, link=None, notification_id=None):
        """Send notification through ntfy.sh with optional acknowledgment."""
        ntfy_url = f"{self.config.NTFY_URL}/{self.config.NTFY_TOPIC}"

        headers = {
            "Title": title,
            "Priority": str(self.config.NTFY_PRIORITY),
            "Tags": self.config.NTFY_TAGS,
        }

        # Add click action - either the original link or our acknowledgment URL
        if self.config.WEBHOOK_ENABLED and notification_id and self.config.WEBHOOK_URL:
            # Add actions for acknowledgment
            ack_url = f"{self.config.WEBHOOK_URL}{self.config.WEBHOOK_PATH}?id={notification_id}&secret={self.config.WEBHOOK_SECRET}"

            # If there's an original link, add both actions
            if link:
                headers["Actions"] = f"view, View Post, {link}; view, Acknowledge, {ack_url}, clear=true"
                # Still set the primary click to the original link for convenience
                headers["Click"] = link
            else:
                # Just set the acknowledgment as the click action
                headers["Click"] = ack_url
                headers["Actions"] = f"view, Acknowledge, {ack_url}, clear=true"

            # Add a note about acknowledgment to the message
            message = f"{message}\n\nPlease acknowledge this notification within {self.config.NOTIFICATION_FOLLOWUP_MINUTES} minutes to prevent a phone alert."
        elif link:
            # Just use the original link if no acknowledgment
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

    def start_followup_thread(self):
        """Start a background thread to check for unacknowledged notifications."""
        if not self.state_manager or not self.config.TWILIO_ENABLED:
            logger.info(
                "Notification followup is disabled - missing state manager or Twilio is disabled")
            return False

        if self.running:
            logger.warning("Followup thread is already running")
            return False

        def check_for_pending_notifications():
            logger.info("Starting notification followup thread")
            self.running = True

            while self.running:
                try:
                    # Check for notifications older than the configured timeout
                    pending = self.state_manager.get_pending_notifications_needing_followup(
                        minutes=self.config.NOTIFICATION_FOLLOWUP_MINUTES)

                    for notification in pending:
                        logger.info("Found unacknowledged notification: %s",
                                    notification['notification_id'])

                        # Send Twilio notification as followup
                        self._send_twilio_notification(
                            notification['title'],
                            f"{notification['message']}\n\n(This is a followup because the original notification was not acknowledged.)",
                            notification['link']
                        )

                        # Mark as acknowledged since we've sent the followup
                        self.state_manager.mark_notification_acknowledged(
                            notification['notification_id'])

                    # Sleep for a minute between checks
                    time.sleep(60)
                except Exception as e:
                    logger.error(
                        "Error in notification followup thread: %s", e)
                    time.sleep(60)  # Sleep on error to avoid rapid retries

            logger.info("Notification followup thread stopped")

        self.followup_thread = threading.Thread(
            target=check_for_pending_notifications)
        self.followup_thread.daemon = True
        self.followup_thread.start()
        return True

    def stop_followup_thread(self):
        """Stop the followup thread."""
        if not self.running:
            return

        logger.info("Stopping notification followup thread")
        self.running = False
        # Thread will exit on next loop check
