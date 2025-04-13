"""State manager for tracking app data."""
import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class StateManager:
    """Manages the persistent state of seen Reddit posts."""

    def __init__(self, db_path):
        """Initialize the state manager with the path to the SQLite database."""
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_db()

    def _ensure_db_directory(self):
        """Ensure the directory for the database file exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info("Created directory for database: %s", db_dir)

    def _init_db(self):
        """Initialize the database if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            # Create table for seen posts if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seen_posts (
                    post_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    subreddit TEXT NOT NULL,
                    title TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error("Error initializing database: %s", e)
            raise
        finally:
            conn.close()

    def is_post_seen(self, post_id):
        """Check if a post has already been processed."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM seen_posts WHERE post_id = ?", (post_id,))
            result = cursor.fetchone() is not None
            return result
        finally:
            conn.close()

    def mark_post_seen(self, post_id, username, subreddit, title):
        """Mark a post as processed."""
        conn = sqlite3.connect(self.db_path)
        try:
            timestamp = datetime.now().isoformat()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO seen_posts (post_id, username, subreddit, title, timestamp) VALUES (?, ?, ?, ?, ?)",
                (post_id, username, subreddit, title, timestamp)
            )
            conn.commit()
            logger.info("Marked post as seen: %s", post_id)
        except Exception as e:
            logger.error("Error marking post as seen: %s", e)
            conn.rollback()
            raise
        finally:
            conn.close()
