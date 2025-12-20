# Research & Findings: External Ratings API Integration

**Feature**: 005-ratings-api-integration
**Date**: 2024-12-18
**Status**: Complete - No clarifications needed

## Overview

This feature requires integrating with an external API to POST rating updates. The project is a mature Python scraper with established patterns for error handling, logging, and configuration management. All technical decisions can be made using existing project patterns as reference.

---

## Decision 1: API Request Retry Strategy

**Question**: Should we implement retry logic for failed API requests?

**Decision**: Single retry on first failure only

**Rationale**:
- Matches pattern used in existing email notification system (`send_email_notification()`)
- Prevents cascading delays when external API is temporarily unavailable
- One retry catches transient network blips without excessive retries
- Adds complexity without significant benefit for initial version

**Alternatives Considered**:
- **Exponential backoff** (3-5 retries with increasing delays)
  - Rejected: Too complex for Phase 1; can be added in Phase 2 if metrics show need
- **No retries** (fail immediately)
  - Rejected: Would miss transient failures; 1 retry is minimal safety net
- **Async queue for retry** (store failures, retry later)
  - Rejected: No queue infrastructure in project; out of scope for Phase 1

**Implementation**: Try once, wait for response. If any error (timeout, network, 5xx), retry once immediately. If still fails, log and continue.

---

## Decision 2: Request Timeout Configuration

**Question**: What timeout value should we use for API requests?

**Decision**: 5-second timeout per request

**Rationale**:
- Matches typical HTTP client pattern (requests library default behavior)
- Reasonable for modern internal/managed APIs
- Prevents indefinite hangs if network is slow
- 5 seconds allows for typical network round-trip + minimal processing
- Configurable via code constant if needed in future

**Alternatives Considered**:
- **10 seconds**: Too generous; could delay scraper unnecessarily
- **2 seconds**: Too aggressive; may timeout legitimate requests
- **Configurable via env var**: Rejected for Phase 1 (added complexity; can do later)

**Evidence from existing code**:
- Email notifications use 10-second timeout: `smtplib.SMTP(host, port, timeout=10)`
- FIDE website scraping uses 10-second timeout: `requests.get(url, timeout=10)`
- 5 seconds is reasonable middle ground for known internal API

---

## Decision 3: Error Logging Approach

**Question**: How should we log API failures for operator visibility?

**Decision**: Log all failures to stderr using Python `logging` module with full context

**Rationale**:
- Consistent with existing error logging in project (email, FIDE scrape errors)
- Python `logging` module already imported in fide_scraper.py
- Includes structured information: FIDE ID, HTTP status, error message
- Allows operators to search logs for issues and debugging
- No external dependencies required (logging is stdlib)

**Log Format Example**:
```
ERROR: API request failed for FIDE ID 12345678: ConnectionError - Failed to connect to https://eduklein.cloud/api/fide-ratings/
ERROR: API request failed for FIDE ID 87654321: HTTPError - 500 Server Error
ERROR: API request timeout for FIDE ID 11111111 after 5 seconds (attempted 1 retries)
INFO: API request successful for FIDE ID 12345678: 200 OK
```

**Alternatives Considered**:
- **Database logging**: Rejected - no DB in project; violates simplicity principle
- **External logging service** (Splunk, DataDog): Rejected - out of scope; adds infrastructure
- **Silent failures**: Rejected - no visibility for operators

---

## Decision 4: Failure Mode When External API is Down

**Question**: What should the system do if the external API is consistently unavailable?

**Decision**: Continue processing all ratings locally; log failure with player ID for later reconciliation

**Rationale**:
- Per spec assumption: "local database is the source of truth"
- FIDE scraper reliability must not depend on external service
- Ratings get stored locally in CSV; can be reconciled/re-sent later
- Administrators can see in logs which updates failed and retry manually if needed
- Simpler than queuing infrastructure

**Implementation**:
- Log each failure with context (FIDE ID, timestamp, error)
- Continue immediately to next player
- No blocking, no exceptions, no retry delay

**Alternatives Considered**:
- **Queue for later retry**: Rejected - no queue infrastructure; Phase 2 candidate
- **Halt scraper**: Rejected - violates requirement to keep scraper operational
- **Discard failed updates**: Rejected - lossy; administrators can't reconcile

---

## Decision 5: Environment Variable Configuration

**Question**: How should the API endpoint and token be configured?

**Decision**: Two environment variables: `FIDE_RATINGS_API_ENDPOINT` and `API_TOKEN`

**Rationale**:
- Consistent with existing pattern in project (SMTP config via env vars)
- Matches industry best practice: secrets in environment, not code
- Already using python-dotenv for configuration
- Clear separation: endpoint (infrastructure) and token (secret)
- Specific endpoint name allows for future expansion to other endpoints

**Implementation**:
```python
FIDE_RATINGS_API_ENDPOINT = os.getenv('FIDE_RATINGS_API_ENDPOINT')
API_TOKEN = os.getenv('API_TOKEN')

# If both present, enable API posting
# If either missing, skip API posting with log message
```

**Alternatives Considered**:
- **Single combined var** `API_CONFIG=<endpoint>:<token>`: Rejected - less clear
- **Config file**: Rejected - environment vars are project standard
- **Hardcoded endpoint, only token configurable**: Rejected - less flexible

---

## Decision 6: Request Body Format and Headers

**Question**: What format should we use for API request body and headers?

**Decision**: JSON body with Token-based Authorization header

**Rationale**:
- Specified in user requirements (exact format provided)
- Token authentication: `Authorization: Token YOUR_API_TOKEN`
- Content-Type: `application/json`
- Matches modern REST API conventions

**Request Structure**:
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

**Headers**:
```
Authorization: Token {api_token}
Content-Type: application/json
```

**No Alternatives**: User provided exact API contract; no research needed.

---

## Decision 7: Success Indicator

**Question**: What HTTP status code indicates successful API request?

**Decision**: HTTP 200 OK only

**Rationale**:
- Specified in user requirements (200 OK is success)
- 201 Created or 202 Accepted not expected by this API
- Treat anything else (4xx, 5xx, 3xx) as error

**Implementation**:
```python
response.raise_for_status()  # Raises HTTPError for non-2xx
if response.status_code == 200:
    return True
```

**Response Validation**:
- Check status code
- Optionally parse response JSON (per spec, includes ingested_at timestamp)
- Don't rely on response body for success (status code is authoritative)

---

## Decision 8: Dependencies

**Question**: Do we need any new Python packages?

**Decision**: No new dependencies required

**Rationale**:
- `requests` library already in requirements.txt (used for FIDE scraping)
- `python-dotenv` already in requirements.txt (used for config)
- `logging` is Python standard library
- No need for specialized HTTP or retry libraries

**Verification**: Current requirements.txt includes:
```
requests>=2.31.0          # HTTP client (✓ needed)
beautifulsoup4>=4.12.0    # HTML parsing (not used for this feature)
python-dotenv>=1.0.0      # Env vars (✓ needed)
```

---

## Summary of All Decisions

| Area | Decision | Confidence |
|------|----------|-----------|
| Retry strategy | Single retry only | HIGH - matches existing patterns |
| Timeout | 5 seconds | HIGH - reasonable default |
| Logging | stderr via logging module | HIGH - consistent with codebase |
| Failure mode | Continue locally, log failures | HIGH - per spec assumption |
| Configuration | FIDE_RATINGS_API_ENDPOINT + API_TOKEN env vars | HIGH - consistent pattern |
| Request format | JSON + Token auth header | HIGH - user-specified |
| Success indicator | HTTP 200 only | HIGH - user-specified |
| Dependencies | None new (use existing) | HIGH - verified in requirements.txt |

---

## Next Steps

All research complete. Ready for Phase 1 design and contract generation:
- ✓ No [NEEDS CLARIFICATION] markers
- ✓ All technical decisions made
- ✓ Dependencies verified
- ✓ Integration points identified
- ✓ Error handling strategy defined

Proceed to create:
1. data-model.md
2. contracts/api-schema.yaml (OpenAPI spec)
3. quickstart.md
4. Update agent context
