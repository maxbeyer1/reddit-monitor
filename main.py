"""Application entry point."""
import logging
import os
from reddit_monitor import config
from reddit_monitor.monitor import RedditMonitor


def setup_logging():
    """Set up logging configuration."""
    log_level = logging.DEBUG if config.DEBUG else logging.INFO

    log_dir = '/app/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Log to console
            logging.FileHandler(f'{log_dir}/reddit_monitor.log')  # Log to file
        ]
    )


def main():
    """Main entry point for the application."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Initializing Reddit Monitor")

    try:
        # Create and run the monitor
        monitor = RedditMonitor(config)
        monitor.run()
    except Exception as e:
        logger.error("Failed to start monitor: %s", e)
        raise


if __name__ == "__main__":
    main()
