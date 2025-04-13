"""Webhook server for handling notification acknowledgments."""
import logging
import threading
from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)


class WebhookServer:
    """Simple Flask-based webhook server for notification acknowledgments."""

    def __init__(self, config, state_manager):
        """Initialize the webhook server."""
        self.config = config
        self.state_manager = state_manager
        self.app = Flask(__name__)
        self.server_thread = None
        self.running = False

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register Flask routes."""

        @self.app.route(self.config.WEBHOOK_PATH, methods=['GET'])
        def acknowledge():
            """Handle acknowledgment requests."""
            notification_id = request.args.get('id')
            secret = request.args.get('secret')

            # Validate the secret
            if not secret or secret != self.config.WEBHOOK_SECRET:
                logger.warning("Unauthorized webhook access attempt")
                return jsonify({"success": False, "error": "Unauthorized"}), 401

            if not notification_id:
                logger.warning("Missing notification ID in webhook request")
                return jsonify({"success": False, "error": "Missing notification ID"}), 400

            # Mark notification as acknowledged
            success = self.state_manager.mark_notification_acknowledged(
                notification_id)

            if success:
                logger.info(
                    "Successfully acknowledged notification: %s", notification_id)
                return jsonify({"success": True}), 200
            else:
                logger.warning(
                    "Failed to acknowledge notification: %s", notification_id)
                return jsonify({"success": False, "error": "Notification not found"}), 404

        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({"status": "ok"}), 200

    def start(self):
        """Start the webhook server in a separate thread."""
        if self.running:
            logger.warning("Webhook server is already running")
            return

        if not self.config.WEBHOOK_ENABLED:
            logger.info("Webhook server is disabled by configuration")
            return

        if not self.config.WEBHOOK_SECRET:
            logger.warning(
                "Webhook server secret is not set, this is insecure!")

        if not self.config.WEBHOOK_URL:
            logger.warning(
                "Webhook public URL is not configured, acknowledgment links may not work")

        def run_server():
            logger.info("Starting webhook server on %s:%s",
                        self.config.WEBHOOK_HOST, self.config.WEBHOOK_PORT)
            self.app.run(
                host=self.config.WEBHOOK_HOST,
                port=self.config.WEBHOOK_PORT,
                debug=False,  # Never run in debug mode for production
                use_reloader=False,  # Disable reloader to avoid duplicate processes
                threaded=True
            )

        self.server_thread = threading.Thread(target=run_server)
        # Make thread a daemon so it exits when main thread exits
        self.server_thread.daemon = True
        self.server_thread.start()
        self.running = True
        logger.info("Webhook server thread started")

    def stop(self):
        """Stop the webhook server."""
        if not self.running:
            return

        logger.info("Stopping webhook server")
        self.running = False
        # Flask doesn't provide a clean way to stop the server from outside
        # For this basic implementation,
        # we rely on daemon threads that will be killed when main exits
