# API Contract: External Ratings API

**Feature**: 005-ratings-api-integration
**Date**: 2024-12-18
**Endpoint**: https://chesshub.cloud/api/fide-ratings/

---

## Overview

This contract defines the exact format, headers, and behavior for POSTing FIDE player rating updates to the external ratings service.

---

## POST /api/fide-ratings/

**Purpose**: Submit a single player's FIDE rating snapshot for ingestion into the external ratings database.

**HTTP Method**: POST

**Base URL**: https://chesshub.cloud/api/fide-ratings/

**Full URL**: https://chesshub.cloud/api/fide-ratings/

**Content-Type**: application/json

---

## Request

### Headers

```
POST /api/fide-ratings/ HTTP/1.1
Host: chesshub.cloud
Authorization: Token {API_TOKEN}
Content-Type: application/json
Content-Length: {length}
User-Agent: FIDE-Scraper/1.0
```

**Header Details**:
- `Authorization`: Required. Format: `Token {value}` where {value} is the API token from environment variable API_TOKEN
- `Content-Type`: Required. Must be `application/json` (all request bodies are JSON)
- `User-Agent`: Recommended. Example: `FIDE-Scraper/1.0` or `fide-scraper/{version}`

### Body

**Format**: JSON object

**Fields** (all required):

```json
{
  "date": "2024-12-18",
  "fide_id": "12345678",
  "player_name": "John Doe",
  "standard_rating": 2500,
  "rapid_rating": 2400,
  "blitz_rating": 2300
}
```

**Field Specifications**:

| Field | Type | Length | Format | Required | Example | Notes |
|-------|------|--------|--------|----------|---------|-------|
| date | string | - | ISO 8601 YYYY-MM-DD | YES | "2024-12-18" | Must be valid date |
| fide_id | string | 4-10 | Numeric digits | YES | "12345678" | FIDE ID from profile |
| player_name | string | 1-255 | UTF-8 text | YES | "John Doe" | Player name as appears in FIDE |
| standard_rating | integer \| null | - | >= 0 | YES | 2500, null | Null if unrated |
| rapid_rating | integer \| null | - | >= 0 | YES | 2400, null | Null if unrated |
| blitz_rating | integer \| null | - | >= 0 | YES | 2300, null | Null if unrated |

**Examples**:

**Example 1: All ratings present**
```json
{
  "date": "2024-12-18",
  "fide_id": "12345678",
  "player_name": "Alice Smith",
  "standard_rating": 2700,
  "rapid_rating": 2650,
  "blitz_rating": 2600
}
```

**Example 2: One rating unrated (null)**
```json
{
  "date": "2024-12-18",
  "fide_id": "87654321",
  "player_name": "Bob Johnson",
  "standard_rating": 1800,
  "rapid_rating": 1900,
  "blitz_rating": null
}
```

**Example 3: Multiple ratings unrated**
```json
{
  "date": "2024-12-18",
  "fide_id": "11111111",
  "player_name": "Charlie Brown",
  "standard_rating": null,
  "rapid_rating": 1500,
  "blitz_rating": null
}
```

---

## Response

### Success Response (200 OK)

**Status Code**: 200

**Headers**:
```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: {length}
```

**Body**:
```json
{
  "id": 1,
  "date": "2024-12-18",
  "fide_id": "12345678",
  "player_name": "John Doe",
  "standard_rating": 2500,
  "rapid_rating": 2400,
  "blitz_rating": 2300,
  "ingested_at": "2024-12-18T11:30:45.123456Z"
}
```

**Field Details**:
- `id`: Integer record ID (assigned by API)
- `ingested_at`: ISO 8601 timestamp when record was ingested
- Other fields: Echo of request body

**Interpretation**: HTTP 200 status code indicates successful ingestion. Response body is informational; do not rely on response body for success determination.

### Error Response (4xx - Client Error)

**Status Codes**: 400, 401, 403, 404, 422

**Example 400 Bad Request**:
```json
{
  "error": "Invalid FIDE ID format: 123 (must be 4-10 digits)"
}
```

**Example 401 Unauthorized**:
```json
{
  "error": "Invalid or missing authentication token"
}
```

**Example 422 Unprocessable Entity**:
```json
{
  "error": "Player name cannot be empty"
}
```

**Interpretation**: Do not retry 4xx errors (client error, not retryable). Log error details and continue to next rating update.

### Error Response (5xx - Server Error)

**Status Codes**: 500, 502, 503, 504

**Example 500 Internal Server Error**:
```json
{
  "error": "Database connection failed"
}
```

**Interpretation**: Retry once on 5xx errors (server-side issues may be transient).

### Network Errors (No Response)

**Scenarios**:
- Connection timeout (network unreachable)
- Socket timeout (no response within 5 seconds)
- DNS resolution failure
- Connection refused

**Treatment**: Treat as retryable. Log error and retry once. If still fails, log and continue.

---

## Behavior

### Idempotency

**Not Idempotent**: POST requests are not idempotent per HTTP specification. Submitting the same request twice may result in duplicate records in the external database.

**Implication for Retry Logic**:
- Retry only on network errors and 5xx responses (where request may not have been received)
- Do not retry on successful 200 response (even if response body is malformed)
- If uncertain about whether request reached server, log and skip retry

### Rate Limiting

**Not Specified**: Current API contract does not mention rate limiting. Assume no rate limits for Phase 1.

**Future Consideration**: If API returns 429 Too Many Requests, treat as retryable error.

### Authentication

**Method**: Token-based Bearer authentication

**Header Format**: `Authorization: Token {token_value}`

**Token Source**: Environment variable `API_TOKEN`

**Failure Cases**:
- Missing Authorization header → 401 Unauthorized
- Invalid token value → 401 Unauthorized
- Expired token → 401 Unauthorized

**Treatment**: All 401 responses are non-retryable (log error, continue to next update).

### Timeout

**Client-side Timeout**: 5 seconds per request

**After Timeout**: Treat as network error, retry once.

**If Still Timing Out**: Log error and continue (don't block other updates).

---

## Implementation Checklist

### Request Construction
- [ ] Read FIDE_RATINGS_API_ENDPOINT and API_TOKEN from environment
- [ ] Validate both environment variables present
- [ ] Build JSON body with exact field names (snake_case)
- [ ] Add Authorization header with Token format
- [ ] Set Content-Type to application/json
- [ ] Set timeout to 5 seconds

### Response Handling
- [ ] Check HTTP status code first
- [ ] For 200 OK: Log success and return True
- [ ] For 4xx: Log error details and return False (no retry)
- [ ] For 5xx: Log error, retry once, return False if still fails
- [ ] For network errors: Log error, retry once, return False if still fails

### Error Logging
- [ ] Include FIDE ID in all error messages
- [ ] Include HTTP status code (if applicable)
- [ ] Include error message from response (if available)
- [ ] Include network error details (timeout, connection refused, etc.)
- [ ] Log timestamp

### Retry Logic
- [ ] Single retry on 5xx errors
- [ ] Single retry on network errors (timeout, connection)
- [ ] No retry on 4xx errors
- [ ] No retry on 200 OK (even if response malformed)
- [ ] After 1 retry failure, log and continue (don't delay)

---

## Examples

### Valid Request/Response Pair

**Request**:
```bash
curl -X POST https://chesshub.cloud/api/fide-ratings/ \
  -H "Authorization: Token my-secret-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2024-12-18",
    "fide_id": "12345678",
    "player_name": "Alice Chen",
    "standard_rating": 2450,
    "rapid_rating": 2350,
    "blitz_rating": 2200
  }' \
  --max-time 5
```

**Response** (200 OK):
```json
{
  "id": 42,
  "date": "2024-12-18",
  "fide_id": "12345678",
  "player_name": "Alice Chen",
  "standard_rating": 2450,
  "rapid_rating": 2350,
  "blitz_rating": 2200,
  "ingested_at": "2024-12-18T14:23:45.678901Z"
}
```

### Invalid Authentication

**Request** (missing token):
```bash
curl -X POST https://chesshub.cloud/api/fide-ratings/ \
  -H "Content-Type: application/json" \
  -d '{"date": "2024-12-18", "fide_id": "12345678", ...}'
```

**Response** (401 Unauthorized):
```json
{
  "error": "Authorization header required"
}
```

### Malformed Request

**Request** (invalid FIDE ID):
```bash
curl -X POST https://chesshub.cloud/api/fide-ratings/ \
  -H "Authorization: Token my-secret-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2024-12-18",
    "fide_id": "123",
    "player_name": "Bob",
    "standard_rating": 2000,
    "rapid_rating": 1900,
    "blitz_rating": 1800
  }'
```

**Response** (422 Unprocessable Entity):
```json
{
  "error": "FIDE ID must be 4-10 digits, got: 123"
}
```

---

## Testing

### Happy Path Test
- POST valid rating with all fields
- Expect 200 OK with ingested_at timestamp

### Error Handling Tests
- Invalid authentication: Expect 401 (no retry)
- Malformed data: Expect 422 (no retry)
- Server error: Expect 500 (retry once)
- Connection timeout: Expect timeout (retry once)

### Edge Cases
- Null ratings (unrated players): Should succeed
- Empty player_name: Should fail with 422
- Invalid date format: Should fail with 422
- Large ratings (>4000): Should succeed
