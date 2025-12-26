# Design Document: Scrape Rating History

## Architecture

### 1. Table Parsing Enhancement

**Current:** Extract first data row only from the rating history table
```html
<tr><td>Nov/2025</td><td>1800</td><td>1884</td><td>1800</td></tr>  <!-- Extracted -->
<tr><td>Out/2025</td><td>1800</td><td>1914</td><td>1800</td></tr>  <!-- Ignored -->
...
```

**New:** Extract all data rows, deduplicate by month (keeping topmost), then parse each row

```python
def _extract_all_rating_history_from_fide_table(html: str) -> List[Dict]:
    """
    Extract all rating history records from the table, returning one per month.
    For duplicate months, keeps the topmost (most recent) entry.
    Returns list of dicts: [{"month_year": "Nov/2025", "standard": 1800, "rapid": 1884, "blitz": 1800}, ...]
    """
```

### 2. Month-to-Date Mapping

Parse Portuguese month names and map to the last day of the month:

```python
def _parse_month_year_to_date(month_year_str: str) -> Optional[date]:
    """
    Parse "Nov/2025" or "Out/2025" (Portuguese month) to date of last day of month.
    Nov/2025 -> 2025-11-30
    Out/2025 (October) -> 2025-10-31
    """
```

Month mapping:
- Jan/Janeiro → 01
- Fev/Fevereiro → 02
- Mar/Março → 03
- Abr/Abril → 04
- Mai/Maio → 05
- Jun/Junho → 06
- Jul/Julho → 07
- Ago/Agosto → 08
- Set/Setembro → 09
- Out/Outubro → 10
- Nov/Novembro → 11
- Dez/Dezembro → 12

### 3. CSV Storage Model

**Current format (daily, one record per day):**
```
Date,FIDE ID,Player Name,Standard,Rapid,Blitz
2025-12-23,94157,Eduardo Pavinato Klein,1800,1884,1800
```

**New format (monthly, one record per month-year per player - same column name, different date values):**
```
Date,FIDE ID,Player Name,Standard,Rapid,Blitz
2025-11-30,94157,Eduardo Pavinato Klein,1800,1884,1800
2025-10-31,94157,Eduardo Pavinato Klein,1800,1914,1800
2025-09-30,94157,Eduardo Pavinato Klein,1800,1924,1800
```

**Storage behavior:**
- "Date" column now contains the last day of the month instead of the current date
- Replace existing row if month-year already exists (UPDATE semantics)
- Append new rows for new month-years (INSERT semantics)
- Preserve old records if a month disappears from the table
- No schema migration needed (same column name)

### 4. Historical Ratings Loading

**Current:** Load latest record per player from CSV

**New:** Load all monthly records per player (entire history), indexed by month

```python
def load_historical_ratings_by_player_monthly(filepath: str) -> Dict[str, List[Dict]]:
    """
    Returns: {
        fide_id: [
            {"Month": "2025-11-30", "Standard": 1800, "Rapid": 1884, ...},
            {"Month": "2025-10-31", "Standard": 1800, "Rapid": 1914, ...},
            ...
        ]
    }
    """
```

### 5. Change Detection

**Current:** Compare latest scraped ratings to last stored record

**New:** Detect months that exist in scraped history but not in stored history

```python
def detect_new_months(
    fide_id: str,
    scraped_history: List[Dict],  # From _extract_all_rating_history_from_fide_table
    stored_history: Dict[str, List[Dict]]  # From load_historical_ratings_by_player_monthly
) -> List[Dict]:
    """
    Returns list of new month records to notify on.
    Compares month-year values; new months are those in scraped_history but not in stored_history.

    Example return:
    [
        {"month": "2025-11-30", "standard": 1800, "rapid": 1884, "blitz": 1800}
    ]
    """
```

### 6. Notification Logic

**Current:** Notifications for any rating change

**New:** Notifications only for new months

```python
def send_batch_notifications(...):
    """
    Process results and send notifications ONLY for players with new months detected.
    Skip players with 'new_months': [] (empty list = no changes).
    """
```

## Deduplication Strategy

When a month appears multiple times in the scraped table (like June appearing twice in the example), keep the topmost entry:

```python
def _deduplicate_by_month(history_rows: List[Dict]) -> List[Dict]:
    """
    When month appears multiple times, keep first occurrence (topmost, most recent).
    Input: [{"month_year": "Nov/2025", ...}, {"month_year": "Jun/2025", ...}, {"month_year": "Jun/2025", ...}]
    Output: [{"month_year": "Nov/2025", ...}, {"month_year": "Jun/2025", ...}]  # Second Jun removed
    """
```

## Implementation Sequence

1. Add month parsing and date mapping functions
2. Extract all history rows from table (replace single-row extraction)
3. Implement deduplication logic
4. Update historical data loading to work with monthly records
5. Modify change detection to find new months
6. Update notification logic to only trigger on new months
7. Update tests for all new functionality
