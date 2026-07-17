# Implementation Plan: External Ratings API Integration

**Branch**: `005-ratings-api-integration` | **Date**: 2024-12-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-ratings-api-integration/spec.md`

## Summary

Add external API integration to the FIDE scraper to POST rating updates to https://chesshub.cloud/api/fide-ratings/ after each scrape operation completes. The API endpoint and authentication token will be configured via environment variables (FIDE_RATINGS_API_ENDPOINT, API_TOKEN). The integration will be resilient to external API failures, logging all requests and errors while continuing to process rating updates locally without interruption.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: requests (HTTP client, already in requirements.txt), python-dotenv (env config, already in requirements.txt)
**Storage**: File-based (CSV append-only, no database changes required)
**Testing**: pytest (existing test framework)
**Target Platform**: Linux server (Docker deployment)
**Project Type**: Single monolithic Python script (fide_scraper.py)
**Performance Goals**: <5 seconds per API POST request with 1 retry; 100% local scrape reliability regardless of API availability
**Constraints**: Must not block FIDE scraper operations; external API failure must not crash or halt processing
**Scale/Scope**: Per-player rating updates (same model as email notifications currently used)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Evaluation | Status |
|-----------|-----------|--------|
| **I. Code Quality** | New API integration code will follow existing patterns (requests library, error handling, logging) with type hints and docstrings | ✓ PASS |
| **II. Testing** | Integration will have pytest unit tests covering success/failure scenarios, config loading, and request formatting | ✓ PASS |
| **III. Simplicity** | Adds single new function `post_rating_to_api()` and integration call; no new dependencies or architectural patterns required | ✓ PASS |
| **IV. Documentation** | Code will include inline docstrings; .env.example will be updated with new variables; README updated if deployment docs exist | ✓ PASS |

**Conclusion**: Feature aligns with all constitution principles. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
fide_scraper.py                 # Main script - add post_rating_to_api() function
                                # and integrate into main batch processing flow

requirements.txt                # No changes - requests and python-dotenv already present

.env.example                    # Update with new env variables:
                                # FIDE_RATINGS_FIDE_RATINGS_API_ENDPOINT=https://chesshub.cloud/api/fide-ratings/
                                # API_TOKEN=

tests/
└── test_fide_scraper.py        # Add tests for:
                                # - test_post_rating_to_api_success()
                                # - test_post_rating_to_api_network_error()
                                # - test_post_rating_to_api_http_error()
                                # - test_load_api_config_missing_vars()
                                # - test_load_api_config_valid()
```

**Structure Decision**: Feature integrates into existing monolithic `fide_scraper.py` script following the same patterns used for email notifications (SMTP integration). No new source directories required. New function will be added to the same script with corresponding tests in existing test file.

## Complexity Tracking

> **N/A**: No violations from Constitution Check. Feature adds single focused function to existing codebase following established patterns.

---

## Phase 0: Research & Clarifications

### Clarifications Resolved

All requirements were sufficiently specified in the feature description. The following technical decisions were made based on the existing codebase:

**1. API Request Retry Strategy**
- **Decision**: Single retry on first failure only
- **Rationale**: Matches existing pattern used in email notification system; prevents cascading delays
- **Alternatives**: Exponential backoff rejected for Phase 1 (can add in Phase 2 if needed)

**2. Request Timeout Configuration**
- **Decision**: 5-second timeout per request
- **Rationale**: Reasonable for HTTP requests to known internal/managed APIs; balances responsiveness vs network variability
- **Alternatives**: Configurable timeout in future; hardcoded for initial implementation

**3. Error Logging Approach**
- **Decision**: Log all failures with full context (FIDE ID, status code, error message) to stderr via logging module
- **Rationale**: Consistent with existing email error logging; allows administrators to investigate issues
- **Alternatives**: Database logging rejected (no DB in project); external logging rejected (out of scope)

**4. Failure Mode (API Down)**
- **Decision**: Continue processing all ratings locally; log failure with player ID for later reconciliation
- **Rationale**: Local database is source of truth per spec assumption
- **Alternatives**: Queue for retry rejected (no queue infrastructure; can add in Phase 2)

---

## Phase 1: Design & Contracts

### 1. Data Model

#### RatingUpdate Entity

```yaml
RatingUpdate:
  description: "Single player rating snapshot for external API transmission"
  fields:
    date: 
      type: string (ISO 8601)
      example: "2024-12-18"
      required: true
    fide_id:
      type: string (4-10 digits)
      example: "12345678"
      required: true
    player_name:
      type: string
      example: "John Doe"
      required: true
    standard_rating:
      type: integer or null
      range: 0-4000+
      required: true (can be null if unrated)
    rapid_rating:
      type: integer or null
      range: 0-4000+
      required: true (can be null if unrated)
    blitz_rating:
      type: integer or null
      range: 0-4000+
      required: true (can be null if unrated)

  validation:
    - fide_id: must be 4-10 numeric digits (validated by validate_fide_id())
    - ratings: must be integers >= 0 or None (existing validation)
    - date: must be valid ISO 8601 date string
```

### 2. API Contracts

#### POST /api/fide-ratings/

**Request**:
```http
POST https://chesshub.cloud/api/fide-ratings/
Authorization: Token YOUR_API_TOKEN
Content-Type: application/json

{
  "date": "2024-12-18",
  "fide_id": "12345678",
  "player_name": "John Doe",
  "standard_rating": 2500,
  "rapid_rating": 2400,
  "blitz_rating": 2300
}
```

**Response (200 OK)**:
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

**Error Response (400, 401, 500, etc.)**:
```json
{
  "error": "Detail message about the error"
}
```

**Contract Details**:
- Authentication: Token-based (Authorization header)
- Content negotiation: application/json only
- Success indicator: HTTP 200 status code
- Idempotency: Not required (POST is not idempotent)
- Rate limiting: Not specified (assume no limits for first version)
- Timeout: 5 seconds per request

### 3. Function Signatures (Python)

```python
def load_api_config() -> dict:
    """
    Load API configuration from environment variables.
    
    Returns:
        dict: {'endpoint': str, 'token': str}
    
    Raises:
        ValueError: If required environment variables are missing
    
    Environment variables:
        - FIDE_RATINGS_API_ENDPOINT: Full URL to API endpoint (required)
        - API_TOKEN: Authentication token (required)
    """

def post_rating_to_api(
    profile: dict,
    api_endpoint: str,
    api_token: str,
    timeout: int = 5,
    max_retries: int = 1
) -> bool:
    """
    POST a player rating update to external API.
    
    Args:
        profile: dict with keys {
            'Date', 'FIDE ID', 'Player Name', 
            'Standard', 'Rapid', 'Blitz'
        }
        api_endpoint: Full URL to POST endpoint
        api_token: Bearer token for Authorization header
        timeout: Request timeout in seconds (default 5)
        max_retries: Number of retries on failure (default 1)
    
    Returns:
        bool: True if successful (200 OK), False if failed after retries
    
    Side effects:
        - Logs success to logging.info()
        - Logs errors to logging.error() with full context
        - Does NOT raise exceptions on API failures
    
    Handles:
        - requests.Timeout: logged as error, retries once, returns False
        - requests.ConnectionError: logged as error, retries once, returns False
        - requests.HTTPError: logged with status code, returns False
        - Unexpected response format: logged as error, returns False
    """

def should_post_to_api() -> bool:
    """
    Determine if API posting is enabled (both config vars present).
    
    Returns:
        bool: True if both FIDE_RATINGS_API_ENDPOINT and API_TOKEN are configured
    """
```

### 4. Integration Points

**Main batch processing flow** (`main()` function):
```python
# Pseudo-code showing integration:

api_config = load_api_config()  # Load at startup
api_enabled = should_post_to_api()

for profile in player_profiles:
    # ... existing rating scrape and local storage ...
    
    if api_enabled:
        post_rating_to_api(
            profile=profile,
            api_endpoint=api_config['endpoint'],
            api_token=api_config['token']
        )
    # ... continue with next player (regardless of API result) ...
```

### 5. Error Handling Strategy

**Timeout Errors**:
- Catch: `requests.Timeout`
- Log: "API request timeout for FIDE ID X after 5 seconds (attempted N retries)"
- Action: Retry once, then log as failed and continue

**Connection Errors**:
- Catch: `requests.ConnectionError`
- Log: "Failed to connect to API for FIDE ID X: {error}"
- Action: Retry once, then log as failed and continue

**HTTP Errors (4xx, 5xx)**:
- Catch: `requests.HTTPError`
- Log: "API returned {status_code} for FIDE ID X: {response_body}"
- Action: Don't retry 4xx (likely bad request); retry once on 5xx

**Unexpected Responses**:
- Invalid JSON response
- Missing required fields in response
- Log: "Unexpected response from API for FIDE ID X: {response}"
- Action: Log error and continue

### 6. Configuration

**New environment variables** (add to .env.example):
```bash
# External API Integration
FIDE_RATINGS_API_ENDPOINT=https://chesshub.cloud/api/fide-ratings/
API_TOKEN=your-api-token-here
```

**Validation**:
- Both variables must be set for API posting to be enabled
- Missing variables result in graceful skip (no API posting)
- Invalid URL format logs clear error message

---

## Phase 1 Deliverables

- [x] Updated plan.md with technical design
- [ ] research.md created with all clarifications resolved
- [ ] data-model.md with RatingUpdate entity details
- [ ] contracts/api-schema.yaml with OpenAPI specification
- [ ] quickstart.md with integration examples
- [ ] Agent context files updated (see Phase 1 step 3)

