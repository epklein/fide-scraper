# Design Document: Quick Execution Mode

## Context

The FIDE scraper currently always processes all player IDs from the players.csv file. Users want an option to run in "quick" mode, where only newly discovered FIDE IDs from the external API are processed. This is useful for:
- Running lightweight checks during business hours
- Processing incremental updates without re-scraping existing players
- Reducing load when the CSV file contains hundreds of IDs but only a few are new

## Goals

**Primary Goal:** Enable fast, incremental execution focused on new players only.

**Secondary Goals:**
- Maintain backward compatibility (default behavior unchanged)
- Keep implementation simple and non-disruptive
- Ensure both modes share the same downstream logic (notifications, CSV updates, API posts)

## Non-Goals

- Custom execution profiles or complex mode configurations
- Persistent state tracking of execution modes
- Performance optimization beyond skipping existing player processing
- Changes to notification or API update logic

## Decision: Execution Mode Pattern

### Decision: CLI Flag-Based Mode Selection

**What:** Use a `--quick` command-line flag to select execution mode.

**Why:**
1. Simple, explicit, and discoverable (`--help` shows it)
2. No persistent configuration needed
3. Easy to use in cron jobs and CI/CD (just add `--quick` to one job)
4. Standard Unix pattern

**Alternatives Considered:**
- Environment variable: Less discoverable, requires users to manage `.env` for each run
- Config file mode selection: Adds complexity, requires state management
- Always-quick mode based on API results: Loses ability to do full runs when needed

### Decision: ID Selection Logic Separation

**What:** Extract ID selection into a separate function `select_fide_ids_for_processing()` that encapsulates the mode logic.

**Why:**
1. Keeps main() clean and focused on orchestration
2. Makes mode logic testable in isolation
3. Makes it easy to add more modes in the future
4. Separates "what IDs to process" from "how to process them"

**Function Signature:**
```python
def select_fide_ids_for_processing(
    mode: str,  # 'normal' or 'quick'
    api_endpoint: str,
    api_token: str,
    csv_player_data: dict
) -> tuple[list[str], list[str]]:
    """
    Returns (selected_ids, new_api_ids)
    - selected_ids: The IDs to process (all CSV in normal mode, new API only in quick mode)
    - new_api_ids: The new IDs from API (used for augmentation)
    """
```

**Mode Behavior:**
- **Normal Mode:**
  1. Fetch API IDs (if configured)
  2. Merge with CSV IDs
  3. Return all IDs for processing (CSV + new API IDs)
  4. Return new IDs separately for augmentation

- **Quick Mode:**
  1. Fetch API IDs (if configured)
  2. Compare with CSV IDs
  3. Return only new IDs for processing
  4. Return same new IDs for augmentation

## Decision: Augmentation Behavior

**What:** Players.csv is augmented with new API IDs in both modes.

**Why:**
1. Ensures next run (quick or normal) knows about new players
2. Maintains consistent "single source of truth" in players.csv
3. Makes quick mode a genuine subset of normal mode behavior

## Decision: Error Handling Strategy

**What:**
- API failures in quick mode → Log and continue with empty new ID list (valid scenario)
- Augmentation failures → Log warning, continue processing (don't block on file I/O)
- No new IDs in quick mode → Valid scenario, exit with success code 0 if any other processing succeeded

**Why:**
- Graceful degradation: Tool remains useful even when API is unavailable
- Distinction between configuration errors (exit 2) and processing failures (exit 1)
- Aligns with existing error handling patterns in the codebase

## Decision: Downstream Logic Unchanged

**What:** Notification, API update, and CSV output logic remain identical in both modes.

**Why:**
1. Keeps implementation scope minimal
2. Reduces testing burden
3. Both modes produce valid results for downstream systems
4. Future enhancements can modify downstream behavior independently

## Implementation Strategy

### Phase 1: CLI & Mode Selection
1. Add `--quick` argument to argparse
2. Create `select_fide_ids_for_processing()` function
3. Update main() to call the selection function

### Phase 2: Testing
1. Unit tests for selection function
2. Integration tests with mock data
3. Manual testing with real setup

### Phase 3: Documentation
1. Update README with usage examples
2. Update help text
3. Update .env.example comments if needed

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Quick mode gets out of sync with CSV | Augmentation always happens; user can run normal mode to sync |
| Backward compatibility broken | Default (no flag) behaves identically to before |
| Confusion about which IDs are processed | Clear logging indicates mode and ID counts |
| API failures break quick mode | Graceful handling; proceed with empty list if API unavailable |

## Exit Code Semantics

- **0:** Success (at least one player processed OR normal mode)
- **1:** Failure (errors occurred during processing)
- **2:** Configuration/validation error (missing files, invalid input)

Special case for quick mode: If API returns no new IDs and no players are processed, still exit 0 (valid scenario).

## Testing Strategy

### Unit Tests
- Mode selection logic with various CSV/API combinations
- ID filtering (new vs. existing)
- Error scenarios

### Integration Tests
- Full run with `--quick` flag
- Full run without flag (normal mode)
- CSV augmentation verification
- Notification dispatch (should work same as normal)
- API updates (should work same as normal)

### Manual Testing
- Run with real scraper setup
- Verify --help shows `--quick`
- Verify exit codes
- Verify CSV updates

## Future Extensions

If more modes are needed later:
- Modes could extend to: `normal`, `quick`, `incremental`, `single-player`, etc.
- Selection function signature already supports this
- Each mode would define its own ID selection logic
