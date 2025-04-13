# Reddit Post Monitor

A reliable service that monitors a specific Reddit user's posts in a specific subreddit and sends notifications through multiple channels.

## Features

- Monitors a specific Reddit user's posts in a target subreddit
- Sends primary notifications via ntfy.sh
- Provides backup notifications via Twilio SMS/voice calls
- Containerized with Docker for easy deployment
- Automatic restart capabilities for high reliability
- Persistent storage to prevent duplicate notifications

## Prerequisites

- Docker and Docker Compose
- Reddit API credentials (client ID and secret)
- Twilio account (optional, for backup notifications)

## Configuration

1. Copy `.env.example` to `.env`
2. Edit `.env` to add your configuration details:
   - Reddit API credentials
   - Target username and subreddit
   - Notification preferences
   - Twilio credentials (if using backup notifications)

## Running the Service

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## Data Storage

All data is stored in the `./data` directory, which is mounted as a volume in the Docker container. This ensures that the service can remember which posts it has already seen, even if the container is restarted.

## Logs

Logs are stored in the `./logs` directory and are also mounted as a volume for persistence.
