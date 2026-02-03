# Change Proposal: Quick Execution Mode

**Change ID:** `add-quick-execution-mode`

**Scope:** Add a `--quick` flag to process only newly discovered FIDE IDs from the API, skipping existing players in the CSV file.

## Summary

This change introduces a quick execution mode that fetches only new FIDE IDs from the external API and processes only those players, ignoring existing IDs already in the local players.csv file. This enables faster runs when you only care about recently added players.

## Why

### Problem

Currently, every execution processes all FIDE IDs from the players.csv file, whether they are new or have been there for weeks. This is inefficient when you want to:
- Do a quick check of recently added players
- Minimize API and scraping load for large existing player bases
- Run fast "delta" processing that focuses only on new players

### Solution

Add a `--quick` command-line flag that changes the execution mode to:
1. Fetch new FIDE IDs from the API
2. Compare against existing players.csv
3. Process **only the new IDs** returned by the API that don't exist in the CSV
4. Still augment the players.csv file with the new IDs
5. Send notifications and API updates normally

This allows stakeholders to run quick executions during business hours and full executions during off-peak times.

## Key Changes

1. **Add CLI argument:** New `--quick` flag to enable quick execution mode
2. **Conditional ID filtering:** When `--quick` is active:
   - Fetch FIDE IDs from API
   - Keep only IDs that are new (not in current players.csv)
   - Skip processing existing IDs from the CSV
3. **Augmentation still occurs:** New IDs are added to players.csv for future runs
4. **Normal downstream processing:** Notifications, API updates, and CSV output work the same way

## Affected Capabilities

- **Execution Modes:** New capability to support multiple execution strategies (normal vs. quick)
- **CLI Interface:** Modified to accept `--quick` flag
- **ID Selection Logic:** Modified to conditionally filter IDs based on execution mode

## Technical Considerations

- **Backward compatibility:** Default behavior (no flag) remains unchanged; existing workflows unaffected
- **players.csv augmentation:** Still happens in quick mode so next run can track new IDs
- **Error handling:** Graceful degradation if API fails in quick mode (falls back to empty list of new IDs)
- **Execution speed:** Quick mode should be faster due to fewer scraping operations

## Specification Deltas

See `specs/execution-modes/spec.md` for detailed requirements.
