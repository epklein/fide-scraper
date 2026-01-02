# Quick Start Guide: External Ratings API Integration

**Feature**: 005-ratings-api-integration
**Date**: 2024-12-18

---

## Overview

This guide shows how to integrate the FIDE scraper with an external ratings API to automatically POST rating updates after each scrape.

---

## Configuration

### 1. Set Environment Variables

Add the following to your `.env` file:

```bash
# External API Integration
FIDE_RATINGS_API_ENDPOINT=https://chesshub.cloud/api/fide-ratings/
API_TOKEN=your-secret-api-token-here
```

**Where to get these values**:
- `FIDE_RATINGS_API_ENDPOINT`: The full URL to the ratings API endpoint (provided by the API service)
- `API_TOKEN`: Your authentication token for the API (provided by the API service)

### 2. Update .env.example

Keep the example file updated for documentation:

```bash
# External API Integration
FIDE_RATINGS_API_ENDPOINT=https://chesshub.cloud/api/fide-ratings/
API_TOKEN=your-api-token-here
```

---

## Usage

### Automatic Operation

Once configured, the scraper automatically POSTs rating updates to the external API:

```bash
# Single player scrape (with optional API posting if configured)
python fide_scraper.py 12345678

# Batch scrape (with optional API posting if configured)
python fide_scraper.py --batch

# Batch with email notifications and API posting
python fide_scraper.py --batch --notify
```

### API Posting Behavior

**If both `FIDE_RATINGS_API_ENDPOINT` and `API_TOKEN` are configured**:
- After each player's ratings are scraped and stored locally
- A POST request is sent to the configured API endpoint
- Success/failure is logged to stderr
- Processing continues regardless of API success/failure

**If either environment variable is missing**:
- API posting is skipped silently
- Scraper continues normally
- All ratings are stored locally as usual

### Checking Logs

Monitor the scraper logs to see API posting results:

```bash
# Run scraper with visible logging
python fide_scraper.py --batch 2>&1 | grep "API"

# Example successful log:
# INFO: API request successful for FIDE ID 12345678: 200 OK

# Example failure log:
# ERROR: API request failed for FIDE ID 87654321: HTTPError - 500 Server Error
```

---

## Request/Response Examples

### Successful Rating Update

**What gets POSTed**:
```json
{
  "date": "2024-12-18",
  "fide_id": "12345678",
  "player_name": "Alice Smith",
  "standard_rating": 2450,
  "rapid_rating": 2350,
  "blitz_rating": 2200
}
```

**What you get back** (200 OK):
```json
{
  "id": 42,
  "date": "2024-12-18",
  "fide_id": "12345678",
  "player_name": "Alice Smith",
  "standard_rating": 2450,
  "rapid_rating": 2350,
  "blitz_rating": 2200,
  "ingested_at": "2024-12-18T14:23:45.678901Z"
}
```

### Failed Rating Update

If the API is temporarily unavailable:

```
ERROR: API request failed for FIDE ID 12345678: ConnectionError - Failed to connect
ERROR: Retrying... (attempt 1 of 1)
ERROR: API request failed for FIDE ID 12345678: Connection timeout (after retry)
INFO: Continuing with next player...
```

**Result**: Rating is stored locally in `fide_ratings.csv` for later manual reconciliation.

---

## Configuration Examples

### Example 1: Development (Local Testing)

```bash
# .env for local development
FIDE_RATINGS_API_ENDPOINT=http://localhost:8000/api/fide-ratings/
API_TOKEN=dev-token-12345
```

### Example 2: Production

```bash
# .env for production deployment
FIDE_RATINGS_API_ENDPOINT=https://chesshub.cloud/api/fide-ratings/
API_TOKEN=${API_TOKEN}  # Use secret management system
```

### Example 3: Disabled

```bash
# .env with API disabled (empty token)
FIDE_RATINGS_API_ENDPOINT=
API_TOKEN=
# Results: API posting skipped, scraper works normally
```

---

## Monitoring

### Check Configuration

```python
import os
from dotenv import load_dotenv

load_dotenv()
api_endpoint = os.getenv('FIDE_RATINGS_API_ENDPOINT')
api_token = os.getenv('API_TOKEN')

if api_endpoint and api_token:
    print(f"✓ API Integration enabled: {api_endpoint}")
else:
    print("✗ API Integration disabled (missing configuration)")
```

### Check Logs for Success Rate

```bash
# Count successful API posts
grep "API request successful" scraper.log | wc -l

# Count failed API posts
grep "API request failed" scraper.log | wc -l

# Check for specific player
grep "FIDE ID 12345678" scraper.log
```

### Manual Re-send (Future Phase 2)

After Phase 1, if you need to manually re-send failed updates:

```bash
# Read failed FIDE IDs from logs
grep "API request failed" scraper.log | grep -o "FIDE ID [0-9]*" | sort -u

# Manually scrape those players to retry API posting
python fide_scraper.py 12345678  # Scrape and re-POST
```

---

## Error Handling

### API Endpoint Unreachable

**Symptom**: Multiple "ConnectionError" messages in logs

**Diagnosis**:
1. Check `FIDE_RATINGS_API_ENDPOINT` value: `grep FIDE_RATINGS_API_ENDPOINT .env`
2. Test connectivity: `curl -I https://chesshub.cloud/api/fide-ratings/`
3. Check firewall/network access

**Action**: Fix endpoint URL or network access; scraper continues unaffected

### Authentication Failed (401 Unauthorized)

**Symptom**: "401 Unauthorized" errors in logs

**Diagnosis**:
1. Check `API_TOKEN` value: `grep API_TOKEN .env`
2. Verify token with API service provider

**Action**: Update token in `.env` and restart scraper

### Server Errors (5xx)

**Symptom**: "500 Server Error" messages in logs

**Action**:
- Retry is automatic (once)
- If persistent, contact API service provider
- Ratings stored locally; can retry later

### Timeout Issues

**Symptom**: "Timeout" messages in logs

**Diagnosis**: External API may be slow or unreachable

**Action**:
- First retry is automatic
- If persistent, check network and API status
- Ratings stored locally; can retry later

---

## Testing

### Test Configuration

```bash
# Verify environment variables are loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(f'Endpoint: {os.getenv(\"FIDE_RATINGS_API_ENDPOINT\")}'); print(f'Token set: {bool(os.getenv(\"API_TOKEN\"))}')"
```

### Manual API Test (using requests)

```python
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv('FIDE_RATINGS_API_ENDPOINT')
token = os.getenv('API_TOKEN')

if not endpoint or not token:
    print("API not configured")
    exit(1)

# Test payload
payload = {
    "date": "2024-12-18",
    "fide_id": "12345678",
    "player_name": "Test Player",
    "standard_rating": 2000,
    "rapid_rating": 1900,
    "blitz_rating": 1800
}

# Send test request
try:
    response = requests.post(
        endpoint,
        json=payload,
        headers={'Authorization': f'Token {token}'},
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
```

### Unit Tests

```bash
# Run pytest with API integration tests
pytest tests/test_fide_scraper.py -k "api" -v

# Run all tests including API
pytest tests/test_fide_scraper.py -v
```

---

## Deployment

### Docker Deployment

Update `docker-compose.yaml` to include API configuration:

```yaml
services:
  fide-scraper:
    image: fide-scraper:latest
    environment:
      FIDE_RATINGS_API_ENDPOINT: ${FIDE_RATINGS_API_ENDPOINT}
      API_TOKEN: ${API_TOKEN}
    # ... rest of config
```

Run with environment variables:

```bash
export FIDE_RATINGS_API_ENDPOINT=https://chesshub.cloud/api/fide-ratings/
export API_TOKEN=your-token-here
docker-compose up
```

Or use `.env` file:

```bash
docker-compose up
# Docker automatically loads .env file
```

### Kubernetes Deployment

Store API credentials as secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: fide-api-config
type: Opaque
stringData:
  FIDE_RATINGS_API_ENDPOINT: https://chesshub.cloud/api/fide-ratings/
  API_TOKEN: your-token-here
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: fide-scraper
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: fide-scraper
            image: fide-scraper:latest
            envFrom:
            - secretRef:
                name: fide-api-config
```

---

## Integration with Email Notifications

The API integration works alongside email notifications:

```bash
# Batch scrape WITH email notifications AND API posting
python fide_scraper.py --batch --notify

# This will:
# 1. Scrape all FIDE profiles
# 2. Send email notifications to configured recipients (if enabled)
# 3. POST updates to external API (if configured)
# 4. Store all ratings locally in CSV
```

Failures in one integration don't affect the others:
- Email send fails: API posting continues
- API posting fails: Email sending continues
- Local rating storage continues regardless

---

## Troubleshooting Checklist

- [ ] Verify `FIDE_RATINGS_API_ENDPOINT` and `API_TOKEN` in `.env`
- [ ] Test connectivity: `curl -I $FIDE_RATINGS_API_ENDPOINT`
- [ ] Check logs: `grep "API" scraper.log`
- [ ] Verify token validity with API provider
- [ ] Check network/firewall access
- [ ] Confirm API is accessible from deployment environment
- [ ] Review ratings stored locally in `fide_ratings.csv` (local storage always succeeds)
