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

# Create data and output directories for volume mounts
RUN mkdir -p /data && chmod 777 /data

# Default command: run batch processing
CMD ["python", "fide_scraper.py"]
