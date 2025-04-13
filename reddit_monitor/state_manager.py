"""State manager for tracking app data."""
import sqlite3
import os
import logging
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StateManager:
    """Manages the persistent state of seen Reddit posts and pending notifications."""

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
            
            # Create table for pending notifications
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_notifications (
                    notification_id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    link TEXT,
                    created_at TEXT NOT NULL,
                    acknowledged INTEGER DEFAULT 0,
                    FOREIGN KEY (post_id) REFERENCES seen_posts(post_id)
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
            
    def create_pending_notification(self, post_id, title, message, link=None):
        """Create a pending notification record and return its ID."""
        conn = sqlite3.connect(self.db_path)
        try:
            notification_id = str(uuid.uuid4())
            created_at = datetime.now().isoformat()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO pending_notifications 
                (notification_id, post_id, title, message, link, created_at, acknowledged) 
                VALUES (?, ?, ?, ?, ?, ?, 0)""",
                (notification_id, post_id, title, message, link, created_at)
            )
            conn.commit()
            logger.info("Created pending notification: %s for post: %s", notification_id, post_id)
            return notification_id
        except Exception as e:
            logger.error("Error creating pending notification: %s", e)
            conn.rollback()
            raise
        finally:
            conn.close()
            
    def mark_notification_acknowledged(self, notification_id):
        """Mark a notification as acknowledged."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE pending_notifications SET acknowledged = 1 WHERE notification_id = ?",
                (notification_id,)
            )
            affected_rows = cursor.rowcount
            conn.commit()
            if affected_rows > 0:
                logger.info("Marked notification as acknowledged: %s", notification_id)
                return True
            else:
                logger.warning("No notification found with ID: %s", notification_id)
                return False
        except Exception as e:
            logger.error("Error marking notification as acknowledged: %s", e)
            conn.rollback()
            return False
        finally:
            conn.close()
            
    def get_pending_notifications_needing_followup(self, minutes=3):
        """Get notifications that are pending and older than specified minutes."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cutoff_time = (datetime.now() - timedelta(minutes=minutes)).isoformat()
            cursor.execute(
                """SELECT notification_id, post_id, title, message, link 
                FROM pending_notifications 
                WHERE acknowledged = 0 AND created_at < ?""",
                (cutoff_time,)
            )
            results = cursor.fetchall()
            pending_notifications = []
            for row in results:
                pending_notifications.append({
                    'notification_id': row[0],
                    'post_id': row[1],
                    'title': row[2],
                    'message': row[3],
                    'link': row[4]
                })
            return pending_notifications
        except Exception as e:
            logger.error("Error getting pending notifications: %s", e)
            return []
        finally:
            conn.close()
