## 1. Fixtures

- [x] 1.1 Save the captured FIDE responses under `tests/fixtures/fide_events/`:
  - `a_calculations_page1.html`, the first listing page with the "Check more periods" button;
  - `a_calculations_more.html`, the `action=2` response;
  - `indv_rapid_2025-11_rated.html`, with summary `K*chg`;
  - `indv_standard_2026-11_unrated.html`, with summary `Rp K` and no `K*chg`.

  The source files are in `$PANE_SCRATCH_DIR/fide/`. Strip the BOM only where the parser does too.
- [x] 1.2 Add a synthetic fixture with several event blocks in one period, and the "No records found." body.

## 2. Chess Hub API client (`events_api.py`)

- [x] 2.1 Add `load_events_api_config()`:
  - read `FIDE_EVENTS_API_ENDPOINT` and `API_TOKEN`;
  - return `None` when either is missing, with a warning when only the endpoint is set;
  - derive the `latest-periods/` URL, taking care of the trailing slash.
- [x] 2.2 Add `fetch_latest_periods(config)`:
  - `GET` with `Authorization: Token`;
  - return `{fide_id: date}`;
  - raise on any non-2xx, network error or invalid JSON.
- [x] 2.3 Add `post_period_events(config, fide_id, player_name, rating_period, time_control, events)`:
  - serialize the dates as ISO strings;
  - return the `{created, updated}` counts on 2xx and raise otherwise.
- [x] 2.4 Unit tests with mocked `requests`:
  - config combinations;
  - the auth header;
  - URL derivation;
  - success, 401, 500 and timeout for both calls;
  - the payload shape.

## 3. FIDE fetching and parsing (`fide_events.py`)

- [x] 3.1 Add the request helper and the per-run budget:
  - wait `REQUEST_DELAY_SECONDS` before each request;
  - send the scraper's usual headers plus `X-Requested-With: XMLHttpRequest`;
  - raise `RateLimitError` on an empty or BOM-only body, reusing `fide_scraper._is_rate_limited_response`;
  - count requests against `FIDE_EVENTS_MAX_REQUESTS` and raise a dedicated `RequestCapReached` before going over.
- [x] 3.2 Add `parse_period_listing(html)`. It returns the sorted list of (period date, time control) from the `View` links, and whether the "Check more periods" button is present.
- [x] 3.3 Add `fetch_period_listing(fide_id, stored_period)`. It fetches page 1 and calls `POST action=2` only under the rule in design §4, then returns the merged, deduplicated pairs.
- [x] 3.4 Add `parse_period_events(html)`, one dict per event block:
  - code and name from the `report.phtml?event=` link;
  - city and country from the location line;
  - the two dates;
  - `games` from column `n` and `rating_change` from `K*chg`, both by header label;
  - an event without a code or dates is skipped with a warning;
  - "No records found." returns `[]`;
  - unrecognized markup raises a parse error.
- [x] 3.5 Add `fetch_period_events(fide_id, period, time_control)`, which maps `standard`, `rapid` and `blitz` to `t` 0, 1 and 2.
- [x] 3.6 Unit tests against the fixtures:
  - the listing with and without the button;
  - the `action=2` decision for each stored-period case in the spec;
  - the rated and unrated events with the exact field values from the spec scenarios;
  - several events in one period;
  - No records;
  - unrecognized markup;
  - the XHR header and pacing, with `time.sleep` mocked;
  - the request cap;
  - throttle detection.

## 4. Period selection and local state

- [x] 4.1 Add `pending_pairs(listing, stored_period)`: pairs whose period is at or after the stored period, or all of them when there is none, sorted by period and then standard, rapid, blitz.
- [x] 4.2 Add `published_list(results)`, the newest month across the rating histories of this run's results, or `None`.
- [x] 4.3 Add `load_state(path)`, which treats a missing or unreadable file as empty, and `save_state(path, state)`, which writes `fide_id,checked_period` through a temp file and `os.replace`.
- [x] 4.4 Unit tests:
  - ordering;
  - the inclusive stored period;
  - no stored period;
  - the published list across mixed results;
  - the state round-trip;
  - a missing file;
  - other players' rows kept;
  - an atomic write that leaves no partial file on failure.

## 5. Orchestration (`sync_events`)

- [x] 5.1 Add `sync_events(fide_ids, results)`, in this order:
  - return early when the config is disabled or there is no published list;
  - read latest-periods once, and skip the sync on failure;
  - go through the selected IDs in order, skipping players already checked for the published list.
- [x] 5.2 Sync each due player:
  - get the listing and the pending pairs;
  - fetch then post each pair in order;
  - when all are posted, set `checked_period` and save the state;
  - mark a player with no calculations checked;
  - take the player name from the run's result for that ID, and skip with a warning a player whose profile failed this run.
- [x] 5.3 Handle errors:
  - `RateLimitError` and `RequestCapReached` stop the whole sync;
  - network, HTTP, parse and post errors stop only the current player;
  - neither case marks the player checked.
- [x] 5.4 Log the summary line: players due, completed and failed, periods posted, events created and updated, requests used, and the stop reason (`completed`, `cap`, `throttled`, `skipped`).
- [x] 5.5 Unit tests with FIDE and Chess Hub mocked:
  - a player already checked makes zero requests;
  - a full backfill goes oldest first;
  - resume after an interruption;
  - throttle on the 2nd player stops the sync;
  - a timeout on one player continues with the next;
  - a rejected post;
  - the cap reached mid-player;
  - latest-periods unavailable;
  - no published list;
  - quick-mode IDs only.

## 6. Integration in `fide_scraper.py`

- [x] 6.1 In `main()`, call `sync_events(fide_ids, results)` after the console output, the API updates and the notifications. Wrap it in `try/except Exception` that only logs, and leave the exit code logic unchanged.
- [x] 6.2 Test that `main()` writes the CSV and posts the ratings before any event request, and that an exception in `sync_events` does not change the exit code.

## 7. Configuration and docs

- [x] 7.1 Add `FIDE_EVENTS_API_ENDPOINT`, `FIDE_EVENTS_STATE_FILE` and `FIDE_EVENTS_MAX_REQUESTS` to `.env.example` with comments. In `.env.docker`, set `FIDE_EVENTS_STATE_FILE=/data/fide_events_state.csv` and the production endpoint.
- [x] 7.2 Document in `README.md`:
  - the event sync;
  - its variables;
  - the state file and how to reset it;
  - the expected backfill behavior across runs.

## 8. Verification

- [x] 8.1 Run the full test suite (`pytest`).
- [x] 8.2 Do a manual run against the live sites for one FIDE ID, with a local state file and `FIDE_EVENTS_MAX_REQUESTS` low enough to stop mid-backfill. Then run again and confirm that it resumes, and that a third run makes no FIDE event request. Respect the rate limit between runs.
- [x] 8.3 Run `openspec validate fide-events-history --strict`.

## 9. Old FIDE data and progress logging (found in a production run)

- [x] 9.1 Treat the "Invalid data" period response (old periods listed with a View link) as a period without events.
- [x] 9.2 Repair old event dates: a `0000-00-00` date takes the other one, and an end a century early is moved forward 100 years when that lands within a year of the start; otherwise the end becomes the start.
- [x] 9.3 Log a start line, one line per completed player, and the listing or period in every failure line.
- [x] 9.4 Fixtures and tests from players 2101246, 1503014 and 2107660 (2001-2002 periods).
