# Feature Specification: Fetch FIDE IDs from API and Augment Players File

**Feature Branch**: `006-fide-ids-api`
**Created**: 2025-12-19
**Status**: Draft
**Input**: User description: "The file with the players (FIDE_PLAYERS_FILE) list will be complemented by a list of FIDE IDs that are collected from an API endpoint (FIDE_IDS_API_ENDPOINT=https://eduklein.cloud/api/fide-ids/) that is authenticated by the same API_TOKEN. The FIDE IDs collected from the API endpoint will be appended to the csv file in FIDE_PLAYERS_FILE (deduplication needed). After that, the script works the same, with extra FIDE IDs retrieved."

## Clarifications

### Session 2025-12-19

- Q: Should FIDE IDs be treated as strings or numeric values? → A: Strings (matching API response format)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fetch FIDE IDs from API endpoint (Priority: P1)

The system retrieves a list of FIDE IDs from the configured API endpoint before starting the rating scraper. This provides an additional source of player identifiers to scrape ratings for, expanding coverage beyond the initially configured players file. An administrator can verify that new FIDE IDs were successfully retrieved by checking logs and observing the updated players file.

**Why this priority**: This is the core functionality that enables the feature. Without successfully fetching FIDE IDs from the API, the entire enhancement is non-functional. This determines which players will be scraped.

**Independent Test**: Can be fully tested by configuring the API endpoint and token, running the scraper startup sequence, and verifying that the API is called and returns FIDE IDs that are then made available for processing. Delivers the value of expanding player coverage through automated API-sourced identifiers.

**Acceptance Scenarios**:

1. **Given** valid API endpoint and authentication token are configured, **When** the scraper initializes, **Then** an HTTP GET request is sent to the FIDE_IDS_API_ENDPOINT with `Authorization: Token <API_TOKEN>` header.
2. **Given** the API returns a JSON response with `fide_ids` array and `count`, **When** the response is received, **Then** the system parses the `fide_ids` array (string values) and prepares them for processing.
3. **Given** the API returns an empty `fide_ids` array, **When** the response is processed, **Then** the system logs this condition and continues with only the existing players file.

---

### User Story 2 - Append API IDs to players file with deduplication (Priority: P1)

The system appends the FIDE IDs retrieved from the API to the existing FIDE_PLAYERS_FILE while removing duplicate entries. This ensures the players file contains a comprehensive, non-redundant list of identifiers from both sources. An administrator can examine the updated CSV file and confirm it contains all unique IDs from both the original file and the API.

**Why this priority**: This is essential for ensuring data integrity and preventing duplicate processing. Without proper deduplication, the system would waste resources scraping duplicate entries and could produce conflicting data.

**Independent Test**: Can be fully tested by providing a players file with some initial IDs, mocking the API to return a list with overlapping and new IDs, running the merge operation, and verifying that the output file contains all unique IDs with no duplicates. Delivers the value of maintaining a single source of truth for player identifiers.

**Acceptance Scenarios**:

1. **Given** the existing players CSV file contains FIDE IDs [100, 200, 300] and the API returns [200, 300, 400, 500], **When** the merge operation completes, **Then** the updated CSV contains exactly [100, 200, 300, 400, 500] in the same format as the original file.
2. **Given** the API returns FIDE IDs that already exist in the players file, **When** the merge completes, **Then** no duplicate entries are created in the CSV.
3. **Given** the CSV file has a specific format/structure (headers, columns), **When** new IDs are appended, **Then** the file structure and format are preserved exactly as before.

---

### User Story 3 - Continue scraping with expanded player list (Priority: P1)

After the players file is updated with deduplicated IDs from the API, the scraper continues its normal operation using the augmented list. This ensures the enhanced player coverage immediately benefits the rating scraping process. An administrator observes that more players are being scraped compared to previous runs.

**Why this priority**: This realizes the business value of the feature by ensuring the additional FIDE IDs from the API are actually used in the scraping process. Without this, fetched IDs would be wasted.

**Independent Test**: Can be fully tested by running a complete scraper cycle with the augmented players file and verifying that the system successfully scrapes ratings for both original and API-sourced FIDE IDs, with logs showing the expanded player count. Delivers the value of improved coverage and more comprehensive rating data collection.

**Acceptance Scenarios**:

1. **Given** the players file has been updated with API-sourced IDs, **When** the scraper main loop executes, **Then** it processes all IDs in the updated file including both original and API-sourced ones.
2. **Given** a FIDE ID from the API that was not in the original file, **When** the scraper processes it, **Then** it retrieves and stores the rating data as it would for any other ID.
3. **Given** the scraper workflow (rating API calls, data storage, external API integration), **When** processing augmented IDs, **Then** all downstream operations work identically to original IDs.

---

### Edge Cases

- What happens when the API endpoint returns malformed JSON or unexpected data structure? It is logged, but the process continues.
- How does the system handle the API returning duplicate IDs or IDs already in the players file? It doesn't include duplicates in the file.
- How does the system behave if the API request times out or returns an HTTP error (4xx, 5xx)? It loggs and the process continues.
- What happens if the API returns a very large number of IDs (thousands or more) - are there performance implications? No.
- How does the system handle if the CSV file is currently locked or in use by another process? There is no possibility as this is the only script processing the file.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load the FIDE_IDS_API_ENDPOINT URL from environment variable at startup
- **FR-002**: System MUST load the API_TOKEN from environment variable for authentication
- **FR-003**: System MUST validate that both FIDE_IDS_API_ENDPOINT and API_TOKEN are present before attempting API requests
- **FR-004**: System MUST send a GET request to the FIDE_IDS_API_ENDPOINT with `Authorization: Token <API_TOKEN>` header before scraping begins
- **FR-005**: System MUST parse the `fide_ids` array (strings) from the JSON API response
- **FR-006**: System MUST read the existing FIDE_PLAYERS_FILE and extract all current FIDE IDs
- **FR-007**: System MUST deduplicate IDs from both sources (existing file + API response) to create a unified list
- **FR-008**: System MUST preserve the original CSV format, structure, and headers when appending new IDs
- **FR-009**: System MUST append the new unique IDs to the FIDE_PLAYERS_FILE in the same format as existing entries
- **FR-010**: System MUST proceed with normal scraper operation using the updated players file after the merge completes
- **FR-011**: System MUST log the number of IDs fetched from API, IDs already in file, and final count of unique IDs after deduplication
- **FR-012**: System MUST handle API failures gracefully - if the API request fails, continue with only the existing players file (do not crash)
- **FR-013**: System MUST handle file I/O errors gracefully (missing file, permission errors, file locks) and report them clearly

### Key Entities *(include if feature involves data)*

- **FIDE ID**: A unique string identifier for a chess player in the FIDE rating system (e.g., "12345678"). Retrieved from both the local CSV file and the external API. Treated as strings in all comparison and deduplication operations.
- **Players CSV File**: A CSV file (FIDE_PLAYERS_FILE) containing at minimum a column with FIDE ID strings. Format will be determined by examining existing file structure.
- **API Response**: JSON response from FIDE_IDS_API_ENDPOINT with structure: `{ "fide_ids": ["12345678", "23456789", ...], "count": N }`. Contains alphabetically sorted, deduplicated FIDE IDs as strings for active users only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System successfully fetches FIDE IDs from the API endpoint on every scraper run (100% success rate when API is available)
- **SC-002**: Deduplication is 100% accurate - no duplicate FIDE IDs exist in the updated players file after merge
- **SC-003**: The updated players file retains all original IDs plus all new unique IDs from the API (zero loss of existing data)
- **SC-004**: The CSV file format and structure are preserved exactly after the merge (verified by file diff or structure comparison)
- **SC-005**: Scraper processes all IDs in the updated players file (both original and API-sourced) in the same run
- **SC-006**: When the API is unavailable, scraper still functions normally using only the existing players file with no crashes
- **SC-007**: Processing of API IDs and file merge completes within 10 seconds for typical workloads (100-1000 IDs) to maintain acceptable startup time
- **SC-008**: Administrator logs clearly indicate how many IDs came from each source and the final count for verification

## Assumptions

- The FIDE_IDS_API_ENDPOINT returns a JSON response with `fide_ids` array of strings and `count` integer (as documented in API spec)
- The API uses token-based authentication with Authorization header: `Authorization: Token <API_TOKEN>`
- The API returns FIDE IDs as strings (e.g., "12345678"), sorted alphabetically, with server-side deduplication of active users
- The API filters results to include only active users with valid FIDE IDs
- The existing FIDE_PLAYERS_FILE is a valid CSV with at least one column containing FIDE IDs (format to be determined by examining file structure)
- FIDE IDs will be treated as strings in all deduplication and comparison operations
- The players file will be the system's source of truth and is writeable by the scraper process
- API failure should not block scraper operation - it's an enhancement, not a critical blocker

## Out of Scope

- Bidirectional synchronization - we only fetch IDs from the API, not push back
- Incremental updates - each run fetches the full API list and re-merges
- Webhook callbacks or real-time ID updates from the API
- Batch deduplication optimizations for very large datasets (>100,000 IDs)
- Archive or history tracking of which IDs came from which source
