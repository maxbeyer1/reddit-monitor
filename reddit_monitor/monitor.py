"""Main monitoring service for Reddit posts."""
import time
import logging
import traceback
import signal
from datetime import datetime
import praw

from .state_manager import StateManager
from .notifier import NotificationService
from .webhook import WebhookServer

logger = logging.getLogger(__name__)


class RedditMonitor:
    """Main class for monitoring Reddit posts from a specific user in a specific subreddit."""

    def __init__(self, config):
        """Initialize the monitor with configuration."""
        self.config = config
        self.running = False
        self.setup_signal_handlers()

        # Initialize services
        self.state_manager = StateManager(config.DATABASE_PATH)
        self.notifier = NotificationService(config, self.state_manager)
        
        # Initialize webhook server if enabled
        self.webhook_server = None
        if config.WEBHOOK_ENABLED:
            self.webhook_server = WebhookServer(config, self.state_manager)

        # Initialize Reddit client
        self.reddit = self._setup_reddit_client()

        # Validate required configuration
        self._validate_config()

    def _setup_reddit_client(self):
        """Initialize the Reddit API client."""
        try:
            reddit = praw.Reddit(
                client_id=self.config.REDDIT_CLIENT_ID,
                client_secret=self.config.REDDIT_CLIENT_SECRET,
                user_agent=self.config.REDDIT_USER_AGENT
            )
            logger.info("Reddit client initialized successfully")
            return reddit
        except Exception as e:
            logger.error("Failed to initialize Reddit client: %s", e)
            raise

    def _validate_config(self):
        """Validate that all required configuration is present."""
        missing_vars = []

        # Check Reddit API credentials
        if not self.config.REDDIT_CLIENT_ID:
            missing_vars.append("REDDIT_CLIENT_ID")
        if not self.config.REDDIT_CLIENT_SECRET:
            missing_vars.append("REDDIT_CLIENT_SECRET")

        # Check target monitoring parameters
        if not self.config.TARGET_USERNAME:
            missing_vars.append("TARGET_USERNAME")
        if not self.config.TARGET_SUBREDDITS:
            missing_vars.append("TARGET_SUBREDDIT")
            
        # Check webhook configuration if enabled
        if self.config.WEBHOOK_ENABLED and not self.config.WEBHOOK_URL:
            logger.warning("WEBHOOK_URL is not set but webhook is enabled - acknowledgment links will not work properly")
            
        if self.config.WEBHOOK_ENABLED and not self.config.WEBHOOK_SECRET:
            logger.warning("WEBHOOK_SECRET is not set - this is a security risk")

        if missing_vars:
            error_msg = f"Missing required configuration variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        # pylint: disable=unused-argument
        def signal_handler(sig, frame):
            logger.info("Received signal %s, shutting down gracefully...", sig)
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def check_for_new_posts(self):
        """Check for new posts from the target user in the monitored subreddits."""
        try:
            for subreddit_name in self.config.TARGET_SUBREDDITS:
                # Get the subreddit
                subreddit = self.reddit.subreddit(subreddit_name)

                # Get new submissions from the subreddit
                # Limit to recent posts to avoid excessive API usage
                for submission in subreddit.new(limit=10):
                    # Check if this post is from our target user
                    if submission.author and submission.author.name.lower() == self.config.TARGET_USERNAME.lower():
                        post_id = submission.id

                        # Skip if we've already seen this post
                        if self.state_manager.is_post_seen(post_id):
                            continue

                        # Construct notification message
                        title = f"New Reddit Post by u/{submission.author.name}"
                        message = (
                            f"Post in r/{submission.subreddit.display_name}: {submission.title}\n\n"
                            f"Posted at: {datetime.fromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                        )
                        link = f"https://www.reddit.com{submission.permalink}"

                        # Mark the post as seen first to avoid duplicate processing
                        self.state_manager.mark_post_seen(
                            post_id,
                            submission.author.name,
                            submission.subreddit.display_name,
                            submission.title
                        )
                        
                        # Send the notification with the post_id for acknowledgment tracking
                        notification_sent = self.notifier.send_notification(
                            title, message, link, post_id)

                        logger.info(
                            "Detected new post by target user in r/%s: %s", subreddit_name, post_id)

                        # Return if successful to avoid processing multiple posts in a single loop
                        if notification_sent:
                            return notification_sent

            # No new posts found
            return True

        except Exception as e:
            logger.error("Error checking for new posts: %s", e)
            logger.debug(traceback.format_exc())
            return False

    def run(self):
        """Start the monitoring loop."""
        logger.info(
            "Starting Reddit monitor for u/%s in subreddits: %s", 
            self.config.TARGET_USERNAME, 
            ", ".join([f"r/{sub}" for sub in self.config.TARGET_SUBREDDITS]))
        self.running = True
        
        # Start the webhook server if enabled
        if self.webhook_server and self.config.WEBHOOK_ENABLED:
            self.webhook_server.start()
            logger.info("Webhook server started")
        
        # Start the notification followup thread
        if self.config.WEBHOOK_ENABLED and self.config.TWILIO_ENABLED:
            self.notifier.start_followup_thread()
            logger.info("Notification followup thread started")

        while self.running:
            try:
                self.check_for_new_posts()

                # Sleep for the configured interval
                time.sleep(self.config.POLLING_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                self.running = False
            except Exception as e:
                logger.error("Unhandled exception in monitoring loop: %s", e)
                logger.debug(traceback.format_exc())

                # Sleep to avoid hammering the API in case of persistent errors
                time.sleep(10)
        
        # Stop the notification followup thread
        if self.notifier:
            self.notifier.stop_followup_thread()
            
        # There's no clean way to stop the Flask server in this implementation
        # In a production environment, you'd use a proper WSGI server with shutdown capabilities

        logger.info("Reddit monitor stopped")
