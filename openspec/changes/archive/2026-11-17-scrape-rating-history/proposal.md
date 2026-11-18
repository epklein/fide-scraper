# Change Proposal: Scrape Rating History

**Change ID:** `scrape-rating-history`

**Scope:** Enhanced scraping to extract full rating history per player and detect new monthly records.

## Summary

This change extends the FIDE scraper from extracting only the most recent rating record to scraping the complete rating history available on each player's profile. Each monthly record is mapped to the last day of that month and stored with monthly granularity. Notifications are triggered only when new months are detected in the scraped history.

## Why

### Problem

Currently, the scraper only captures the most recent rating for each player per day, missing the complete historical record that FIDE makes available on each player's profile page. This limits trend analysis and means that if the scraper is inactive for a period, previously available historical data is lost.

### Solution

By scraping the complete rating history table from FIDE profiles and storing records monthly instead of daily, we can:
- Build a complete historical record of each player's ratings
- Detect when new historical months become available on FIDE (e.g., when a month's data is finalized and frozen in the history)
- Reduce notification noise by only alerting when genuinely new data appears, not on every daily refresh
- Support recovery from scraper downtime by capturing all available history in the next run

## Motivation

- **Improved history tracking:** Capture all available historical ratings instead of just the latest, allowing better trend analysis
- **Intelligent change detection:** By storing monthly records, we can detect when new months appear in the rating history
- **Noise reduction:** Notifications only trigger for new data (new months), not for each daily refresh of the same month
- **Better reconciliation:** Complete historical data allows catching up missed months if the scraper was inactive

## Key Changes

1. **Enhanced table parsing:** Extract all data rows from the rating history table (not just the first row)
2. **Month deduplication:** When a month appears multiple times in the table, keep only the most recent (topmost) entry
3. **Date mapping:** Map month/year strings (e.g., "Nov/2025") to the last day of that month (e.g., "2025-11-30")
4. **Monthly storage model:** Change CSV storage from one row per day to one row per month per player, replacing existing month entries
5. **History comparison:** Compare entire scraped history against stored history to identify new months
6. **Selective notifications:** Only trigger email/API notifications when new months are added to the history

## Affected Capabilities

- **Rating History Extraction:** New capability to extract multiple historical records per player
- **Date Mapping:** New capability to map month/year to specific dates
- **Rating Storage:** Modified to use monthly granularity instead of daily
- **Change Detection:** Modified to detect new months in history rather than daily changes
- **Notification Logic:** Modified to only notify on new months

## Technical Considerations

- **Backward compatibility:** CSV "Date" column now contains monthly dates (last day of month) instead of daily dates; no schema migration needed
- **Deduplication strategy:** For repeated months, keep the topmost entry (most recent)
- **Storage efficiency:** Monthly granularity reduces redundant daily entries for unchanged months
- **Partial history:** System handles incomplete historical data and fills in missing months on subsequent runs

## Specification Deltas

See `specs/rating-history-extraction/spec.md` and `specs/change-detection/spec.md` for detailed requirements.
