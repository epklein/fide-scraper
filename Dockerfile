FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code only
COPY fide_scraper.py .

# Create .env with Docker-specific paths (for mounted volumes)
RUN echo "FIDE_PLAYERS_FILE=/data/players.csv" > .env && \
    echo "FIDE_OUTPUT_FILE=/data/fide_ratings.csv" >> .env

# Create data and output directories for volume mounts
RUN mkdir -p /data

# Set default permissions
#RUN chmod +x fide_scraper.py

# Default command: run batch processing
CMD ["python", "fide_scraper.py"]
