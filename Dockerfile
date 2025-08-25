# Render.com Docker deployment for the Discord Music Bot
FROM python:3.11-slim

# Install system dependencies (FFmpeg is required for audio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
  && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY music_bot.py ./

# Runtime settings
ENV PYTHONUNBUFFERED=1

# Start the bot
CMD ["python", "music_bot.py"]
