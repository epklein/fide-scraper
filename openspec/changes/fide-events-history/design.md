## Context

The scraper runs every 2 hours. Each run fetches `ratings.fide.com/profile/<id>/chart` for every player and parses the rating history: one row per published list month, with rating and games per time control. It writes `fide_ratings.csv` and posts the ratings to Chess Hub. It keeps about 1.5 s between requests (`REQUEST_DELAY_SECONDS`) to stay under FIDE's limit of about 95 requests per 2 minutes. FIDE signals throttling with HTTP 200 and an empty body, and its nginx micro-cache keeps that empty response per URL for several minutes.

Chess Hub already exposes the FIDE side of the events feature, in production:

- `GET /api/fide-events/latest-periods/` returns `{"<fide_id>": "YYYY-MM-01"}`: for each player with at least one stored participation, the highest `rating_period` across all time controls. The call is token-authenticated (`Authorization: Token <API_TOKEN>`) and has no pagination.
- `POST /api/fide-events/` takes one player, one rating period and one time control: `{fide_id, player_name, rating_period, time_control, events: [{fide_event_code, name, city, country, start_date, end_date, games, rating_change}]}`. It only adds and updates, and accepts an empty `events` list.

FIDE has no bulk endpoint for a player's events. These are the endpoints behind the profile's Calculations tab, verified on 2026-11-17:

| Endpoint | Returns |
|---|---|
| `GET /a_calculations.phtml?event=<id>` | the most recent periods, as rows `YYYY-Mon` with a `View` link `calculations.phtml?id_number=<id>&period=YYYY-MM-01&rating=<0\|1\|2>` per time control that has games, and a "Check more periods" button when older rows exist |
| `POST /a_calculations.phtml` with `action=2&plr_id=<id>` | all remaining older rows, same markup, in one response |
| `GET /a_indv_calculation.php?id_number=<id>&rating_period=YYYY-MM-01&t=<0\|1\|2>` | the events rated in that period and time control. Without `X-Requested-With: XMLHttpRequest` the body is empty, the same as the throttle response. An empty `rating_period` returns "No records found". |

`a_indv_calculation.php` returns one block per event:

- the name links to `/report.phtml?event=<code>&t=<t>`;
- the next line has the location (`Canoas RS BRA`, sometimes inside `<strong>`) and two `dates_span` dates (start, end);
- a `calc_table` follows, with a summary row and then one row per opponent.

The summary columns depend on the player's status. A rated player has `Rc Ro w n chg K K*chg`. A player still unrated in that list has `Rc Ro w n chg Rp K`, with no `K*chg`.

The profile's rating history and `a_chart_data.phtml` both leave out the periods in which the player had no rating yet. So they cannot replace the `a_calculations` listing.

## Goals / Non-Goals

**Goals:**
- Send every FIDE event of every tracked player to Chess Hub, including those played while unrated.
- In steady state, cost about one listing request per player per monthly FIDE list, plus one request per new period and time control, with zero extra requests on the other runs.
- Resume an interrupted backfill exactly where it stopped, without gaps and without changing the Chess Hub API.
- Never let the event sync affect the rating scrape, its outputs, notifications or exit code.

**Non-Goals:**
- Storing games and opponents. Those come from the calculation rows, and Chess Hub does not accept them.
- Reading `tournament_information.phtml` (time control text, arbiter, number of players).
- Detecting FIDE corrections to periods older than the stored period.
- Any change to Chess Hub's endpoints.

## Decisions

### 1. Two new modules, mirroring the cbx-scraper

- `fide_events.py` holds the FIDE side and the orchestration:
  - fetch and parse the listing;
  - fetch and parse each period and time control;
  - choose the periods to fetch;
  - keep the local state;
  - `sync_events(...)`.
- `events_api.py` holds the Chess Hub side:
  - read the config;
  - `GET latest-periods/`;
  - `POST` one period.

`fide_scraper.py` only calls `sync_events` from `main()`. *Alternative:* add everything to `fide_scraper.py`, which already has more than 1,300 lines. Rejected, because separate modules keep the parsing testable with fixtures and match the sibling project.

### 2. Configuration

- `FIDE_EVENTS_API_ENDPOINT`, for example `https://chesshub.cloud/api/fide-events/`. The latest-periods URL is that value with `latest-periods/` appended.
- The token is the existing `API_TOKEN`.
- The sync is disabled, with a warning if only one of the two is set, unless both are set. This is the same rule as `CBX_EVENTS_API_ENDPOINT`.
- `FIDE_EVENTS_STATE_FILE`, default `fide_events_state.csv`.
- `FIDE_EVENTS_MAX_REQUESTS`, default `300`: FIDE requests per run, which is about 7.5 minutes at the default delay.

### 3. When a player is due: the local checked list

- The state file has the columns `fide_id,checked_period`. The second is the newest FIDE list (`YYYY-MM-01`) for which all of the player's pending periods were sent.
- The **published list** of a run is the newest month in the rating histories parsed in that same run. FIDE publishes every list at once, so any rated player shows it. The run gets this value without any extra request.
- A player is due when they have no row, or when their `checked_period` is older than the published list. A player who is not due costs zero requests.
- If the run parsed no history at all, there is no published list and the sync is skipped.
- *Alternative:* use the calendar month. Rejected, because a run at 00:00 on the 1st, before FIDE publishes, would mark the month as checked without the new list.
- *Alternative:* ask Chess Hub to store a "checked" marker. Rejected, because it is an API change and the API is already released.

### 4. Which periods to fetch: from the stored period on, oldest first

- `stored = latest_periods.get(fide_id)`.
- Fetch the first listing page.
- Call `action=2` only if `stored` is missing, or if `stored` is older than the oldest period on page 1 and page 1 has the "Check more periods" button. Older rows exist only on page 2, so every period at or after `stored` is otherwise already on page 1.
- Pending = every (period, time control) with `period >= stored`, or every pair when `stored` is missing. They are sorted by period ascending, then standard, rapid, blitz.
- Re-sending the `stored` period covers the case where only some time controls of it were sent, because the stored value is a maximum across time controls. It also picks up corrections in the latest period. The local state limits this re-send to once per list.
- With the ascending order, the stored value always means "everything before this is sent". So a run cut short by the cap, throttling or an error resumes correctly in the next run.

### 5. Parsing

The listing is parsed for its `View` links, using `period` and `rating` from each `href`.

`a_indv_calculation.php` is parsed per event block:

- `fide_event_code` comes from `report.phtml?event=`, and `name` is the link text.
- From the location line, the last token is `country` when it is 3 uppercase letters, and the rest is `city`.
- `start_date` and `end_date` come from the two `dates_span`.
- `games` and `rating_change` come from the summary row, read by header label and not by position:
  - `games` is the `n` column;
  - `rating_change` is the `K*chg` column, or `null` when the header has no `K*chg` (unrated).

Old events have broken dates in FIDE's data. Events up to 2001 have an end of `0000-00-00`. Events up to about 2006 have an end a century before the start, such as 2001-12-17 to 1901-12-23. Chess Hub rejects an end before the start, and a rejected period would block that player's backfill on every run. So the dates are repaired:
- a missing date takes the other one;
- an end a century early is moved forward 100 years when that lands within a year of the start;
- any other end before the start becomes the start.

An event without a code, or with neither date valid, is skipped with a warning.

Some old periods are listed with a `View` link but answer "Invalid data". That counts as a period without events, the same as "No records found". Treating it as a failure would stop the oldest-first backfill at that period forever.

A response that is not empty, yields no events and is neither message counts as a parse failure.

The time control comes from the `t` used in the request: 0 is `standard`, 1 is `rapid`, 2 is `blitz`.

### 6. Requests, pacing and throttling

- All FIDE requests go through one helper. It waits `REQUEST_DELAY_SECONDS` before each request, sends the scraper's usual headers plus `X-Requested-With: XMLHttpRequest`, and raises the existing `RateLimitError` on an empty or BOM-only body.
- A `RateLimitError` stops the **whole** sync for the run. The throttle applies to the whole IP, and the cache keeps the empty response, so continuing would only waste requests.
- Network and HTTP errors, parse failures and failed POSTs stop only that player, and the sync goes on to the next one.
- In every case the player keeps their old `checked_period`, so the next run retries.
- Reaching `FIDE_EVENTS_MAX_REQUESTS` stops the sync before the next FIDE request.

### 7. Order of work in a run

1. The sync runs after the rating batch, its CSV output, the API updates and the notifications. Ratings never wait for events.
2. It calls `latest-periods/` once. If that call fails, the sync is skipped for the run. Treating every player as "no stored period" would start a full backfill for everyone.
3. Players are handled in the order the run selected them, so quick mode syncs only its new IDs.
4. For each due player, each pending period is fetched and then posted, one at a time. When all are posted, `checked_period` is set to the published list.
5. A player with no calculations at all is marked checked.
6. The state file is written after each player, through a temp file and `os.replace`, so a crash keeps the work done so far.
7. The whole sync is wrapped in `try/except`. It logs a summary (players checked, periods posted, events created and updated, requests used, stop reason) and never changes the exit code.

## Risks / Trade-offs

- [FIDE changes the Calculations markup] → Fixtures in tests cover rated and unrated blocks. A parse failure is logged per player and does not mark the player checked, so the data is fetched again once the parser is fixed.
- [The first backfill for many players is large: on average a dozen or more requests per active player] → The per-run cap, the ascending order and Chess Hub's stored period spread it over several runs and let it resume. Later months cost little.
- [The calculations appear after the profile already shows the new list] → The player is marked checked for that list. Next month, the fetch from the stored period on still includes the missed period, because it is newer than the stored one. It arrives one list late, not never.
- [FIDE adds an event to a period older than the stored one] → It is not detected (non-goal). Deleting the player's row from the state file does not help either, because the stored period still bounds the fetch.
- [A run with only unrated new players (quick mode) finds no published list] → The sync is skipped, and the next normal run picks them up.
- [The state file is lost, for example a volume that was not persisted] → The only cost is one extra listing request per player, and one re-sent period each. The safety comes from Chess Hub's stored period. The state file must still sit on the persisted volume, next to `fide_ratings.csv`.
- [The event sync makes runs longer and could overlap the next cron run] → The cap keeps the sync to about 7.5 minutes at the default delay, against a 2-hour interval.

## Migration Plan

1. Deploy with `FIDE_EVENTS_API_ENDPOINT` unset. Nothing changes.
2. Set `FIDE_EVENTS_API_ENDPOINT`, and set `FIDE_EVENTS_STATE_FILE=/data/fide_events_state.csv` in `.env.docker`. The `/data` volume is already persisted, next to `fide_ratings.csv`. The backfill starts and spreads over the next runs, which the logs show through the summary line.
3. Rollback: unset `FIDE_EVENTS_API_ENDPOINT`. The data already sent stays in Chess Hub, which is harmless, and the state file can stay or be deleted.

## Open Questions

- Is 300 FIDE requests per run the right default cap, or should the first backfill be run once by hand with a higher cap?
