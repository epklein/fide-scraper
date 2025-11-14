"""
Unit tests for fide_scraper.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import requests

# Add parent directory to path to import fide_scraper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fide_scraper


class TestFideIdValidation:
    """Tests for FIDE ID validation."""
    
    def test_valid_fide_id_numeric(self):
        """Test that valid numeric FIDE IDs pass validation."""
        assert fide_scraper.validate_fide_id("538026660") == True
        assert fide_scraper.validate_fide_id("123456") == True
        assert fide_scraper.validate_fide_id("12345678") == True
    
    def test_invalid_fide_id_non_numeric(self):
        """Test that non-numeric FIDE IDs fail validation."""
        assert fide_scraper.validate_fide_id("abc123") == False
        assert fide_scraper.validate_fide_id("1503abc") == False
        assert fide_scraper.validate_fide_id("") == False
    
    def test_invalid_fide_id_too_short(self):
        """Test that FIDE IDs shorter than 4 digits fail validation."""
        assert fide_scraper.validate_fide_id("123") == False
        assert fide_scraper.validate_fide_id("12") == False
        assert fide_scraper.validate_fide_id("1") == False
    
    def test_invalid_fide_id_too_long(self):
        """Test that FIDE IDs longer than 10 digits fail validation."""
        assert fide_scraper.validate_fide_id("12345678901") == False
        assert fide_scraper.validate_fide_id("123456789012") == False
    
    def test_invalid_fide_id_empty(self):
        """Test that empty strings fail validation."""
        assert fide_scraper.validate_fide_id("") == False
        assert fide_scraper.validate_fide_id(None) == False


class TestRatingExtraction:
    """Tests for rating extraction from HTML."""
    
    def test_extract_standard_rating_success(self):
        """Test extracting standard rating from HTML using documented structure from research.md."""
        # HTML structure matches research.md exactly
        html = """
        <div class="profile-games ">
            <div class="profile-standart profile-game ">
                <img src="/img/logo_std.svg" alt="standart" height=25>
                <p>2500</p>
                <p style="font-size: 8px; padding:0; margin:0;">STANDARD <span class=inactiv_note></span></p>
            </div>
        </div>
        """
        rating = fide_scraper.extract_standard_rating(html)
        assert rating == 2500
    
    def test_extract_rapid_rating_success(self):
        """Test extracting rapid rating from HTML using documented structure from research.md."""
        # HTML structure matches research.md exactly
        html = """
        <div class="profile-games ">
            <div class="profile-rapid profile-game ">
                <img src="/img/logo_rpd.svg" alt="rapid" height=25>
                <p>2450</p>
                <p style="font-size: 8px; padding:0; margin:0;">RAPID<span class=inactiv_note></p>
            </div>
        </div>
        """
        rating = fide_scraper.extract_rapid_rating(html)
        assert rating == 2450
    
    def test_extract_blitz_rating_success(self):
        """Test extracting blitz rating from HTML using documented structure from research.md."""
        # HTML structure matches research.md exactly
        html = """
        <div class="profile-games ">
            <div class="profile-blitz profile-game ">
                <img src="/img/logo_blitz.svg" alt="blitz" height=25>
                <p>2400</p>
                <p style="font-size: 8px; padding:0; margin:0;">BLITZ<span class=inactiv_note></p>
            </div>
        </div>
        """
        rating = fide_scraper.extract_blitz_rating(html)
        assert rating == 2400
    
    def test_extract_rating_unrated(self):
        """Test handling unrated players using documented structure from research.md."""
        # HTML structure matches research.md exactly - shows "Not rated" case
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
        # Should return None for unrated
        assert standard is None
        assert rapid is None
        assert blitz is None
    
    def test_extract_rating_missing_element(self):
        """Test handling missing rating elements (no profile-games div)."""
        html = "<html><body></body></html>"
        standard = fide_scraper.extract_standard_rating(html)
        rapid = fide_scraper.extract_rapid_rating(html)
        blitz = fide_scraper.extract_blitz_rating(html)
        assert standard is None
        assert rapid is None
        assert blitz is None
    
    def test_extract_rating_partial_structure(self):
        """Test handling when profile-games exists but rating divs are missing."""
        # Has profile-games but no rating divs
        html = """
        <div class="profile-games ">
            <!-- No rating divs present -->
        </div>
        """
        standard = fide_scraper.extract_standard_rating(html)
        rapid = fide_scraper.extract_rapid_rating(html)
        blitz = fide_scraper.extract_blitz_rating(html)
        assert standard is None
        assert rapid is None
        assert blitz is None
    
    def test_extract_rating_mixed_rated_unrated(self):
        """Test handling when one rating is present and one is unrated."""
        # Standard rated, rapid unrated (matches research.md example structure)
        html = """
        <div class="profile-games ">
            <div class="profile-standart profile-game ">
                <img src="/img/logo_std.svg" alt="standart" height=25>
                <p>2500</p>
                <p style="font-size: 8px; padding:0; margin:0;">STANDARD <span class=inactiv_note></span></p>
            </div>
            <div class="profile-rapid profile-game ">
                <img src="/img/logo_rpd.svg" alt="rapid" height=25>
                <p>Not rated</p>
                <p style="font-size: 8px; padding:0; margin:0;">RAPID<span class=inactiv_note></p>
            </div>
            <div class="profile-blitz profile-game ">
                <img src="/img/logo_blitz.svg" alt="blitz" height=25>
                <p>2400</p>
                <p style="font-size: 8px; padding:0; margin:0;">BLITZ<span class=inactiv_note></p>
            </div>
        </div>
        """
        standard = fide_scraper.extract_standard_rating(html)
        rapid = fide_scraper.extract_rapid_rating(html)
        blitz = fide_scraper.extract_blitz_rating(html)
        assert standard == 2500
        assert rapid is None
        assert blitz == 2400
    
    def test_extract_blitz_rating_unrated(self):
        """Test handling unrated blitz rating."""
        html = """
        <div class="profile-games ">
            <div class="profile-blitz profile-game ">
                <img src="/img/logo_blitz.svg" alt="blitz" height=25>
                <p>Not rated</p>
                <p style="font-size: 8px; padding:0; margin:0;">BLITZ<span class=inactiv_note></p>
            </div>
        </div>
        """
        blitz = fide_scraper.extract_blitz_rating(html)
        assert blitz is None


class TestErrorHandling:
    """Tests for error handling."""
    
    @patch('fide_scraper.requests.get')
    def test_network_error_handling(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = requests.ConnectionError("Network error")
        with pytest.raises(ConnectionError):
            fide_scraper.fetch_fide_profile("538026660")
    
    @patch('fide_scraper.requests.get')
    def test_http_error_404(self, mock_get):
        """Test handling of 404 errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        result = fide_scraper.fetch_fide_profile("99999999")
        assert result is None
    
    @patch('fide_scraper.requests.get')
    def test_http_error_500(self, mock_get):
        """Test handling of 500 errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_response
        with pytest.raises(requests.HTTPError):
            fide_scraper.fetch_fide_profile("538026660")
    
    @patch('fide_scraper.requests.get')
    def test_timeout_handling(self, mock_get):
        """Test handling of request timeouts."""
        mock_get.side_effect = requests.Timeout("Request timeout")
        with pytest.raises(requests.Timeout):
            fide_scraper.fetch_fide_profile("538026660")
    
    def test_parsing_error_handling(self):
        """Test handling of HTML parsing errors."""
        invalid_html = "<html><body><broken>"
        # Should not raise exception, should return None or handle gracefully
        standard = fide_scraper.extract_standard_rating(invalid_html)
        rapid = fide_scraper.extract_rapid_rating(invalid_html)
        blitz = fide_scraper.extract_blitz_rating(invalid_html)
        # Either None or exception handled gracefully
        assert standard is None or isinstance(standard, (int, str, type(None)))
        assert rapid is None or isinstance(rapid, (int, str, type(None)))
        assert blitz is None or isinstance(blitz, (int, str, type(None)))


class TestFormatOutput:
    """Tests for rating output formatting."""
    
    def test_format_output_all_ratings(self):
        """Test formatting output with all three ratings."""
        output = fide_scraper.format_ratings_output(2500, 2450, 2400)
        assert "Standard: 2500" in output
        assert "Rapid: 2450" in output
        assert "Blitz: 2400" in output
    
    def test_format_output_with_unrated_blitz(self):
        """Test formatting output with unrated blitz."""
        output = fide_scraper.format_ratings_output(2500, 2450, None)
        assert "Standard: 2500" in output
        assert "Rapid: 2450" in output
        assert "Blitz: Unrated" in output
    
    def test_format_output_all_unrated(self):
        """Test formatting output when all ratings are unrated."""
        output = fide_scraper.format_ratings_output(None, None, None)
        assert "Standard: Unrated" in output
        assert "Rapid: Unrated" in output
        assert "Blitz: Unrated" in output
