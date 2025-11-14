# Research: FIDE Rating Scraper

**Date**: 2025-01-27  
**Purpose**: Resolve technical unknowns identified in Technical Context

## Web Scraping Library Decision

**Decision**: Use `requests` + `beautifulsoup4` for web scraping

**Rationale**:
- Simple, lightweight, and well-established libraries
- Perfect for single-page scraping tasks
- Minimal dependencies (only 2 packages)
- Easy to test and mock
- Widely used and well-documented
- No need for full framework like Scrapy for this simple use case

**Alternatives considered**:
- **Scrapy**: Too heavy for a simple script; designed for large-scale crawling
- **httpx**: Modern alternative to requests, but requests is more widely adopted and sufficient
- **Selenium/Playwright**: Overkill; FIDE website doesn't require JavaScript rendering for basic profile data

## FIDE Website Structure

**Decision**: FIDE player profile URL pattern: `https://ratings.fide.com/profile/{fide_id}`

**Rationale**:
- Standard FIDE ratings website structure
- Profile pages contain standard, rapid, and blitz ratings

**Alternatives considered**:
- FIDE API: No official public API available for ratings lookup
- Alternative endpoints: Standard profile URL is the primary method

## HTML Structure Inspection

**Status**: ✅ **COMPLETE** - HTML structure inspected and documented

**Required Steps**:
1. Fetch a known player profile page (e.g., FIDE ID: 538026660 - Magnus Carlsen)
2. Inspect the HTML structure using browser DevTools or BeautifulSoup
3. Identify exact CSS selectors, class names, or data attributes for:
   - Standard rating element
   - Rapid rating element
   - Blitz rating element
4. Document the selectors with examples
5. Test selectors with multiple player profiles to ensure consistency

**Documentation Format**:
```html
<!-- Example structure to document -->
<div class="profile-games ">
    <div class="profile-standart profile-game ">
        <img src="/img/logo_std.svg" alt="standart" height=25>
        <p>Not rated</p><p style="font-size: 8px; padding:0; margin:0;">STANDARD <span class=inactiv_note></span></p>
    </div>
    <div class="profile-rapid profile-game ">
        <img src="/img/logo_rpd.svg" alt="rapid"  height=25>
        <p>1577</p><p style="font-size: 8px; padding:0; margin:0;">RAPID<span class=inactiv_note></p>
    </div>
    <div class="profile-blitz profile-game ">
        <img src="/img/logo_blitz.svg " alt="blitz"  height=25>
        <p>Not rated</p><p style="font-size: 8px; padding:0; margin:0;">BLITZ<span class=inactiv_note></p>
    </div>
    <!--profile-games-->
</div>
```

**Selectors Documented**:
- Standard rating selector: `div.profile-standart` → first `<p>` tag contains rating
- Rapid rating selector: `div.profile-rapid` → first `<p>` tag contains rating
- Blitz rating selector: `div.profile-blitz` → first `<p>` tag contains rating
- Note: FIDE website uses "standart" (typo) instead of "standard" in the class name
- Unrated indicator: `<p>` tag contains "Not rated" text

**Selector Reliability**:
- ✅ Selectors tested on actual FIDE profile pages
- ✅ Selectors work consistently across different player profiles
- ✅ Handles "Not rated" cases properly
- ⚠️ Structure may change if FIDE updates their website

## HTML Parsing Approach

**Decision**: Use BeautifulSoup with 'html.parser' (built-in parser)

**Rationale**:
- No additional dependencies required
- Sufficient for parsing static HTML
- Fast and reliable for simple extraction tasks
- Cross-platform compatibility

**Alternatives considered**:
- **lxml parser**: Faster but requires additional C dependencies
- **html5lib**: More lenient but slower and heavier

## Error Handling Strategy

**Decision**: Implement comprehensive error handling for:
- Network errors (connection timeouts, DNS failures)
- HTTP errors (404, 500, etc.)
- HTML parsing errors (missing elements, structure changes)
- Invalid FIDE ID format

**Rationale**:
- User experience requires clear error messages (per FR-006)
- Network reliability cannot be assumed
- Website structure may change over time
- Input validation prevents unnecessary network calls

## FIDE ID Validation

**Decision**: Validate FIDE ID format before making network requests

**Rationale**:
- FIDE IDs are numeric strings (typically 6-8 digits)
- Early validation provides immediate feedback
- Reduces unnecessary network calls
- Improves user experience

**Note**: Exact format validation rules will be determined during implementation based on FIDE's actual ID format.
