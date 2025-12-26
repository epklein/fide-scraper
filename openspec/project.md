# Project Context

## Purpose

FIDE Scraper is a Python-based batch processing tool that automatically retrieves and tracks chess player ratings from the FIDE (Confederação Brasileira de Xadrez) website. The project maintains historical rating records, sends email notifications when player ratings change, and integrates with external APIs for fetching player IDs and posting rating updates. It's designed for headless/scheduled execution via cron jobs and containerized deployment.

**Key Goals**:
- Automate daily collection of chess player rating data
- Maintain historical rating trends across Standard, Rapid, and Blitz formats
- Notify stakeholders of significant rating changes via email
- Integrate with external systems for player data synchronization
- Enable reliable, error-tolerant batch processing with comprehensive logging

## Tech Stack

- **Language**: Python 3.11+
- **HTTP Requests**: `requests` (>=2.31.0)
- **HTML Parsing**: BeautifulSoup4 (>=4.12.0)
- **Configuration**: python-dotenv (>=1.0.0)
- **Email**: Python built-in `smtplib`
- **Testing**: pytest
- **Containerization**: Docker / Docker Compose
- **Process Scheduling**: cron (system-level)
- **Data Format**: CSV

## Project Conventions

### Code Style

- **Type Hints**: Use function type annotations for parameters and return values (e.g., `-> bool`, `-> Optional[str]`, `-> List[Dict]`)
- **Naming**: Snake_case for functions and variables, UPPER_CASE for constants
- **Docstrings**: Include docstrings for all public functions explaining purpose, parameters, and return values
- **Imports**: Group imports by category (stdlib, third-party, local) separated by blank lines
- **Error Handling**: Graceful degradation for optional features (e.g., SMTP, external APIs) with informative logging
- **Logging**: Use Python's built-in logging module; logs written to `/logs/` directory with timestamps
- **Line Length**: Target 100 characters max per line
- **Code Organization**: Modular design with separation of concerns across files

### Architecture Patterns

- **Modular File Structure**: Separate concerns into focused modules:
  - `fide_scraper.py`: Core scraping logic, CSV I/O, orchestration
  - `email_notifier.py`: Email composition and SMTP delivery
  - `ratings_api.py`: External API communication with token-based authentication
- **Configuration Management**: 12-factor app pattern using environment variables (`.env` files)
- **CSV Data Format**:
  - Input: Player ID, Name, Email (from `players.csv`)
  - Output: FIDE ID, Date, Standard Rating, Rapid Rating, Blitz Rating, Last Scraped (from `fide_ratings.csv`)
  - Deduplication: Same-day runs replace existing records; multi-day history maintained
- **Error Recovery**: Non-blocking failures for optional integrations (SMTP, external APIs)
- **Containerization**: Docker for consistent deployment; Docker Compose for multi-service orchestration

### Testing Strategy

- **Testing Framework**: pytest
- **Test Structure**:
  - `tests/` directory with files named `test_*.py`
  - Unit tests: Core functionality, validation, parsing logic
  - Integration tests: File operations, email composition, API interactions
  - Validation tests: Input/output data integrity
- **Mocking**: Use `unittest.mock` for network operations, file I/O in isolation tests
- **Fixtures**: Sample HTML, test data files stored in `tests/fixtures/`
- **Coverage Target**: All non-trivial business logic should have tests
- **Running Tests**: `pytest` from project root (configured in `.vscode/settings.json`)

### Git Workflow

- **Main Branch**: `main` - production-ready code only
- **Feature Development**: Use OpenSpec change proposals for specification-driven development
- **Branching Strategy**: Feature branches created from `main` for each change proposal
- **Commit Conventions**:
  - Descriptive commit messages focusing on "what" and "why"
  - Atomic commits grouped by logical feature/fix
  - Recent commits: Rating scraping features, OpenSpec integration, repo initialization
- **Code Review**: Changes managed through OpenSpec proposals with design/task artifacts

## Domain Context

**Chess Rating System**: FIDE (Brazilian Chess Federation) maintains official chess ratings in three time controls:
- **Standard**: Classical chess (matches >30 minutes per side)
- **Rapid**: Faster games (10-25 minutes per side)
- **Blitz**: Fast games (3-9 minutes per side)

**Player Identification**: Players are identified by a 4-10 digit FIDE ID (numeric). The scraper validates IDs before attempting to fetch profiles.

**Data Persistence**: Historical ratings are tracked in CSV format with date-based records. The same player ID + date should only appear once; later runs on the same day overwrite earlier results.

**Rating Change Detection**: Email notifications trigger when a player's rating differs from the previous scrape result. This allows stakeholders to monitor player progress without email noise for unchanged ratings.

**Integration Points**:
- External API for fetching additional player FIDE IDs (optional, with token auth)
- External API for posting scraped ratings upstream (optional, with token auth)
- SMTP server for sending email notifications (optional; defaults to localhost)

## Important Constraints

- **Scraping Rate**: The FIDE website should not be scrapped faster than once per hour per player ID (respectful scraping to avoid overloading their servers)
- **CSV Integrity**: Output CSV must maintain consistent column order and format to avoid breaking downstream systems
- **Optional Dependencies**: SMTP and external APIs are optional—tool must function without them (with appropriate logging)
- **Data Privacy**: Email addresses from `players.csv` are sensitive; never log full email addresses in plaintext; handle credentials securely in `.env` files
- **Error Tolerance**: Tool must not halt completely on partial failures (e.g., one player fails but others succeed); all errors logged for troubleshooting
- **Python Version**: Requires Python 3.11+ for proper type hint support and modern language features

## External Dependencies

- **FIDE Website** (`ratings.fide.com`): Source of truth for player ratings; scraped via HTTP requests with BeautifulSoup HTML parsing
- **SMTP Server** (optional, configurable via env vars):
  - Default: `localhost:587`
  - Used for sending email notifications to player contacts
  - Authentication optional (depends on server setup)
  - Accessible to: email_notifier.py
- **External API: Player IDs** (optional, configurable via `FIDE_IDS_API_ENDPOINT`):
  - Provides list of additional player FIDE IDs to scrape
  - Requires token authentication via `API_TOKEN`
  - Returns: JSON list of player IDs
  - Fallback: If unavailable, uses only IDs from local `players.csv`
- **External API: Rating Updates** (optional, configurable via `FIDE_RATINGS_API_ENDPOINT`):
  - Receives POST requests with scraped rating data
  - Requires token authentication via `API_TOKEN`
  - Expected format: JSON with player ratings and timestamps
  - Fallback: If unavailable, ratings still saved to local `fide_ratings.csv`
