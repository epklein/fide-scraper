#!/bin/bash
# Run FIDE scraper via Docker

LOG_FILE="logs/scraper.log"

mkdir -p logs

{
    echo "=== Script started at $(date) ==="
    echo ""
    docker run --rm --env-file .env -v /root/data:/data -v /root/output:/output fide-scraper-fide-scraper:latest
    echo ""
    echo "=== Finished exec at $(date) ==="
    echo ""
} >> "$LOG_FILE" 2>&1