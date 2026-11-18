## ADDED Requirements

### Requirement: Optional event sync configuration

The system SHALL run the FIDE event sync only when both `FIDE_EVENTS_API_ENDPOINT` and `API_TOKEN` are set. The latest-periods URL SHALL be `FIDE_EVENTS_API_ENDPOINT` with `latest-periods/` appended. `FIDE_EVENTS_STATE_FILE` SHALL default to `fide_events_state.csv`. `FIDE_EVENTS_MAX_REQUESTS` SHALL default to 300.

#### Scenario: Sync enabled
- **WHEN** `FIDE_EVENTS_API_ENDPOINT` is `https://chesshub.cloud/api/fide-events/` and `API_TOKEN` is set
- **THEN** the sync runs, posts to `https://chesshub.cloud/api/fide-events/` and reads `https://chesshub.cloud/api/fide-events/latest-periods/`

#### Scenario: Endpoint not set
- **WHEN** `FIDE_EVENTS_API_ENDPOINT` is unset or empty
- **THEN** the sync does not run and makes no request to FIDE or Chess Hub

#### Scenario: Endpoint set without token
- **WHEN** `FIDE_EVENTS_API_ENDPOINT` is set and `API_TOKEN` is empty
- **THEN** the sync does not run and logs a warning that event posting is disabled

### Requirement: Sync never affects the rating scrape

The system SHALL run the event sync after the rating batch, its CSV output, the ratings API updates and the email notifications. No error raised during the sync SHALL change the rating outputs, the notifications or the process exit code.

#### Scenario: Sync runs after ratings
- **WHEN** a run with the sync enabled processes players
- **THEN** `fide_ratings.csv` is written and the ratings are posted before the first event request is made

#### Scenario: Unexpected error in the sync
- **WHEN** the sync raises an unexpected exception
- **THEN** the error is logged and the run exits with the same code it would have had without the sync

### Requirement: Stored periods are read once per run

The system SHALL read `GET latest-periods/` once per run, with the header `Authorization: Token <API_TOKEN>`, and use the returned map `{fide_id: "YYYY-MM-01"}` as each player's stored period. A player missing from the map has no stored period. If the call fails, the system SHALL skip the sync for the run.

#### Scenario: Stored period present
- **WHEN** latest-periods returns `{"538026660": "2026-11-01"}`
- **THEN** player 538026660 has stored period 2026-11-01

#### Scenario: Player missing from the map
- **WHEN** latest-periods returns `{}` for a due player
- **THEN** the player has no stored period and is fully backfilled

#### Scenario: latest-periods unavailable
- **WHEN** latest-periods returns HTTP 500, 401 or a network error
- **THEN** no FIDE event request is made in that run, no state is changed and a warning is logged

### Requirement: Player checked once per published list

The system SHALL take the run's published list as the newest month in the rating histories parsed in that run. A player SHALL be due when the state file has no `checked_period` for them, or when that period is older than the published list. A player who is not due SHALL cost no FIDE request. If the run parsed no rating history, the sync SHALL be skipped.

#### Scenario: Already checked for the current list
- **WHEN** the published list is 2026-11-01 and the state file has `538026660,2026-11-01`
- **THEN** no request is made for player 538026660

#### Scenario: New list published
- **WHEN** the published list is 2026-12-01 and the state file has `538026660,2026-11-01`
- **THEN** player 538026660 is due

#### Scenario: Player never checked
- **WHEN** the state file has no row for a selected player
- **THEN** the player is due

#### Scenario: No history parsed in the run
- **WHEN** every profile in the run failed or had no rating history
- **THEN** the sync is skipped

### Requirement: Only the players selected by the run

The system SHALL consider only the FIDE IDs selected for the run, in the order they were selected.

#### Scenario: Quick mode
- **WHEN** the run is in quick mode and selected only new ID 1503014
- **THEN** the sync considers only player 1503014

### Requirement: Period listing

The system SHALL list a due player's (period, time control) pairs from the `View` links of `GET https://ratings.fide.com/a_calculations.phtml?event=<fide_id>`, taking the period from `period=YYYY-MM-01` and the time control from `rating=` (0 standard, 1 rapid, 2 blitz). The system SHALL also request the older periods with `POST https://ratings.fide.com/a_calculations.phtml` and the body `action=2&plr_id=<fide_id>`, and only when:
- the first page shows the "Check more periods" button, and
- the player has no stored period, or the stored period is older than the oldest period on the first page.

#### Scenario: Stored period on the first page
- **WHEN** the first page lists 2026-11, 2026-10 and 2026-08, has the "Check more periods" button, and the stored period is 2026-08-01
- **THEN** the older periods are not requested

#### Scenario: Stored period older than the first page
- **WHEN** the first page's oldest period is 2026-08 and the stored period is 2025-11-01
- **THEN** the older periods are requested and their pairs are added to the listing

#### Scenario: Full backfill
- **WHEN** the player has no stored period and the first page has the "Check more periods" button
- **THEN** the older periods are requested

#### Scenario: Player without calculations
- **WHEN** the listing has no `View` link
- **THEN** no period is fetched and the player is marked checked for the published list

### Requirement: Pending periods from the stored period on, oldest first

The system SHALL fetch every listed pair whose period is at or after the player's stored period, or every listed pair when there is no stored period. Pairs SHALL be ordered by period ascending, then standard, rapid, blitz.

#### Scenario: Stored period is re-sent
- **WHEN** the stored period is 2026-08-01 and the listing has (2026-08, rapid), (2026-10, blitz), (2026-11, standard) and (2026-11, rapid)
- **THEN** the pairs are fetched in the order (2026-08, rapid), (2026-10, blitz), (2026-11, standard), (2026-11, rapid)

#### Scenario: Older periods skipped
- **WHEN** the stored period is 2026-08-01 and the listing also has (2026-06, rapid)
- **THEN** (2026-06, rapid) is not fetched

### Requirement: Period events parsing

The system SHALL fetch each pending pair from `GET https://ratings.fide.com/a_indv_calculation.php?id_number=<fide_id>&rating_period=<YYYY-MM-01>&t=<0|1|2>`. It SHALL parse one event per block. Each event SHALL have:
- `fide_event_code`, from the `report.phtml?event=<code>` link;
- `name`, the link text;
- `city` and `country`, from the location line: `country` is the last token when it is 3 uppercase letters, and `city` is the rest;
- `start_date` and `end_date`, from the two dates;
- `games`, from the summary column `n`;
- `rating_change`, from the summary column `K*chg`, or null when the summary has no `K*chg` column.

FIDE's dates for old events SHALL be repaired so that `end_date >= start_date`:
- a missing date (`0000-00-00`) takes the other date;
- an `end_date` before `start_date` moves forward 100 years when that lands between `start_date` and 366 days after it, and otherwise becomes `start_date`.

An event without a code, or with neither date valid, SHALL be skipped with a warning. A response of "No records found." or "Invalid data" SHALL be a period without events.

#### Scenario: Rated period
- **WHEN** rapid 2025-11-01 shows event 442504 "2o Circuito de Xadrez Canoas Shopping Aberto Recreativo e Inclusivo Escolar Absoluto Quarta Etapa", location "Canoas RS BRA", dates 2025-10-11 and 2025-10-11, and a summary with `n` 6 and `K*chg` 52.00
- **THEN** the event is `{fide_event_code: "442504", name: "2o Circuito de Xadrez Canoas Shopping Aberto Recreativo e Inclusivo Escolar Absoluto Quarta Etapa", city: "Canoas RS", country: "BRA", start_date: 2025-10-11, end_date: 2025-10-11, games: 6, rating_change: 52.00}`

#### Scenario: Unrated period
- **WHEN** standard 2026-11-01 shows event 500368 with location "Porto Alegre RS BRA", dates 2026-09-23 and 2026-10-21, and a summary with headers `Rc Ro w n chg Rp K` and `n` 3
- **THEN** the event has `city: "Porto Alegre RS"`, `country: "BRA"`, `games: 3` and `rating_change: null`

#### Scenario: Several events in one period
- **WHEN** a period response has three event blocks
- **THEN** three events are parsed, in page order

#### Scenario: No records
- **WHEN** the response is "No records found."
- **THEN** the period has no events

#### Scenario: Invalid data
- **WHEN** standard 2001-10-01 is listed with a `View` link and the response is "Invalid data"
- **THEN** the period has no events and the sync goes on with the next period

#### Scenario: Missing end date
- **WHEN** event 19212 has dates 2001-02-09 and 0000-00-00
- **THEN** its `start_date` and `end_date` are both 2001-02-09

#### Scenario: End date a century early
- **WHEN** event 21236 has dates 2001-12-17 and 1901-12-23
- **THEN** its `end_date` is 2001-12-23

#### Scenario: Unrecognized markup
- **WHEN** the response is not empty, is not "No records found." and yields no event
- **THEN** it is treated as a parse failure for the player

### Requirement: Each period is posted to Chess Hub

The system SHALL post each fetched pair, right after fetching it and before fetching the next, as `POST FIDE_EVENTS_API_ENDPOINT` with the header `Authorization: Token <API_TOKEN>` and the body `{fide_id, player_name, rating_period, time_control, events}`. `player_name` SHALL be the name parsed from the player's profile in the run, and `time_control` SHALL be `standard`, `rapid` or `blitz`. Any response other than HTTP 2xx SHALL count as a failed post.

#### Scenario: Period posted
- **WHEN** rapid 2025-11-01 of player 538026660 has one event
- **THEN** the body is `{"fide_id": "538026660", "player_name": "Klein, Eduardo Pavinato", "rating_period": "2025-11-01", "time_control": "rapid", "events": [...]}` with that event, dates as `YYYY-MM-DD`

#### Scenario: Post rejected
- **WHEN** Chess Hub answers HTTP 400 for a period
- **THEN** no further period of that player is fetched in the run and the player is not marked checked

### Requirement: FIDE request pacing and AJAX header

The system SHALL wait `REQUEST_DELAY_SECONDS` before every FIDE event request and SHALL send `X-Requested-With: XMLHttpRequest` with it. A response with an empty or BOM-only body SHALL be treated as FIDE throttling.

#### Scenario: AJAX header sent
- **WHEN** any listing or period request is made
- **THEN** it has the header `X-Requested-With: XMLHttpRequest`

#### Scenario: Pacing
- **WHEN** two FIDE event requests are made in a row
- **THEN** at least `REQUEST_DELAY_SECONDS` passes before the second

### Requirement: Failure handling and resumption

The system SHALL stop the whole sync for the run when FIDE throttles. It SHALL stop only the current player on a network error, timeout, HTTP error, parse failure or failed post, and go on with the next player. A player whose sync stopped SHALL keep their previous `checked_period`.

#### Scenario: Throttled
- **WHEN** a period request of the second due player returns an empty body
- **THEN** no further FIDE request is made in the run, and the second player is not marked checked

#### Scenario: Network error on one player
- **WHEN** a listing request times out for one player
- **THEN** that player is not marked checked and the next due player is synced

#### Scenario: Resume after interruption
- **WHEN** a backfill stopped after posting (2025-11, rapid), and the next run's latest-periods returns 2025-11-01 for the player
- **THEN** the next run fetches every listed pair of 2025-11 and later, (2025-11, rapid) included, and nothing older

### Requirement: Per-run request cap

The system SHALL make at most `FIDE_EVENTS_MAX_REQUESTS` FIDE event requests per run. When the cap is reached, the sync SHALL stop before the next FIDE request, and the current player SHALL not be marked checked.

#### Scenario: Cap reached mid-backfill
- **WHEN** `FIDE_EVENTS_MAX_REQUESTS` is 10 and a player has 14 pending pairs
- **THEN** at most 10 FIDE requests are made, counting the listing requests, the posted periods stay posted, and the player is not marked checked

### Requirement: Local checked state

The system SHALL keep a CSV file at `FIDE_EVENTS_STATE_FILE` with the header `fide_id,checked_period` and one row per player. When every pending pair of a player has been posted, the system SHALL set that player's `checked_period` to the run's published list. It SHALL rewrite the file after each player through a temporary file and an atomic rename. A missing or unreadable file SHALL be treated as empty.

#### Scenario: Player completed
- **WHEN** all pending pairs of player 538026660 are posted in a run whose published list is 2026-12-01
- **THEN** the state file has the row `538026660,2026-12-01`

#### Scenario: Missing state file
- **WHEN** the state file does not exist
- **THEN** every selected player is due and the file is created after the first completed player

#### Scenario: Other players kept
- **WHEN** the state file has rows for players A and B and only A is synced in the run
- **THEN** B's row is unchanged

### Requirement: Run summary

The system SHALL log one line when the sync starts: the due players out of the selected ones, the published list, the number of players with stored events, and the cap. It SHALL log one line for each completed player: the pending pairs, the stored period they start from, the periods posted, the events created and updated, and the FIDE requests used. Every failure line SHALL name the player and the listing or the period and time control that failed. At the end, it SHALL log one summary line for the sync with these values:
- players due, completed, failed;
- periods posted;
- events created and updated, as reported by Chess Hub;
- FIDE requests used;
- the stop reason: completed, cap, throttled or skipped.

#### Scenario: Progress during a long sync
- **WHEN** 120 players are due
- **THEN** one line is logged when the sync starts and one after each completed player, so a long sync is visible as it runs

#### Scenario: Summary after a capped run
- **WHEN** the sync stops at the cap
- **THEN** the summary line reports the stop reason `cap` and the number of requests used
