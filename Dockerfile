FROM python:3.12-alpine

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY reddit_monitor/ /app/reddit_monitor/
COPY main.py /app/

# Create directories for data and logs
RUN mkdir -p /data /app/logs

# Run as non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
RUN chown -R appuser:appgroup /app /data
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose webhook server port
EXPOSE 5000

# Run the application
CMD ["python", "main.py"]