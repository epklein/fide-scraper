## Why

Chess Hub stores the events a player took part in and shows them on the profile. It also joins those events with CBX events and club events. The cbx-scraper already sends CBX events. Chess Hub has the FIDE side ready, but nothing sends FIDE events yet: `POST /api/fide-events/` and `GET /api/fide-events/latest-periods/` are in production but not yet recorded in the chess-wizard changelog.

FIDE has no endpoint that returns a player's whole event history. The events can be read only one rating period and one time control at a time, from the AJAX endpoints behind the profile's Calculations tab. The cron runs every 2 hours and FIDE throttles around 95 requests per 2 minutes. So the scraper has to fetch only what Chess Hub does not have yet, and only when FIDE can have published something new.

## What Changes

- **Read the event history from FIDE.**
  - List the rating periods that have calculations, per time control, from `a_calculations.phtml?event=<id>`.
  - Call "Check more periods" (`POST a_calculations.phtml`, `action=2`) only when the needed periods are not on the first page.
  - Read each needed period and time control from `a_indv_calculation.php`. For each event, keep its FIDE code, name, city, country, start and end dates, games and rating change.
  - These endpoints only answer AJAX requests: send the `X-Requested-With: XMLHttpRequest` header.
- **Fetch incrementally, using Chess Hub's state.**
  - At the start of the run, read `GET /api/fide-events/latest-periods/` once.
  - For each player, fetch the periods from that period on, that period included, so corrections and a partly sent period are picked up.
  - A player missing from the response gets a full backfill.
  - The backfill goes from the oldest period to the newest. Then an interrupted run never leaves gaps below the stored period.
- **Send each period and time control** with `POST /api/fide-events/`, in the same order. The API only adds and updates, so sending a period again is safe.
- **Keep a local record of the last checked list for each player**, so a player is checked once per FIDE rating list and not on every 2-hour run.
  - The newest published list is taken from the rating histories scraped in the same run.
  - A player is marked checked only after all of their pending periods were sent.
- **Pace and recover from throttling.**
  - The new requests use the existing delay between requests.
  - A throttled or failed call stops that player's sync without marking it checked, so the next run retries it.
  - A cap on event requests per run lets a large backfill spread over several runs.
- **Make the sync optional.** It runs only when `FIDE_EVENTS_API_ENDPOINT` and `API_TOKEN` are set, following the cbx-scraper. A failure in the event sync never fails the rating scrape, its notifications or its exit code.

## Capabilities

### New Capabilities

- `event-history-sync`:
  - discover and parse a player's FIDE events from the Calculations endpoints;
  - choose the periods to fetch from Chess Hub's latest stored period and the local checked-list record;
  - post them to `/api/fide-events/`;
  - follow the pacing, throttling, request-cap and optional-configuration rules.

### Modified Capabilities

None. The rating extraction, storage, change detection, notifications and execution modes keep their requirements. Quick mode reaches new players through the same sync, and they get a full backfill because Chess Hub has no stored period for them.

## Impact

- **Code**:
  - a new module for the Calculations endpoints, their parsing and the events API calls, like `events_api.py` in the cbx-scraper;
  - `fide_scraper.py` `main()` runs the sync after the rating batch;
  - new tests with saved FIDE HTML fixtures.
- **Configuration**:
  - `FIDE_EVENTS_API_ENDPOINT`, which also gives the `latest-periods/` URL;
  - an optional cap on event requests per run;
  - the path of the local checked-list file;
  - `.env.example`, `.env.docker` and `README.md`. The state file goes in the `/data` volume, which is already persisted, next to `fide_ratings.csv`.
- **External systems**:
  - more requests to ratings.fide.com, about one listing request per player per monthly list plus one per new period and time control;
  - a one-time backfill, spread over several runs by the cap;
  - Chess Hub's `/api/fide-events/` endpoints, unchanged.
- **Dependencies**: none new. The project already uses `requests` and `beautifulsoup4`.
