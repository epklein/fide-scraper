#!/bin/bash
# Minimal cron setup - adds run-scraper.sh to crontab
# Runs every 2 hours: 0 */2 * * * /app/run-scraper.sh

SCRIPT_PATH="/app/run-scraper.sh"
CRON_JOB="0 */2 * * * $SCRIPT_PATH"

# Add to crontab if not already present
(crontab -l 2>/dev/null || true; echo "$CRON_JOB") | crontab -

echo "✓ Cron job added: $CRON_JOB"
