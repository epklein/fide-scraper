"""
Integration tests for fide_scraper.py

These tests require network access and may make actual HTTP requests.
"""

import pytest
import sys
import os

# Add parent directory to path to import fide_scraper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fide_scraper


@pytest.mark.integration
class TestEndToEndFlow:
    """Integration tests for end-to-end flow."""
    
    def test_end_to_end_with_valid_fide_id(self):
        """Test complete flow with a known valid FIDE ID."""
        # Using a well-known player ID (Magnus Carlsen: 538026660)
        fide_id = "538026660"
        
        # Validate FIDE ID
        assert fide_scraper.validate_fide_id(fide_id) == True
        
        # Fetch profile
        html = fide_scraper.fetch_fide_profile(fide_id)
        assert html is not None
        
        # Extract ratings
        standard = fide_scraper.extract_standard_rating(html)
        rapid = fide_scraper.extract_rapid_rating(html)
        blitz = fide_scraper.extract_blitz_rating(html)
        
        # At least one rating should be present
        assert standard is not None or rapid is not None or blitz is not None
    
    def test_end_to_end_invalid_fide_id(self):
        """Test complete flow with invalid FIDE ID."""
        fide_id = "invalid123"
        
        # Should fail validation
        assert fide_scraper.validate_fide_id(fide_id) == False
    
    def test_end_to_end_nonexistent_fide_id(self):
        """Test complete flow with non-existent FIDE ID."""
        # Use a very large number that likely doesn't exist
        fide_id = "99999999"
        
        # Should pass validation
        assert fide_scraper.validate_fide_id(fide_id) == True
        
        # But fetch should fail or return no ratings
        html = fide_scraper.fetch_fide_profile(fide_id)
        # Either None (404) or HTML with no ratings
        if html:
            standard = fide_scraper.extract_standard_rating(html)
            rapid = fide_scraper.extract_rapid_rating(html)
            blitz = fide_scraper.extract_blitz_rating(html)
            # All should be None for non-existent player
            assert standard is None
            assert rapid is None
            assert blitz is None


@pytest.mark.integration
class TestEdgeCases:
    """Integration tests for edge cases."""
    
    def test_unrated_player(self):
        """Test handling of unrated players using documented HTML structure."""
        # Use the exact HTML structure from research.md for unrated case
        html = """
        <div class="profile-games ">
            <div class="profile-standart profile-game ">
                <img src="/img/logo_std.svg" alt="standart" height=25>
                <p>Not rated</p>
                <p style="font-size: 8px; padding:0; margin:0;">STANDARD <span class=inactiv_note></span></p>
            </div>
            <div class="profile-rapid profile-game ">
                <img src="/img/logo_rpd.svg" alt="rapid" height=25>
                <p>Not rated</p>
                <p style="font-size: 8px; padding:0; margin:0;">RAPID<span class=inactiv_note></p>
            </div>
            <div class="profile-blitz profile-game ">
                <img src="/img/logo_blitz.svg" alt="blitz" height=25>
                <p>Not rated</p>
                <p style="font-size: 8px; padding:0; margin:0;">BLITZ<span class=inactiv_note></p>
            </div>
        </div>
        """
        standard = fide_scraper.extract_standard_rating(html)
        rapid = fide_scraper.extract_rapid_rating(html)
        blitz = fide_scraper.extract_blitz_rating(html)
        # Should return None for unrated without raising exception
        assert standard is None
        assert rapid is None
        assert blitz is None
    
    def test_missing_ratings(self):
        """Test handling when one rating is missing using documented HTML structure."""
        # Test HTML with only standard rating (matches research.md structure)
        html = """
        <div class="profile-games ">
            <div class="profile-standart profile-game ">
                <img src="/img/logo_std.svg" alt="standart" height=25>
                <p>2500</p>
                <p style="font-size: 8px; padding:0; margin:0;">STANDARD <span class=inactiv_note></span></p>
            </div>
            <!-- Rapid rating div missing -->
        </div>
        """
        standard = fide_scraper.extract_standard_rating(html)
        rapid = fide_scraper.extract_rapid_rating(html)
        blitz = fide_scraper.extract_blitz_rating(html)
        # Standard should be found, rapid and blitz should be None
        assert standard == 2500
        assert rapid is None
        assert blitz is None
    
    def test_format_output_unrated(self):
        """Test formatting output with unrated ratings."""
        output = fide_scraper.format_ratings_output(2500, None, None)
        assert "Standard: 2500" in output
        assert "Rapid: Unrated" in output
        assert "Blitz: Unrated" in output
        
        output = fide_scraper.format_ratings_output(None, 2450, 2400)
        assert "Standard: Unrated" in output
        assert "Rapid: 2450" in output
        assert "Blitz: 2400" in output
        
        output = fide_scraper.format_ratings_output(2500, 2450, None)
        assert "Standard: 2500" in output
        assert "Rapid: 2450" in output
        assert "Blitz: Unrated" in output
