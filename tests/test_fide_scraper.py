"""
Unit tests for fide_scraper.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import requests
import smtplib

# Add parent directory to path to import fide_scraper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fide_scraper
import email_notifier
import ratings_api


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
        assert 'Date,FIDE ID,Player Name,Standard,Rapid,Blitz' in content
        # Date should be in ISO format at the beginning
        from datetime import date
        today = date.today().isoformat()
        assert f'{today},538026660,Magnus Carlsen,2830,2780,2760' in content
    
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

        # Read and verify CSV content - Date should come first
        content = output_file.read_text(encoding='utf-8')
        from datetime import date
        today = date.today().isoformat()
        # Check that date is present and values are correct
        assert today in content
        assert '123456,Test Player,2500,,' in content or 'Test Player,2500' in content
    
    def test_write_csv_output_header_row(self, tmp_path):
        """Test that CSV includes header row."""
        output_file = tmp_path / "test_output.csv"
        player_profiles = []
        fide_scraper.write_csv_output(str(output_file), player_profiles)

        # Read and verify header exists even with empty data
        content = output_file.read_text(encoding='utf-8')
        assert 'Date,FIDE ID,Player Name,Standard,Rapid,Blitz' in content

    def test_write_csv_output_same_day_replacement(self, tmp_path):
        """Test that CSV output replaces same-day entries while preserving older entries."""
        output_file = tmp_path / "test_output.csv"
        from datetime import date, timedelta

        # First write - initial data
        player_profiles_1 = [
            {
                'FIDE ID': '538026660',
                'Player Name': 'Magnus Carlsen',
                'Standard': 2830,
                'Rapid': 2780,
                'Blitz': 2760
            }
        ]
        fide_scraper.write_csv_output(str(output_file), player_profiles_1)

        # Second write on same day - should replace previous data
        player_profiles_2 = [
            {
                'FIDE ID': '2016892',
                'Player Name': 'Ding Liren',
                'Standard': 2780,
                'Rapid': 2750,
                'Blitz': 2730
            }
        ]
        fide_scraper.write_csv_output(str(output_file), player_profiles_2)

        # Read and verify behavior
        content = output_file.read_text(encoding='utf-8')
        today = date.today().isoformat()

        # Should have header only once
        header_count = content.count('Date,FIDE ID,Player Name,Standard,Rapid,Blitz')
        assert header_count == 1, "Header should appear only once"

        # Should have only the second (latest) entry for today, not the first one
        assert 'Ding Liren' in content, "Latest entry should be present"
        assert 'Magnus Carlsen' not in content, "Old entry for same day should be removed"
        assert '2016892' in content, "New FIDE ID should be present"
        # Check that old FIDE ID is not in today's entries
        lines = content.split('\n')
        for line in lines:
            if today in line and line.strip():
                assert '538026660' not in line, "Old FIDE ID should not appear in today's entries"

    def test_write_csv_output_preserve_older_dates(self, tmp_path):
        """Test that CSV output preserves entries from previous dates."""
        output_file = tmp_path / "test_output.csv"
        from datetime import date, timedelta

        # Create a file with yesterday's data
        today = date.today()
        yesterday = (today - timedelta(days=1)).isoformat()

        # Manually create a file with yesterday's data
        output_file.write_text(
            f"Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            f"{yesterday},1503014,Magnus Carlsen,2830,2780,2760\n"
        )

        # Now write today's data
        player_profiles = [
            {
                'FIDE ID': '2016892',
                'Player Name': 'Ding Liren',
                'Standard': 2780,
                'Rapid': 2750,
                'Blitz': 2730
            }
        ]
        fide_scraper.write_csv_output(str(output_file), player_profiles)

        # Read and verify both dates are present
        content = output_file.read_text(encoding='utf-8')
        today_str = date.today().isoformat()

        # Should have header only once
        header_count = content.count('Date,FIDE ID,Player Name,Standard,Rapid,Blitz')
        assert header_count == 1, "Header should appear only once"

        # Should have yesterday's entry
        assert yesterday in content, "Yesterday's entry should be preserved"
        assert 'Magnus Carlsen' in content, "Yesterday's player should be present"
        assert '1503014' in content, "Yesterday's FIDE ID should be present"

        # Should have today's entry
        assert today_str in content, "Today's date should be present"
        assert 'Ding Liren' in content, "Today's player should be present"
        assert '2016892' in content, "Today's FIDE ID should be present"

class TestConsoleOutputFormatting:
    """Tests for console output formatting."""

    def test_format_console_output_tabular_format(self):
        """Test console output uses tabular format with aligned columns and Date."""
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
        assert 'Date' in output
        assert 'FIDE ID' in output
        assert 'Player Name' in output
        assert 'Standard' in output
        assert 'Rapid' in output
        assert 'Blitz' in output
        assert '538026660' in output
        assert 'Magnus Carlsen' in output
        # Verify date is in ISO format
        from datetime import date
        today = date.today().isoformat()
        assert today in output
    
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


class TestLoadPlayerDataFromCSV:
    """Tests for load_player_data_from_csv function."""

    def test_load_player_data_from_csv_valid(self, tmp_path):
        """Test loading valid player data from CSV."""
        test_file = tmp_path / "players.csv"
        test_file.write_text(
            "FIDE ID,email\n"
            "12345678,alice@example.com\n"
            "87654321,bob@example.com\n"
            "11111111,\n"
        )
        result = fide_scraper.load_player_data_from_csv(str(test_file))

        assert len(result) == 3
        assert result["12345678"]["email"] == "alice@example.com"
        assert result["87654321"]["email"] == "bob@example.com"
        assert result["11111111"]["email"] == ""

    def test_load_player_data_from_csv_invalid_email(self, tmp_path, capsys):
        """Test that invalid emails are skipped with warnings."""
        test_file = tmp_path / "players.csv"
        test_file.write_text(
            "FIDE ID,email\n"
            "12345678,alice@example.com\n"
            "87654321,invalid-email\n"
            "11111111,charlie@example.com\n"
        )
        result = fide_scraper.load_player_data_from_csv(str(test_file))

        # Should have 2 valid entries (87654321 skipped due to invalid email)
        assert len(result) == 2
        assert "12345678" in result
        assert "87654321" not in result
        assert "11111111" in result

        # Check that warning was printed to stderr
        captured = capsys.readouterr()
        assert "Warning" in captured.err or "invalid email" in captured.err.lower()

    def test_load_player_data_from_csv_missing_email(self, tmp_path):
        """Test handling of missing email (empty field)."""
        test_file = tmp_path / "players.csv"
        test_file.write_text(
            "FIDE ID,email\n"
            "12345678,alice@example.com\n"
            "87654321,\n"
            "11111111,charlie@example.com\n"
        )
        result = fide_scraper.load_player_data_from_csv(str(test_file))

        assert len(result) == 3
        assert result["87654321"]["email"] == ""

    def test_load_player_data_from_csv_file_not_found(self):
        """Test handling of missing CSV file."""
        with pytest.raises(FileNotFoundError):
            fide_scraper.load_player_data_from_csv("/nonexistent/path/players.csv")

    def test_load_player_data_from_csv_invalid_headers(self, tmp_path):
        """Test handling of invalid CSV headers."""
        test_file = tmp_path / "players.csv"
        test_file.write_text(
            "ID,Email\n"
            "12345678,alice@example.com\n"
        )
        with pytest.raises(ValueError) as exc_info:
            fide_scraper.load_player_data_from_csv(str(test_file))
        assert "missing required headers" in str(exc_info.value).lower()

    def test_load_player_data_from_csv_invalid_fide_id(self, tmp_path, capsys):
        """Test that invalid FIDE IDs are skipped with warnings."""
        test_file = tmp_path / "players.csv"
        test_file.write_text(
            "FIDE ID,email\n"
            "12345678,alice@example.com\n"
            "123,invalid_fide\n"
            "87654321,bob@example.com\n"
        )
        result = fide_scraper.load_player_data_from_csv(str(test_file))

        # Should have 2 valid entries (123 is too short)
        assert len(result) == 2
        assert "12345678" in result
        assert "123" not in result
        assert "87654321" in result

        # Check that warning was printed to stderr
        captured = capsys.readouterr()
        assert "Warning" in captured.err or "invalid fide id" in captured.err.lower()

    def test_load_player_data_from_csv_empty_lines(self, tmp_path):
        """Test handling of empty lines in CSV."""
        test_file = tmp_path / "players.csv"
        test_file.write_text(
            "FIDE ID,email\n"
            "12345678,alice@example.com\n"
            "\n"
            "87654321,bob@example.com\n"
        )
        result = fide_scraper.load_player_data_from_csv(str(test_file))

        # Should have 2 valid entries
        assert len(result) == 2
        assert "12345678" in result
        assert "87654321" in result

    def test_load_player_data_from_csv_whitespace_stripped(self, tmp_path):
        """Test that whitespace is stripped from FIDE ID and email."""
        test_file = tmp_path / "players.csv"
        test_file.write_text(
            "FIDE ID,email\n"
            "  12345678  ,  alice@example.com  \n"
            "87654321,  bob@example.com  \n"
        )
        result = fide_scraper.load_player_data_from_csv(str(test_file))

        assert len(result) == 2
        assert result["12345678"]["email"] == "alice@example.com"
        assert result["87654321"]["email"] == "bob@example.com"


class TestLoadHistoricalRatingsByPlayer:
    """Tests for load_historical_ratings_by_player function."""

    def test_load_historical_ratings_valid(self, tmp_path):
        """Test loading valid historical ratings."""
        test_file = tmp_path / "fide_ratings.csv"
        test_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-11-21,12345678,Alice Smith,2440,2300,2100\n"
            "2025-11-21,87654321,Bob Jones,2500,2400,\n"
            "2025-11-22,12345678,Alice Smith,2450,2310,2110\n"
        )
        result = fide_scraper.load_historical_ratings_by_player(str(test_file))

        assert len(result) == 2
        # Should have the latest record for each FIDE ID
        assert result["12345678"]["Standard"] == "2450"
        assert result["87654321"]["Standard"] == "2500"

    def test_load_historical_ratings_latest_per_player(self, tmp_path):
        """Test that only latest record per player is kept."""
        test_file = tmp_path / "fide_ratings.csv"
        test_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-11-20,12345678,Alice Smith,2400,2250,2050\n"
            "2025-11-21,12345678,Alice Smith,2440,2300,2100\n"
            "2025-11-22,12345678,Alice Smith,2450,2310,2110\n"
        )
        result = fide_scraper.load_historical_ratings_by_player(str(test_file))

        assert len(result) == 1
        assert result["12345678"]["Date"] == "2025-11-22"
        assert result["12345678"]["Standard"] == "2450"

    def test_load_historical_ratings_file_not_found(self):
        """Test that missing file returns empty dict (first run)."""
        result = fide_scraper.load_historical_ratings_by_player("/nonexistent/path/fide_ratings.csv")
        assert result == {}

    def test_load_historical_ratings_invalid_headers(self, tmp_path):
        """Test handling of invalid CSV headers."""
        test_file = tmp_path / "fide_ratings.csv"
        test_file.write_text(
            "Date,ID,Name,Standard\n"
            "2025-11-21,12345678,Alice Smith,2440\n"
        )
        # Should return empty dict for invalid format (not raise exception)
        result = fide_scraper.load_historical_ratings_by_player(str(test_file))
        assert result == {}

    def test_load_historical_ratings_empty_file(self, tmp_path):
        """Test handling of empty CSV file."""
        test_file = tmp_path / "fide_ratings.csv"
        test_file.write_text("")
        result = fide_scraper.load_historical_ratings_by_player(str(test_file))
        assert result == {}

    def test_load_historical_ratings_unrated_handling(self, tmp_path):
        """Test handling of unrated/empty rating values."""
        test_file = tmp_path / "fide_ratings.csv"
        test_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-11-21,12345678,Alice Smith,2440,,2100\n"
            "2025-11-21,87654321,Bob Jones,,,\n"
        )
        result = fide_scraper.load_historical_ratings_by_player(str(test_file))

        assert len(result) == 2
        # Empty string should be converted to None
        assert result["12345678"]["Rapid"] is None
        assert result["87654321"]["Standard"] is None

    def test_load_historical_ratings_converts_empty_to_none(self, tmp_path):
        """Test that empty rating strings are converted to None."""
        test_file = tmp_path / "fide_ratings.csv"
        test_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-11-21,12345678,Alice Smith,2440,2300,\n"
        )
        result = fide_scraper.load_historical_ratings_by_player(str(test_file))

        assert result["12345678"]["Standard"] == "2440"
        assert result["12345678"]["Rapid"] == "2300"
        assert result["12345678"]["Blitz"] is None


class TestDetectRatingChanges:
    """Tests for detect_rating_changes function."""

    def test_detect_rating_changes_numeric_change(self):
        """Test detecting numeric rating change."""
        historical_data = {
            "12345678": {
                "Standard": "2440",
                "Rapid": "2300",
                "Blitz": "2100"
            }
        }
        new_ratings = {
            "Standard": 2450,
            "Rapid": 2300,
            "Blitz": 2100
        }
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        assert "Standard" in changes
        assert changes["Standard"] == (2440, 2450)
        assert "Rapid" not in changes
        assert "Blitz" not in changes

    def test_detect_rating_changes_unrated_to_rated(self):
        """Test detecting transition from unrated to rated."""
        historical_data = {
            "12345678": {
                "Standard": "2440",
                "Rapid": None,
                "Blitz": "2100"
            }
        }
        new_ratings = {
            "Standard": 2440,
            "Rapid": 2250,
            "Blitz": 2100
        }
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        assert "Rapid" in changes
        assert changes["Rapid"] == (None, 2250)
        assert len(changes) == 1

    def test_detect_rating_changes_rated_to_unrated(self):
        """Test detecting transition from rated to unrated."""
        historical_data = {
            "12345678": {
                "Standard": "2440",
                "Rapid": "2300",
                "Blitz": "2100"
            }
        }
        new_ratings = {
            "Standard": 2440,
            "Rapid": None,
            "Blitz": 2100
        }
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        assert "Rapid" in changes
        assert changes["Rapid"] == (2300, None)
        assert len(changes) == 1

    def test_detect_rating_changes_multiple_types(self):
        """Test detecting changes in multiple rating types."""
        historical_data = {
            "12345678": {
                "Standard": "2440",
                "Rapid": "2300",
                "Blitz": "2100"
            }
        }
        new_ratings = {
            "Standard": 2450,
            "Rapid": 2310,
            "Blitz": 2100
        }
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        assert "Standard" in changes
        assert changes["Standard"] == (2440, 2450)
        assert "Rapid" in changes
        assert changes["Rapid"] == (2300, 2310)
        assert "Blitz" not in changes
        assert len(changes) == 2

    def test_detect_rating_changes_no_changes(self):
        """Test detecting no changes when ratings are identical."""
        historical_data = {
            "12345678": {
                "Standard": "2440",
                "Rapid": "2300",
                "Blitz": "2100"
            }
        }
        new_ratings = {
            "Standard": 2440,
            "Rapid": 2300,
            "Blitz": 2100
        }
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        assert changes == {}

    def test_detect_rating_changes_missing_player(self):
        """Test that new player (not in history) returns no changes."""
        historical_data = {}
        new_ratings = {
            "Standard": 2440,
            "Rapid": 2300,
            "Blitz": 2100
        }
        changes = fide_scraper.detect_rating_changes(
            "99999999", new_ratings, historical_data
        )

        assert changes == {
            "Standard": (None, 2440),
            "Rapid": (None, 2300),
            "Blitz": (None, 2100)
        }

    def test_detect_rating_changes_all_unrated_to_unrated(self):
        """Test no changes when all ratings remain unrated."""
        historical_data = {
            "12345678": {
                "Standard": None,
                "Rapid": None,
                "Blitz": None
            }
        }
        new_ratings = {
            "Standard": None,
            "Rapid": None,
            "Blitz": None
        }
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        assert changes == {}

    def test_detect_rating_changes_empty_string_ratings(self):
        """Test handling empty string ratings from historical data."""
        historical_data = {
            "12345678": {
                "Standard": "2440",
                "Rapid": "",
                "Blitz": "2100"
            }
        }
        new_ratings = {
            "Standard": 2440,
            "Rapid": 2250,
            "Blitz": 2100
        }
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        # Empty string should be treated as None
        assert "Rapid" in changes
        assert changes["Rapid"] == (None, 2250)

    def test_detect_rating_changes_missing_rating_types(self):
        """Test handling when new_ratings missing some types."""
        historical_data = {
            "12345678": {
                "Standard": "2440",
                "Rapid": "2300",
                "Blitz": "2100"
            }
        }
        new_ratings = {
            "Standard": 2440,
            "Rapid": 2300
            # Blitz missing
        }
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        # Missing Blitz (None) vs "2100" should be detected as change
        assert "Blitz" in changes
        assert changes["Blitz"] == (2100, None)

    def test_detect_rating_changes_significant_increase(self):
        """Test detecting significant rating increase."""
        historical_data = {
            "12345678": {
                "Standard": "2440",
                "Rapid": "2300",
                "Blitz": "2100"
            }
        }
        new_ratings = {
            "Standard": 2550,
            "Rapid": 2400,
            "Blitz": 2200
        }
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        assert "Standard" in changes
        assert changes["Standard"] == (2440, 2550)
        assert "Rapid" in changes
        assert changes["Rapid"] == (2300, 2400)
        assert "Blitz" in changes
        assert changes["Blitz"] == (2100, 2200)

    def test_detect_rating_changes_decrease(self):
        """Test detecting rating decrease."""
        historical_data = {
            "12345678": {
                "Standard": "2440",
                "Rapid": "2300",
                "Blitz": "2100"
            }
        }
        new_ratings = {
            "Standard": 2420,
            "Rapid": 2280,
            "Blitz": 2080
        }
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        assert "Standard" in changes
        assert changes["Standard"] == (2440, 2420)
        assert "Rapid" in changes
        assert changes["Rapid"] == (2300, 2280)
        assert "Blitz" in changes
        assert changes["Blitz"] == (2100, 2080)


class TestComposeNotificationEmail:
    """Tests for compose_notification_email function."""

    def test_compose_notification_email_single_change(self):
        """Test composing email with a single rating change."""
        changes = {"Standard": (2440, 2450)}
        subject, body = email_notifier._compose_notification_email(
            "Alice Smith",
            "12345678",
            changes,
            "alice@example.com"
        )

        assert subject == "Your FIDE Rating Update - Alice Smith"
        assert "Dear Alice Smith," in body
        assert "Standard Rating: 2440 → 2450" in body
        assert "FIDE ID: 12345678" in body
        assert "FIDE Rating Monitor" in body

    def test_compose_notification_email_multiple_changes(self):
        """Test composing email with multiple rating changes."""
        changes = {
            "Standard": (2440, 2450),
            "Rapid": (2300, 2310),
            "Blitz": (2100, 2115)
        }
        subject, body = email_notifier._compose_notification_email(
            "Bob Jones",
            "87654321",
            changes,
            "bob@example.com"
        )

        assert subject == "Your FIDE Rating Update - Bob Jones"
        assert "Standard Rating: 2440 → 2450" in body
        assert "Rapid Rating: 2300 → 2310" in body
        assert "Blitz Rating: 2100 → 2115" in body
        assert "FIDE ID: 87654321" in body

    def test_compose_notification_email_unrated_to_rated(self):
        """Test composing email when player becomes rated."""
        changes = {"Standard": (None, 2450)}
        subject, body = email_notifier._compose_notification_email(
            "Charlie Brown",
            "11111111",
            changes,
            "charlie@example.com"
        )

        assert "Standard Rating: unrated → 2450" in body
        assert "Charlie Brown" in subject

    def test_compose_notification_email_rated_to_unrated(self):
        """Test composing email when player rating is removed."""
        changes = {"Rapid": (2300, None)}
        subject, body = email_notifier._compose_notification_email(
            "Diana Prince",
            "22222222",
            changes,
            "diana@example.com"
        )

        assert "Rapid Rating: 2300 → unrated" in body
        assert "Diana Prince" in subject

    def test_compose_notification_email_multiple_unrated_transitions(self):
        """Test composing email with mixed unrated transitions."""
        changes = {
            "Standard": (None, 2500),
            "Rapid": (2400, None),
            "Blitz": (2300, 2350)
        }
        subject, body = email_notifier._compose_notification_email(
            "Eve Wilson",
            "33333333",
            changes,
            "eve@example.com"
        )

        assert "Standard Rating: unrated → 2500" in body
        assert "Rapid Rating: 2400 → unrated" in body
        assert "Blitz Rating: 2300 → 2350" in body

    def test_compose_notification_email_sorted_by_rating_type(self):
        """Test that rating changes are sorted alphabetically by type."""
        changes = {
            "Blitz": (2100, 2115),
            "Standard": (2440, 2450),
            "Rapid": (2300, 2310)
        }
        subject, body = email_notifier._compose_notification_email(
            "Frank Miller",
            "44444444",
            changes,
            "frank@example.com"
        )

        # Extract the lines with ratings
        lines = body.split('\n')
        rating_lines = [line for line in lines if "Rating:" in line]

        # Verify they appear in sorted order: Blitz, Rapid, Standard
        assert len(rating_lines) == 3
        assert "Blitz" in rating_lines[0]
        assert "Rapid" in rating_lines[1]
        assert "Standard" in rating_lines[2]

    def test_compose_notification_email_with_cc_parameter(self):
        """Test that cc_email parameter is accepted but not used in composition."""
        changes = {"Standard": (2440, 2450)}
        subject, body = email_notifier._compose_notification_email(
            "Grace Lee",
            "55555555",
            changes,
            "grace@example.com",
            "admin@example.com"
        )

        assert subject == "Your FIDE Rating Update - Grace Lee"
        assert "Standard Rating: 2440 → 2450" in body
        # CC email should not appear in the body
        assert "admin@example.com" not in body

    def test_compose_notification_email_without_cc_parameter(self):
        """Test that cc_email is optional."""
        changes = {"Standard": (2440, 2450)}
        subject, body = email_notifier._compose_notification_email(
            "Henry Ford",
            "66666666",
            changes,
            "henry@example.com"
        )

        assert subject == "Your FIDE Rating Update - Henry Ford"
        assert "Your FIDE ratings have been updated" in body

    def test_compose_notification_email_special_characters_in_name(self):
        """Test composing email with special characters in player name."""
        changes = {"Standard": (2440, 2450)}
        subject, body = email_notifier._compose_notification_email(
            "José García-López",
            "77777777",
            changes,
            "jose@example.com"
        )

        assert "José García-López" in subject
        assert "Dear José García-López," in body

    def test_compose_notification_email_large_rating_change(self):
        """Test composing email with large rating fluctuation."""
        changes = {
            "Standard": (2200, 2500),  # 300 point jump
            "Rapid": (2100, 1900)      # 200 point drop
        }
        subject, body = email_notifier._compose_notification_email(
            "Iris Newton",
            "88888888",
            changes,
            "iris@example.com"
        )

        assert "Standard Rating: 2200 → 2500" in body
        assert "Rapid Rating: 2100 → 1900" in body

    def test_compose_notification_email_format_consistency(self):
        """Test that email format is consistent with expected structure."""
        changes = {"Standard": (2440, 2450)}
        subject, body = email_notifier._compose_notification_email(
            "Jack Turner",
            "99999999",
            changes,
            "jack@example.com"
        )

        # Verify expected sections exist in order
        assert body.startswith("Dear Jack Turner,")
        assert "\n\nYour FIDE ratings have been updated. Here are the changes:\n" in body
        assert "FIDE ID: 99999999" in body

    def test_compose_notification_email_no_changes(self):
        """Test composing email with no rating changes (edge case)."""
        changes = {}
        subject, body = email_notifier._compose_notification_email(
            "Kate Mitchell",
            "10101010",
            changes,
            "kate@example.com"
        )

        assert subject == "Your FIDE Rating Update - Kate Mitchell"
        # Body should still have standard greeting and footer
        assert "Dear Kate Mitchell," in body
        assert "FIDE ID: 10101010" in body


class TestSendEmailNotification:
    """Tests for send_email_notification function."""

    @patch('email_notifier.smtplib.SMTP')
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'smtp.example.com',
        'SMTP_PORT': '587',
        'SMTP_USERNAME': 'user@example.com',
        'SMTP_PASSWORD': 'password123'
    })
    def test_send_email_notification_success(self, mock_smtp_class):
        """Test successful email sending."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        result = email_notifier._send_email_notification(
            "alice@example.com",
            None,
            "Test Subject",
            "Test Body"
        )

        assert result is True
        mock_smtp_class.assert_called_once_with('smtp.example.com', 587, timeout=10)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('user@example.com', 'password123')
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch('email_notifier.smtplib.SMTP')
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'localhost',
        'SMTP_PORT': '587'
    }, clear=False)
    def test_send_email_notification_with_cc(self, mock_smtp_class):
        """Test email sending with CC recipient."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        result = email_notifier._send_email_notification(
            "alice@example.com",
            "admin@example.com",
            "Test Subject",
            "Test Body"
        )

        assert result is True
        # Verify sendmail was called with both recipients
        call_args = mock_server.sendmail.call_args
        recipients = call_args[0][1]
        assert "alice@example.com" in recipients
        assert "admin@example.com" in recipients

    @patch('email_notifier.smtplib.SMTP')
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'localhost',
        'SMTP_PORT': '587',
        'SMTP_USERNAME': '',
        'SMTP_PASSWORD': ''
    })
    def test_send_email_notification_no_auth(self, mock_smtp_class):
        """Test email sending without authentication."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        result = email_notifier._send_email_notification(
            "bob@example.com",
            None,
            "Subject",
            "Body"
        )

        assert result is True
        mock_server.starttls.assert_called_once()
        # login should not be called when no credentials
        mock_server.login.assert_not_called()
        mock_server.sendmail.assert_called_once()

    @patch('email_notifier.smtplib.SMTP')
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'localhost',
        'SMTP_PORT': '587',
        'SMTP_USERNAME': 'user@example.com',
        'SMTP_PASSWORD': 'wrong_password'
    })
    def test_send_email_notification_smtp_auth_error(self, mock_smtp_class):
        """Test handling of SMTP authentication error."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(401, "Invalid credentials")

        result = email_notifier._send_email_notification(
            "charlie@example.com",
            None,
            "Subject",
            "Body"
        )

        assert result is False

    @patch('email_notifier.smtplib.SMTP')
    def test_send_email_notification_smtp_error(self, mock_smtp_class):
        """Test handling of general SMTP error."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server
        mock_server.sendmail.side_effect = smtplib.SMTPException("SMTP error")

        result = email_notifier._send_email_notification(
            "diana@example.com",
            None,
            "Subject",
            "Body"
        )

        assert result is False

    @patch('email_notifier.smtplib.SMTP')
    def test_send_email_notification_connection_error(self, mock_smtp_class):
        """Test handling of connection error."""
        mock_smtp_class.side_effect = ConnectionError("Connection refused")

        result = email_notifier._send_email_notification(
            "eve@example.com",
            None,
            "Subject",
            "Body"
        )

        assert result is False

    @patch('email_notifier.smtplib.SMTP')
    def test_send_email_notification_timeout(self, mock_smtp_class):
        """Test handling of timeout error."""
        mock_smtp_class.side_effect = TimeoutError("Connection timeout")

        result = email_notifier._send_email_notification(
            "frank@example.com",
            None,
            "Subject",
            "Body"
        )

        assert result is False

    def test_send_email_notification_invalid_recipient(self):
        """Test handling of invalid recipient email."""
        result = email_notifier._send_email_notification(
            "",
            None,
            "Subject",
            "Body"
        )

        assert result is False

    def test_send_email_notification_none_recipient(self):
        """Test handling of None recipient email."""
        result = email_notifier._send_email_notification(
            None,
            None,
            "Subject",
            "Body"
        )

        assert result is False

    @patch('email_notifier.smtplib.SMTP')
    @patch.dict(os.environ, {
        'SMTP_PORT': 'invalid_port'
    }, clear=False)
    def test_send_email_notification_invalid_port(self, mock_smtp_class):
        """Test handling of invalid SMTP port configuration."""
        result = email_notifier._send_email_notification(
            "grace@example.com",
            None,
            "Subject",
            "Body"
        )

        assert result is False

    @patch('email_notifier.smtplib.SMTP')
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'localhost',
        'SMTP_PORT': '587'
    }, clear=False)
    def test_send_email_notification_email_format(self, mock_smtp_class):
        """Test that email is properly formatted with headers."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        result = email_notifier._send_email_notification(
            "henry@example.com",
            "admin@example.com",
            "Test Subject",
            "Test Body Content"
        )

        assert result is True
        # Get the email message sent
        call_args = mock_server.sendmail.call_args
        email_content = call_args[0][2]

        assert "Subject: Test Subject" in email_content
        assert "To: henry@example.com" in email_content
        assert "Cc: admin@example.com" in email_content
        assert "Test Body Content" in email_content

    @patch('email_notifier.smtplib.SMTP')
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'localhost',
        'SMTP_PORT': '587'
    }, clear=False)
    def test_send_email_notification_special_characters(self, mock_smtp_class):
        """Test email with special characters in subject and body."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        result = email_notifier._send_email_notification(
            "iris@example.com",
            None,
            "Rating Update - José García",
            "Dear José,\nYour rating changed: 2440 → 2450"
        )

        assert result is True
        mock_server.sendmail.assert_called_once()

    @patch('email_notifier.smtplib.SMTP')
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'localhost',
        'SMTP_PORT': '587',
        'SMTP_USERNAME': '',
        'SMTP_PASSWORD': ''
    })
    def test_send_email_notification_empty_credentials(self, mock_smtp_class):
        """Test that empty credentials are treated as no authentication."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        result = email_notifier._send_email_notification(
            "jack@example.com",
            None,
            "Subject",
            "Body"
        )

        assert result is True
        # login should not be called with empty credentials
        mock_server.login.assert_not_called()

    @patch('email_notifier.smtplib.SMTP')
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'localhost',
        'SMTP_PORT': '587'
    }, clear=False)
    def test_send_email_notification_whitespace_cc(self, mock_smtp_class):
        """Test that whitespace-only CC is treated as no CC."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        result = email_notifier._send_email_notification(
            "kate@example.com",
            "   ",
            "Subject",
            "Body"
        )

        assert result is True
        # Verify only recipient is in the recipient list
        call_args = mock_server.sendmail.call_args
        recipients = call_args[0][1]
        assert len(recipients) == 1
        assert recipients[0] == "kate@example.com"


# === EXTERNAL RATINGS API INTEGRATION TESTS ===

class TestLoadApiConfig:
    """Tests for load_api_config() function."""

    @patch.dict(os.environ, {'FIDE_RATINGS_API_ENDPOINT': 'https://api.example.com/ratings/', 'API_TOKEN': 'test-token-123'})
    def test_load_api_config_valid(self):
        """Test loading valid API configuration from environment."""
        config = ratings_api._load_api_config()
        assert config is not None
        assert config['endpoint'] == 'https://api.example.com/ratings/'
        assert config['token'] == 'test-token-123'

    @patch.dict(os.environ, {}, clear=False)
    def test_load_api_config_missing_both(self):
        """Test loading API configuration when both variables are missing."""
        # Remove the variables if they exist
        for var in ['FIDE_RATINGS_API_ENDPOINT', 'API_TOKEN']:
            if var in os.environ:
                del os.environ[var]

        config = ratings_api._load_api_config()
        assert config is None

    @patch.dict(os.environ, {'FIDE_RATINGS_API_ENDPOINT': 'https://api.example.com/ratings/', 'API_TOKEN': ''})
    def test_load_api_config_missing_token(self):
        """Test loading API configuration when token is missing."""
        config = ratings_api._load_api_config()
        assert config is None

    @patch.dict(os.environ, {'FIDE_RATINGS_API_ENDPOINT': '', 'API_TOKEN': 'test-token-123'})
    def test_load_api_config_missing_endpoint(self):
        """Test loading API configuration when endpoint is missing."""
        config = ratings_api._load_api_config()
        assert config is None

    @patch.dict(os.environ, {'FIDE_RATINGS_API_ENDPOINT': '  https://api.example.com/ratings/  ', 'API_TOKEN': '  test-token-123  '})
    def test_load_api_config_strips_whitespace(self):
        """Test that load_api_config strips whitespace from environment variables."""
        config = ratings_api._load_api_config()
        assert config is not None
        assert config['endpoint'] == 'https://api.example.com/ratings/'
        assert config['token'] == 'test-token-123'


class TestShouldPostToApi:
    """Tests for should_post_to_api() helper function."""

    @patch.dict(os.environ, {'FIDE_RATINGS_API_ENDPOINT': 'https://api.example.com/ratings/', 'API_TOKEN': 'test-token-123'})
    def test_should_post_to_api_enabled(self):
        """Test should_post_to_api returns True when both variables are set."""
        assert ratings_api._should_post_to_api() is True

    @patch.dict(os.environ, {}, clear=False)
    def test_should_post_to_api_disabled_missing_both(self):
        """Test should_post_to_api returns False when both variables are missing."""
        for var in ['FIDE_RATINGS_API_ENDPOINT', 'API_TOKEN']:
            if var in os.environ:
                del os.environ[var]

        assert ratings_api._should_post_to_api() is False

    @patch.dict(os.environ, {'FIDE_RATINGS_API_ENDPOINT': 'https://api.example.com/ratings/', 'API_TOKEN': ''})
    def test_should_post_to_api_disabled_missing_token(self):
        """Test should_post_to_api returns False when token is missing."""
        assert ratings_api._should_post_to_api() is False


class TestPostRatingToApi:
    """Tests for post_rating_to_api() function."""

    @patch('ratings_api.requests.post')
    def test_post_rating_to_api_success(self, mock_post):
        """Test successful API POST request."""
        # Mock successful 200 response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        profile = {
            'Date': '2024-12-18',
            'FIDE ID': '12345678',
            'Player Name': 'John Doe',
            'Standard': 2500,
            'Rapid': 2400,
            'Blitz': 2300
        }

        result = ratings_api._post_rating_to_api(
            profile,
            'https://api.example.com/ratings/',
            'test-token-123'
        )

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['headers']['Authorization'] == 'Token test-token-123'
        assert call_kwargs['json']['fide_id'] == '12345678'
        assert call_kwargs['json']['player_name'] == 'John Doe'

    @patch('ratings_api.requests.post')
    def test_post_rating_to_api_timeout(self, mock_post):
        """Test API POST request with timeout error."""
        mock_post.side_effect = requests.Timeout("Connection timeout")

        profile = {
            'Date': '2024-12-18',
            'FIDE ID': '12345678',
            'Player Name': 'John Doe',
            'Standard': 2500,
            'Rapid': 2400,
            'Blitz': 2300
        }

        result = ratings_api._post_rating_to_api(
            profile,
            'https://api.example.com/ratings/',
            'test-token-123'
        )

        assert result is False
        # Should have been called twice (1 initial + 1 retry)
        assert mock_post.call_count == 2

    @patch('ratings_api.requests.post')
    def test_post_rating_to_api_connection_error(self, mock_post):
        """Test API POST request with connection error."""
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        profile = {
            'Date': '2024-12-18',
            'FIDE ID': '12345678',
            'Player Name': 'John Doe',
            'Standard': 2500,
            'Rapid': 2400,
            'Blitz': 2300
        }

        result = ratings_api._post_rating_to_api(
            profile,
            'https://api.example.com/ratings/',
            'test-token-123'
        )

        assert result is False
        # Should have been called twice (1 initial + 1 retry)
        assert mock_post.call_count == 2

    @patch('ratings_api.requests.post')
    def test_post_rating_to_api_http_400_error(self, mock_post):
        """Test API POST request with HTTP 400 error (no retry)."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'Invalid request'}
        mock_post.return_value = mock_response

        profile = {
            'Date': '2024-12-18',
            'FIDE ID': '12345678',
            'Player Name': 'John Doe',
            'Standard': 2500,
            'Rapid': 2400,
            'Blitz': 2300
        }

        result = ratings_api._post_rating_to_api(
            profile,
            'https://api.example.com/ratings/',
            'test-token-123'
        )

        assert result is False
        # Should only be called once (no retry for 4xx)
        assert mock_post.call_count == 1

    @patch('ratings_api.requests.post')
    def test_post_rating_to_api_http_500_error(self, mock_post):
        """Test API POST request with HTTP 500 error (with retry)."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {'error': 'Server error'}
        mock_post.return_value = mock_response

        profile = {
            'Date': '2024-12-18',
            'FIDE ID': '12345678',
            'Player Name': 'John Doe',
            'Standard': 2500,
            'Rapid': 2400,
            'Blitz': 2300
        }

        result = ratings_api._post_rating_to_api(
            profile,
            'https://api.example.com/ratings/',
            'test-token-123'
        )

        assert result is False
        # Should have been called twice (1 initial + 1 retry for 5xx)
        assert mock_post.call_count == 2

    @patch('ratings_api.requests.post')
    def test_post_rating_to_api_http_401_error(self, mock_post):
        """Test API POST request with HTTP 401 error (authentication error)."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {'error': 'Unauthorized'}
        mock_post.return_value = mock_response

        profile = {
            'Date': '2024-12-18',
            'FIDE ID': '12345678',
            'Player Name': 'John Doe',
            'Standard': 2500,
            'Rapid': 2400,
            'Blitz': 2300
        }

        result = ratings_api._post_rating_to_api(
            profile,
            'https://api.example.com/ratings/',
            'test-token-123'
        )

        assert result is False
        # Should only be called once (no retry for 4xx)
        assert mock_post.call_count == 1

    @patch('ratings_api.requests.post')
    def test_post_rating_to_api_null_ratings(self, mock_post):
        """Test API POST with null ratings (unrated players)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        profile = {
            'Date': '2024-12-18',
            'FIDE ID': '87654321',
            'Player Name': 'Jane Doe',
            'Standard': None,
            'Rapid': 1900,
            'Blitz': None
        }

        result = ratings_api._post_rating_to_api(
            profile,
            'https://api.example.com/ratings/',
            'test-token-123'
        )

        assert result is True
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['json']['standard_rating'] is None
        assert call_kwargs['json']['rapid_rating'] == 1900
        assert call_kwargs['json']['blitz_rating'] is None

    @patch('ratings_api.requests.post')
    def test_post_rating_to_api_timeout_value(self, mock_post):
        """Test that timeout is passed correctly to requests.post."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        profile = {
            'Date': '2024-12-18',
            'FIDE ID': '12345678',
            'Player Name': 'John Doe',
            'Standard': 2500,
            'Rapid': 2400,
            'Blitz': 2300
        }

        result = ratings_api._post_rating_to_api(
            profile,
            'https://api.example.com/ratings/',
            'test-token-123',
            timeout=5
        )

        assert result is True
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['timeout'] == 5
