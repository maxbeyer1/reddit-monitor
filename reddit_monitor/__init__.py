"""
A service that monitors Reddit for specific user activity
and sends notifications via multiple channels.
"""

from . import config
from .monitor import RedditMonitor
from .notifier import NotificationService
from .state_manager import StateManager
