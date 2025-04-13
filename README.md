# Reddit Post Monitor

A reliable service that monitors a specific Reddit user's posts in a specific subreddit and sends notifications through multiple channels.

## Features

- Monitors a specific Reddit user's posts in a target subreddit
- Sends primary notifications via ntfy.sh
- Provides backup notifications via Twilio SMS/voice calls
- Notification acknowledgment system with fallback to SMS/voice if not acknowledged
- Containerized with Docker for easy deployment
- Automatic restart capabilities for high reliability
- Persistent storage to prevent duplicate notifications

## Prerequisites

- Docker and Docker Compose
- Reddit API credentials (client ID and secret)
- Twilio account (optional, for backup notifications)
- A publicly accessible URL for the webhook server (for notification acknowledgments)

## Configuration

1. Copy `.env.example` to `.env`
2. Edit `.env` to add your configuration details:
   - Reddit API credentials
   - Target username and subreddit
   - Notification preferences
   - Twilio credentials (if using backup notifications)
   - Webhook configuration (for acknowledgment system):
     - `WEBHOOK_ENABLED`: Set to `true` to enable the acknowledgment system
     - `WEBHOOK_URL`: Public URL that can reach your server (e.g., `https://example.com`)
     - `WEBHOOK_SECRET`: Secret key for validating webhook requests
     - `WEBHOOK_PORT`: Port for the webhook server (default: 5000)
     - `NOTIFICATION_FOLLOWUP_MINUTES`: Time in minutes before sending a followup (default: 3)

## Running the Service

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## Notification Acknowledgment System

The service now includes an acknowledgment system for notifications:

1. When a new post is detected, a notification is sent via ntfy.sh with an "Acknowledge" button
2. If the notification is not acknowledged within the configured time (default: 3 minutes), a voice call and/or SMS is automatically sent as a fallback
3. This ensures you never miss important notifications, while avoiding unnecessary calls when you're already aware

This feature requires:
- A publicly accessible URL where your server can be reached (`WEBHOOK_URL`)
- The webhook port (5000 by default) to be exposed to the internet
- A secret key to prevent unauthorized acknowledgments (`WEBHOOK_SECRET`)

## Data Storage

All data is stored in the `./data` directory, which is mounted as a volume in the Docker container. This ensures that the service can remember which posts it has already seen, even if the container is restarted.

## Logs

Logs are stored in the `./logs` directory and are also mounted as a volume for persistence.
