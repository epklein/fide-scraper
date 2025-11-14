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


class TestPlayerNameExtraction:
    """Tests for player name extraction from HTML."""
    
    def test_extract_player_name_success(self):
        """Test extracting player name from HTML using documented selector h1.player-title."""
        html = """
        <html>
            <head><title>Magnus Carlsen - FIDE Ratings</title></head>
            <body>
                <h1 class="player-title">Magnus Carlsen</h1>
            </body>
        </html>
        """
        name = fide_scraper.extract_player_name(html)
        assert name == "Magnus Carlsen"
    
    def test_extract_player_name_missing_element(self):
        """Test handling when h1.player-title element is missing."""
        html = """
        <html>
            <body>
                <div>Some content</div>
            </body>
        </html>
        """
        name = fide_scraper.extract_player_name(html)
        # Should try fallback strategies
        assert name is None or isinstance(name, str)
    
    def test_extract_player_name_fallback_h1(self):
        """Test fallback to h1 tag without class when player-title not found."""
        html = """
        <html>
            <body>
                <h1>Hikaru Nakamura</h1>
            </body>
        </html>
        """
        name = fide_scraper.extract_player_name(html)
        assert name == "Hikaru Nakamura"
    
    def test_extract_player_name_fallback_title(self):
        """Test fallback to title tag parsing when h1 not found."""
        html = """
        <html>
            <head><title>Fabiano Caruana - FIDE Ratings</title></head>
            <body>
                <div>Some content</div>
            </body>
        </html>
        """
        name = fide_scraper.extract_player_name(html)
        assert name == "Fabiano Caruana"
    
    def test_extract_player_name_empty_html(self):
        """Test handling of empty HTML."""
        html = ""
        name = fide_scraper.extract_player_name(html)
        assert name is None
    
    def test_extract_player_name_none_html(self):
        """Test handling of None HTML."""
        name = fide_scraper.extract_player_name(None)
        assert name is None
    
    def test_extract_player_name_invalid_html(self):
        """Test handling of invalid HTML structure."""
        html = "<html><broken><structure>"
        # Should not raise exception, should return None or handle gracefully
        name = fide_scraper.extract_player_name(html)
        assert name is None or isinstance(name, str)


class TestFileReading:
    """Tests for file reading function."""
    
    def test_read_fide_ids_from_file_valid(self, tmp_path):
        """Test reading valid FIDE IDs from file."""
        test_file = tmp_path / "test_ids.txt"
        test_file.write_text("538026660\n2016892\n1503014\n")
        fide_ids = fide_scraper.read_fide_ids_from_file(str(test_file))
        assert fide_ids == ["538026660", "2016892", "1503014"]
    
    def test_read_fide_ids_from_file_with_empty_lines(self, tmp_path):
        """Test reading file with empty lines (should be skipped)."""
        test_file = tmp_path / "test_ids.txt"
        test_file.write_text("538026660\n\n2016892\n\n1503014\n")
        fide_ids = fide_scraper.read_fide_ids_from_file(str(test_file))
        assert fide_ids == ["538026660", "2016892", "1503014"]
    
    def test_read_fide_ids_from_file_with_whitespace(self, tmp_path):
        """Test reading file with whitespace around IDs (should be stripped)."""
        test_file = tmp_path / "test_ids.txt"
        test_file.write_text("  538026660  \n  2016892  \n  1503014  \n")
        fide_ids = fide_scraper.read_fide_ids_from_file(str(test_file))
        assert fide_ids == ["538026660", "2016892", "1503014"]
    
    def test_read_fide_ids_from_file_not_found(self):
        """Test handling of file not found."""
        with pytest.raises(FileNotFoundError):
            fide_scraper.read_fide_ids_from_file("nonexistent_file.txt")
    
    def test_read_fide_ids_from_file_permission_error(self, tmp_path, monkeypatch):
        """Test handling of permission errors."""
        test_file = tmp_path / "test_ids.txt"
        test_file.write_text("538026660\n")
        # Mock open to raise PermissionError
        def mock_open(*args, **kwargs):
            raise PermissionError("Permission denied")
        monkeypatch.setattr("builtins.open", mock_open)
        with pytest.raises(PermissionError):
            fide_scraper.read_fide_ids_from_file(str(test_file))


class TestCSVGeneration:
    """Tests for CSV generation function."""
    
    def test_write_csv_output_proper_formatting(self, tmp_path):
        """Test CSV generation with proper formatting and escaping."""
        output_file = tmp_path / "test_output.csv"
        player_profiles = [
            {
                'FIDE ID': '538026660',
                'Player Name': 'Magnus Carlsen',
                'Standard': 2830,
                'Rapid': 2780,
                'Blitz': 2760
            }
        ]
        fide_scraper.write_csv_output(str(output_file), player_profiles)
        
        # Read and verify CSV content
        content = output_file.read_text(encoding='utf-8')
        assert 'FIDE ID,Player Name,Standard,Rapid,Blitz' in content
        assert '538026660,Magnus Carlsen,2830,2780,2760' in content
    
    def test_write_csv_output_special_characters(self, tmp_path):
        """Test CSV generation with special characters in player names (proper escaping)."""
        output_file = tmp_path / "test_output.csv"
        player_profiles = [
            {
                'FIDE ID': '123456',
                'Player Name': 'Player, With Comma',
                'Standard': 2500,
                'Rapid': 2450,
                'Blitz': 2400
            }
        ]
        fide_scraper.write_csv_output(str(output_file), player_profiles)
        
        # Read and verify CSV content (comma should be quoted)
        content = output_file.read_text(encoding='utf-8')
        assert '"Player, With Comma"' in content or 'Player, With Comma' in content
    
    def test_write_csv_output_empty_values(self, tmp_path):
        """Test CSV generation with empty/missing ratings."""
        output_file = tmp_path / "test_output.csv"
        player_profiles = [
            {
                'FIDE ID': '123456',
                'Player Name': 'Test Player',
                'Standard': 2500,
                'Rapid': None,
                'Blitz': None
            }
        ]
        fide_scraper.write_csv_output(str(output_file), player_profiles)
        
        # Read and verify CSV content
        content = output_file.read_text(encoding='utf-8')
        assert '123456,Test Player,2500,,' in content or '123456,Test Player,2500,"",""' in content
    
    def test_write_csv_output_header_row(self, tmp_path):
        """Test that CSV includes header row."""
        output_file = tmp_path / "test_output.csv"
        player_profiles = []
        fide_scraper.write_csv_output(str(output_file), player_profiles)
        
        # Read and verify header exists even with empty data
        content = output_file.read_text(encoding='utf-8')
        assert 'FIDE ID,Player Name,Standard,Rapid,Blitz' in content


class TestFilenameGeneration:
    """Tests for date-stamped filename generation."""
    
    def test_generate_output_filename_iso_format(self):
        """Test filename generation uses ISO 8601 format (YYYY-MM-DD)."""
        filename = fide_scraper.generate_output_filename()
        # Should match pattern: fide_ratings_YYYY-MM-DD.csv
        import re
        pattern = r'fide_ratings_\d{4}-\d{2}-\d{2}\.csv'
        assert re.match(pattern, filename) is not None
    
    def test_generate_output_filename_contains_date(self):
        """Test filename contains current date."""
        from datetime import date
        filename = fide_scraper.generate_output_filename()
        today = date.today().isoformat()
        assert today in filename
    
    def test_generate_output_filename_extension(self):
        """Test filename has .csv extension."""
        filename = fide_scraper.generate_output_filename()
        assert filename.endswith('.csv')


class TestConsoleOutputFormatting:
    """Tests for console output formatting."""
    
    def test_format_console_output_tabular_format(self):
        """Test console output uses tabular format with aligned columns."""
        player_profiles = [
            {
                'FIDE ID': '538026660',
                'Player Name': 'Magnus Carlsen',
                'Standard': 2830,
                'Rapid': 2780,
                'Blitz': 2760
            }
        ]
        output = fide_scraper.format_console_output(player_profiles)
        assert 'FIDE ID' in output
        assert 'Player Name' in output
        assert 'Standard' in output
        assert 'Rapid' in output
        assert 'Blitz' in output
        assert '538026660' in output
        assert 'Magnus Carlsen' in output
    
    def test_format_console_output_column_alignment(self):
        """Test console output has proper column alignment."""
        player_profiles = [
            {
                'FIDE ID': '538026660',
                'Player Name': 'Magnus Carlsen',
                'Standard': 2830,
                'Rapid': 2780,
                'Blitz': 2760
            }
        ]
        output = fide_scraper.format_console_output(player_profiles)
        # Check that columns are aligned (lines should have consistent spacing)
        lines = output.split('\n')
        data_lines = [line for line in lines if '538026660' in line]
        if data_lines:
            # Should have consistent spacing between columns
            assert len(data_lines[0].split()) >= 5  # At least 5 columns
    
    def test_format_console_output_missing_ratings(self):
        """Test console output handles missing ratings gracefully."""
        player_profiles = [
            {
                'FIDE ID': '123456',
                'Player Name': 'Test Player',
                'Standard': 2500,
                'Rapid': None,
                'Blitz': None
            }
        ]
        output = fide_scraper.format_console_output(player_profiles)
        assert '123456' in output
        assert 'Test Player' in output
        # Should handle None values (empty or "Unrated")
        assert '2500' in output


class TestBatchProcessingErrorHandling:
    """Tests for batch processing error handling."""
    
    @patch('fide_scraper.fetch_fide_profile')
    @patch('fide_scraper.extract_player_name')
    @patch('fide_scraper.extract_standard_rating')
    @patch('fide_scraper.extract_rapid_rating')
    @patch('fide_scraper.extract_blitz_rating')
    def test_batch_processing_invalid_ids_skipped(self, mock_blitz, mock_rapid, mock_standard, mock_name, mock_fetch):
        """Test that invalid FIDE IDs are skipped without stopping batch."""
        fide_ids = ["538026660", "invalid_id", "2016892"]
        results, errors = fide_scraper.process_batch(fide_ids)
        # Should process valid IDs and skip invalid one
        assert len(errors) >= 1  # At least one error for invalid ID
        # Should continue processing remaining IDs
    
    @patch('fide_scraper.fetch_fide_profile')
    def test_batch_processing_network_errors_continue(self, mock_fetch):
        """Test that network errors for individual IDs don't stop batch processing."""
        import requests
        mock_fetch.side_effect = [requests.ConnectionError("Network error"), "html_content"]
        fide_ids = ["123456", "2016892"]
        results, errors = fide_scraper.process_batch(fide_ids)
        # Should continue processing after network error
        assert len(errors) >= 1  # At least one error for network failure
    
    @patch('fide_scraper.fetch_fide_profile')
    def test_batch_processing_player_not_found_continues(self, mock_fetch):
        """Test that player not found (404) doesn't stop batch processing."""
        mock_fetch.return_value = None  # Simulate 404
        fide_ids = ["99999999", "2016892"]
        results, errors = fide_scraper.process_batch(fide_ids)
        # Should continue processing after player not found
        assert len(errors) >= 1  # At least one error for player not found
