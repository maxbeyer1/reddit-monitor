"""Main monitoring service for Reddit posts."""
import time
import logging
import traceback
import signal
from datetime import datetime
import praw

from .state_manager import StateManager
from .notifier import NotificationService

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
        self.notifier = NotificationService(config)

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
        if not self.config.TARGET_SUBREDDIT:
            missing_vars.append("TARGET_SUBREDDIT")

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
        """Check for new posts from the target user in the target subreddit."""
        try:
            # Get the subreddit
            subreddit = self.reddit.subreddit(self.config.TARGET_SUBREDDIT)

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

                    # Send the notification
                    notification_sent = self.notifier.send_notification(
                        title, message, link)

                    # Mark as seen regardless of notification success to avoid duplicate attempts
                    self.state_manager.mark_post_seen(
                        post_id,
                        submission.author.name,
                        submission.subreddit.display_name,
                        submission.title
                    )

                    logger.info(
                        "Detected new post by target user: %s", post_id)

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
            "Starting Reddit monitor for u/%s in r/%s", {self.config.TARGET_USERNAME}, {self.config.TARGET_SUBREDDIT})
        self.running = True

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

        logger.info("Reddit monitor stopped")
