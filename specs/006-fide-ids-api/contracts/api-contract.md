# API Contract: FIDE IDs Endpoint

## Overview

This document defines the contract between the scraper and the external FIDE IDs API endpoint.

## Endpoint

**Base URL**: `https://chesshub.cloud/api/fide-ids/`

**Endpoint Path**: `/api/fide-ids/`

**Full URL**: `https://chesshub.cloud/api/fide-ids/`

**HTTP Method**: `GET`

**Description**: Retrieve a list of all FIDE IDs for active users in the system.

## Authentication

**Type**: Token-based (Bearer token in Authorization header)

**Header**: `Authorization: Token <API_TOKEN>`

**Token Source**: Environment variable `API_TOKEN`

**Example**:
```
GET https://chesshub.cloud/api/fide-ids/
Authorization: Token your_api_token_here
```

## Request

### Query Parameters
None. The endpoint returns all IDs without filtering options.

### Request Body
None. This is a GET request.

### Headers Required
```
Authorization: Token <API_TOKEN>
Accept: application/json
```

## Response

### Success Response (200 OK)

**Status Code**: `200`

**Content-Type**: `application/json`

**Body Structure**:
```json
{
  "fide_ids": [
    "12345678",
    "23456789",
    "34567890"
  ],
  "count": 3
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `fide_ids` | array[string] | Array of FIDE IDs as strings. Pre-sorted alphabetically. Pre-deduplicated to ensure each ID appears exactly once. Only includes IDs for active users with valid FIDE data. |
| `count` | integer | Total number of distinct FIDE IDs. Always equals `length(fide_ids)`. |

### Response Properties

- **Ordering**: Results are sorted alphabetically (lexicographic order)
- **Deduplication**: Server-side deduplication ensures no duplicates in response
- **Filtering**: Only active users with profiles containing valid FIDE IDs are included
- **Charset**: UTF-8

## Error Responses

### 401 Unauthorized

**Status Code**: `401`

**Trigger**: Missing or invalid `Authorization` header / `API_TOKEN`

**Response Body**:
```json
{
  "detail": "Invalid token."
}
```

**Handling**: Log error, do not retry, continue with existing players file

### 403 Forbidden

**Status Code**: `403`

**Trigger**: Token is valid but does not have permission to access this endpoint

**Response Body**:
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Handling**: Log error, do not retry, continue with existing players file

### 404 Not Found

**Status Code**: `404`

**Trigger**: Endpoint path does not exist at the specified base URL

**Response Body**: HTML or JSON error page

**Handling**: Log error with status code, do not retry, continue with existing players file

### 500 Internal Server Error

**Status Code**: `500`

**Trigger**: Server-side error processing the request

**Response Body**: JSON or HTML error page

**Handling**: Log error, consider for retry (not implemented in v1)

### Timeout

**Trigger**: Request exceeds timeout threshold (typically 30 seconds)

**Handling**: Log timeout error, do not retry in v1, continue with existing players file

### Connection Error

**Trigger**: Network unreachable, DNS resolution failure, connection refused

**Handling**: Log connection error details, do not retry, continue with existing players file

## Implementation Notes

### Timeout Configuration
- Recommend: 30-second timeout on initial implementation
- If timeout occurs, fail gracefully (do not block scraper)

### Retry Strategy
- v1: No retries on failure (simplicity principle)
- Future: Could implement exponential backoff for transient errors

### Caching
- No caching strategy in v1
- Each scraper run fetches fresh list from API

### Rate Limiting
- No explicit rate limit mentioned in API spec
- Assume reasonable limits and do not hammer endpoint
- Single fetch per scraper run (no high frequency)

### Data Validation
- Validate JSON structure before processing
- Validate that `fide_ids` contains strings
- Validate that `count` matches array length
- Log and skip if validation fails

## Example Requests

### Using curl

```bash
curl -X GET "https://chesshub.cloud/api/fide-ids/" \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Accept: application/json"
```

### Using Python requests

```python
import requests

url = "https://chesshub.cloud/api/fide-ids/"
headers = {
    "Authorization": "Token YOUR_API_TOKEN",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers, timeout=30)
response.raise_for_status()

data = response.json()
fide_ids = data["fide_ids"]
count = data["count"]
```

## Compatibility

- **API Version**: Not versioned in URL (assumes stable contract)
- **Breaking Changes**: None currently anticipated
- **Deprecation**: No deprecation strategy mentioned
