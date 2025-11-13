# Process Improvement: HTML Structure Documentation for Web Scraping

## Problem Identified

The initial implementation failed because the HTML structure of the target website (FIDE) was not documented during the research phase. The implementation attempted to use generic selectors that didn't match the actual website structure.

## Root Cause

The research phase (`/speckit.plan` Phase 0) did not include a mandatory step to inspect and document the actual HTML structure of websites being scraped. The research.md file noted that "HTML structure needs to be inspected at implementation time" but didn't require it to be completed before moving to implementation.

## Recommended Process Improvement

### For Planning Phase (`/speckit.plan`)

**Add to Phase 0: Outline & Research**:

When the feature involves web scraping, add a mandatory research step:

```markdown
### Phase 0: Outline & Research

[... existing steps ...]

4. **For Web Scraping Projects**: HTML Structure Inspection (MANDATORY)
   - Fetch actual target webpage(s) using the identified URL pattern
   - Inspect HTML structure using browser DevTools or automated inspection
   - Document exact CSS selectors, class names, data attributes, or XPath expressions
   - Test selectors with multiple sample pages to ensure consistency
   - Document fallback strategies if primary selectors fail
   - Include HTML structure samples in research.md
   
   **Output**: research.md must contain:
   - Exact selectors for all data to be extracted
   - HTML structure examples
   - Selector reliability notes (e.g., "stable", "may change", "requires testing")
   - Fallback selector strategies
```

### For Tasks Phase (`/speckit.tasks`)

**Add reference to HTML structure in implementation tasks**:

When generating tasks for HTML parsing, reference the documented selectors from research.md:

```markdown
- [ ] T014 [US1] Implement HTML parsing function to extract standard rating 
      using selector from research.md: `[selector from research]`
```

### Updated Research Template Section

Add this section to research.md template for web scraping projects:

```markdown
## HTML Structure Inspection

**Status**: ✅ Complete / ⚠️ Requires Inspection

**Inspection Method**: [Browser DevTools / Automated script / Manual inspection]

**Target URL Pattern**: [URL pattern used for inspection]

**Sample URLs Tested**:
- [URL 1] - [Description]
- [URL 2] - [Description]

**Documented Selectors**:

**Standard Rating**:
- Primary selector: `[CSS selector or XPath]`
- Fallback selector: `[alternative if primary fails]`
- HTML example:
  ```html
  [actual HTML snippet]
  ```

**Rapid Rating**:
- Primary selector: `[CSS selector or XPath]`
- Fallback selector: `[alternative if primary fails]`
- HTML example:
  ```html
  [actual HTML snippet]
  ```

**Selector Reliability**:
- [ ] Selectors tested on multiple pages
- [ ] Selectors work consistently
- [ ] Fallback strategies documented
- [ ] Known limitations documented

**Notes**:
- [Any important notes about structure, dynamic content, etc.]
```

## Implementation

### Immediate Action for This Project

1. ✅ Updated research.md with HTML Structure Inspection section template
2. ⏳ **TODO**: Actually inspect FIDE website and fill in the selectors
3. ⏳ **TODO**: Update implementation to use documented selectors
4. ⏳ **TODO**: Test with multiple FIDE IDs to verify selector reliability

### Long-term Process Update

1. Update `.cursor/commands/speckit.plan.md` to include mandatory HTML inspection step
2. Update `.specify/templates/plan-template.md` to prompt for HTML structure research
3. Update `.specify/templates/research-template.md` (if exists) with HTML structure section

## Benefits

1. **Prevents Implementation Failures**: Catch selector issues before coding
2. **Faster Implementation**: Developers have exact selectors ready
3. **Better Testing**: Tests can use actual HTML structure
4. **Easier Maintenance**: Documented selectors help when website changes
5. **Knowledge Sharing**: Future developers understand the structure

## Example: What Should Have Been Documented

```markdown
## HTML Structure Inspection

**Status**: ✅ Complete

**Inspection Method**: Browser DevTools + BeautifulSoup inspection script

**Target URL Pattern**: `https://ratings.fide.com/profile/{fide_id}`

**Sample URLs Tested**:
- https://ratings.fide.com/profile/538026660 (Magnus Carlsen)
- https://ratings.fide.com/profile/2016892 (Hikaru Nakamura)

**Documented Selectors**:

**Standard Rating**:
- Primary selector: `div.profile-top-rating-data:first-child span`
- Fallback selector: `div[data-rating-type="standard"]`
- HTML example:
  ```html
  <div class="profile-top-rating-data">
    <span>2830</span>
  </div>
  ```

**Rapid Rating**:
- Primary selector: `div.profile-top-rating-data:last-child span`
- Fallback selector: `div[data-rating-type="rapid"]`
- HTML example:
  ```html
  <div class="profile-top-rating-data">
    <span>2780</span>
  </div>
  ```

**Selector Reliability**:
- ✅ Selectors tested on multiple pages
- ✅ Selectors work consistently
- ✅ Fallback strategies documented
- ⚠️ Structure may change if FIDE updates their website

**Notes**:
- Ratings are in the first two `profile-top-rating-data` divs
- Standard rating is typically first, rapid is second
- If only one rating exists, it may be in either position
```

