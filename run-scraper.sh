#!/bin/bash
# Run FIDE scraper via Docker

LOG_FILE="logs/scraper.log"

mkdir -p logs

{
    echo "=== Started at $(date) ==="
    docker-compose down 2>/dev/null || true
    docker-compose run --rm fide-scraper
    docker-compose down 2>/dev/null || true
    echo "=== Completed at $(date) ==="
} >> "$LOG_FILE" 2>&1
