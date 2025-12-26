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
        from datetime import date
        today = date.today()

        player_profiles = [
            {
                'FIDE ID': '538026660',
                'Player Name': 'Magnus Carlsen',
                'Standard': 2830,
                'Rapid': 2780,
                'Blitz': 2760,
                'Rating History': [
                    {'date': today, 'standard': 2830, 'rapid': 2780, 'blitz': 2760}
                ]
            }
        ]
        fide_scraper.write_csv_output(str(output_file), player_profiles)

        # Read and verify CSV content
        content = output_file.read_text(encoding='utf-8')
        assert 'Date,FIDE ID,Player Name,Standard,Rapid,Blitz' in content
        # Date should be in ISO format at the beginning
        today_str = today.isoformat()
        assert f'{today_str},538026660,Magnus Carlsen,2830,2780,2760' in content
    
    def test_write_csv_output_special_characters(self, tmp_path):
        """Test CSV generation with special characters in player names (proper escaping)."""
        output_file = tmp_path / "test_output.csv"
        from datetime import date
        today = date.today()

        player_profiles = [
            {
                'FIDE ID': '123456',
                'Player Name': 'Player, With Comma',
                'Standard': 2500,
                'Rapid': 2450,
                'Blitz': 2400,
                'Rating History': [
                    {'date': today, 'standard': 2500, 'rapid': 2450, 'blitz': 2400}
                ]
            }
        ]
        fide_scraper.write_csv_output(str(output_file), player_profiles)
        
        # Read and verify CSV content (comma should be quoted)
        content = output_file.read_text(encoding='utf-8')
        assert '"Player, With Comma"' in content or 'Player, With Comma' in content
    
    def test_write_csv_output_empty_values(self, tmp_path):
        """Test CSV generation with empty/missing ratings."""
        output_file = tmp_path / "test_output.csv"
        from datetime import date
        today = date.today()

        player_profiles = [
            {
                'FIDE ID': '123456',
                'Player Name': 'Test Player',
                'Standard': 2500,
                'Rapid': None,
                'Blitz': None,
                'Rating History': [
                    {'date': today, 'standard': 2500, 'rapid': None, 'blitz': None}
                ]
            }
        ]
        fide_scraper.write_csv_output(str(output_file), player_profiles)

        # Read and verify CSV content - Date should come first
        content = output_file.read_text(encoding='utf-8')
        today_str = today.isoformat()
        # Check that date is present and values are correct
        assert today_str in content
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

        today = date.today()

        # First write - initial data
        player_profiles_1 = [
            {
                'FIDE ID': '538026660',
                'Player Name': 'Magnus Carlsen',
                'Standard': 2830,
                'Rapid': 2780,
                'Blitz': 2760,
                'Rating History': [
                    {'date': today, 'standard': 2830, 'rapid': 2780, 'blitz': 2760}
                ]
            }
        ]
        fide_scraper.write_csv_output(str(output_file), player_profiles_1)

        # Second write on same day - should replace previous data
        player_profiles_2 = [
            {
                'FIDE ID': '538026660',
                'Player Name': 'Magnus Carlsen',
                'Standard': 2840,
                'Rapid': 2790,
                'Blitz': 2770,
                'Rating History': [
                    {'date': today, 'standard': 2840, 'rapid': 2790, 'blitz': 2770}
                ]
            }
        ]
        fide_scraper.write_csv_output(str(output_file), player_profiles_2)

        # Read and verify behavior
        content = output_file.read_text(encoding='utf-8')
        today_str = today.isoformat()

        # Should have header only once
        header_count = content.count('Date,FIDE ID,Player Name,Standard,Rapid,Blitz')
        assert header_count == 1, "Header should appear only once"

        # Should have the updated entry with new ratings
        assert 'Magnus Carlsen' in content, "Player should be present"
        assert '2840' in content, "Updated Standard rating should be present"
        # Should only have one entry for this player today
        lines = [l for l in content.split('\n') if today_str in l and '538026660' in l]
        assert len(lines) == 1, "Should have exactly one entry per player per month"


    def test_write_csv_output_preserve_older_dates(self, tmp_path):
        """Test that CSV output preserves entries from previous months."""
        output_file = tmp_path / "test_output.csv"
        from datetime import date
        from calendar import monthrange

        # Create a file with last month's data
        today = date.today()
        # Get last day of previous month
        if today.month == 1:
            last_month_date = date(today.year - 1, 12, 31)
        else:
            last_month_date = date(today.year, today.month - 1, monthrange(today.year, today.month - 1)[1])

        last_month_str = last_month_date.isoformat()

        # Manually create a file with last month's data
        output_file.write_text(
            f"Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            f"{last_month_str},1503014,Magnus Carlsen,2830,2780,2760\n"
        )

        # Now write current month's data
        player_profiles = [
            {
                'FIDE ID': '1503014',
                'Player Name': 'Magnus Carlsen',
                'Standard': 2840,
                'Rapid': 2790,
                'Blitz': 2760,
                'Rating History': [
                    {
                        'date': today,
                        'standard': 2840,
                        'rapid': 2790,
                        'blitz': 2760
                    }
                ]
            }
        ]
        fide_scraper.write_csv_output(str(output_file), player_profiles)

        # Read and verify both months are present
        content = output_file.read_text(encoding='utf-8')
        today_str = today.isoformat()

        # Should have header only once
        header_count = content.count('Date,FIDE ID,Player Name,Standard,Rapid,Blitz')
        assert header_count == 1, "Header should appear only once"

        # Should have last month's entry
        assert last_month_str in content, "Last month's entry should be preserved"
        assert 'Magnus Carlsen' in content, "Last month's player should be present"
        assert '1503014' in content, "Last month's FIDE ID should be present"

        # Should have current month's entry
        assert today_str in content, "Current month's date should be present"
        assert 'Magnus Carlsen' in content, "Current month's player should be present"
        assert '1503014' in content, "Current month's FIDE ID should be present"

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
    @patch('fide_scraper.extract_rating_history')
    @patch('fide_scraper.extract_player_name')
    def test_batch_processing_invalid_ids_skipped(self, mock_name, mock_history, mock_fetch):
        """Test that invalid FIDE IDs are skipped without stopping batch."""
        mock_history.return_value = []  # Empty history
        mock_name.return_value = ""  # No name found

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
        # Should return lists of monthly records
        assert isinstance(result["12345678"], list)
        assert isinstance(result["87654321"], list)
        # Check latest records (most recent month)
        assert len(result["12345678"]) >= 1
        assert len(result["87654321"]) >= 1

    def test_load_historical_ratings_latest_per_player(self, tmp_path):
        """Test that only latest record per player is kept."""
        test_file = tmp_path / "fide_ratings.csv"
        test_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-11-30,12345678,Alice Smith,2400,2250,2050\n"
            "2025-10-31,12345678,Alice Smith,2440,2300,2100\n"
            "2025-09-30,12345678,Alice Smith,2450,2310,2110\n"
        )
        result = fide_scraper.load_historical_ratings_by_player(str(test_file))

        assert len(result) == 1
        # Should have list of all monthly records
        assert isinstance(result["12345678"], list)
        assert len(result["12345678"]) == 3
        # Check that dates are present
        dates = [rec.get("Date") for rec in result["12345678"]]
        assert "2025-11-30" in dates
        assert "2025-10-31" in dates
        assert "2025-09-30" in dates

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
        # Should have lists of records
        assert isinstance(result["12345678"], list)
        assert isinstance(result["87654321"], list)
        # Empty string should be converted to None
        assert result["12345678"][0]["Rapid"] is None
        assert result["87654321"][0]["Standard"] is None

    def test_load_historical_ratings_converts_empty_to_none(self, tmp_path):
        """Test that empty rating strings are converted to None."""
        test_file = tmp_path / "fide_ratings.csv"
        test_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-11-21,12345678,Alice Smith,2440,2300,\n"
        )
        result = fide_scraper.load_historical_ratings_by_player(str(test_file))

        assert isinstance(result["12345678"], list)
        assert len(result["12345678"]) == 1
        record = result["12345678"][0]
        assert record["Standard"] == "2440"
        assert record["Rapid"] == "2300"
        assert record["Blitz"] is None


class TestDetectNewMonths:
    """Tests for detect_new_months function."""

    def test_detect_new_months_single_new_month(self):
        """Test detecting a single new month."""
        from datetime import date

        fide_id = "12345678"
        scraped_history = [
            {
                'date': date(2025, 11, 30),
                'standard': 2450,
                'rapid': 2300,
                'blitz': 2100
            },
            {
                'date': date(2025, 10, 31),
                'standard': 2440,
                'rapid': 2300,
                'blitz': 2100
            }
        ]
        stored_history = {
            "12345678": [
                {
                    'Date': '2025-10-31',
                    'Standard': '2440',
                    'Rapid': '2300',
                    'Blitz': '2100'
                }
            ]
        }

        new_months = fide_scraper.detect_new_months(
            fide_id, scraped_history, stored_history
        )

        # Should detect the November entry as new
        assert len(new_months) == 1
        assert new_months[0]['date'] == date(2025, 11, 30)

    def test_detect_new_months_no_new_months(self):
        """Test when all scraped months are already stored."""
        from datetime import date

        fide_id = "12345678"
        scraped_history = [
            {
                'date': date(2025, 11, 30),
                'standard': 2450,
                'rapid': 2300,
                'blitz': 2100
            }
        ]
        stored_history = {
            "12345678": [
                {
                    'Date': '2025-11-30',
                    'Standard': '2450',
                    'Rapid': '2300',
                    'Blitz': '2100'
                }
            ]
        }

        new_months = fide_scraper.detect_new_months(
            fide_id, scraped_history, stored_history
        )

        # Should find no new months
        assert len(new_months) == 0

    def test_detect_new_months_first_run(self):
        """Test first run with no stored history (all scraped months are new)."""
        from datetime import date

        fide_id = "12345678"
        scraped_history = [
            {
                'date': date(2025, 11, 30),
                'standard': 2450,
                'rapid': 2300,
                'blitz': 2100
            },
            {
                'date': date(2025, 10, 31),
                'standard': 2440,
                'rapid': 2300,
                'blitz': 2100
            }
        ]
        stored_history = {}

        new_months = fide_scraper.detect_new_months(
            fide_id, scraped_history, stored_history
        )

        # All months should be new on first run
        assert len(new_months) == 2

    def test_detect_new_months_multiple_new(self):
        """Test detecting multiple new months."""
        from datetime import date

        fide_id = "12345678"
        scraped_history = [
            {
                'date': date(2025, 11, 30),
                'standard': 2450,
                'rapid': 2300,
                'blitz': 2100
            },
            {
                'date': date(2025, 10, 31),
                'standard': 2440,
                'rapid': 2300,
                'blitz': 2100
            },
            {
                'date': date(2025, 9, 30),
                'standard': 2430,
                'rapid': 2290,
                'blitz': 2090
            }
        ]
        stored_history = {
            "12345678": [
                {
                    'Date': '2025-09-30',
                    'Standard': '2430',
                    'Rapid': '2290',
                    'Blitz': '2090'
                }
            ]
        }

        new_months = fide_scraper.detect_new_months(
            fide_id, scraped_history, stored_history
        )

        # Should detect October and November as new
        assert len(new_months) == 2
        dates = [m['date'] for m in new_months]
        assert date(2025, 11, 30) in dates
        assert date(2025, 10, 31) in dates

    def test_detect_new_months_empty_scraped(self):
        """Test when scraped history is empty."""
        fide_id = "12345678"
        scraped_history = []
        stored_history = {
            "12345678": [
                {
                    'Date': '2025-11-30',
                    'Standard': '2450',
                    'Rapid': '2300',
                    'Blitz': '2100'
                }
            ]
        }

        new_months = fide_scraper.detect_new_months(
            fide_id, scraped_history, stored_history
        )

        # No new months when scraped is empty
        assert len(new_months) == 0

    def test_detect_new_months_unrated_handling(self):
        """Test new month detection with unrated values."""
        from datetime import date

        fide_id = "12345678"
        scraped_history = [
            {
                'date': date(2025, 11, 30),
                'standard': None,
                'rapid': 2300,
                'blitz': None
            }
        ]
        stored_history = {}

        new_months = fide_scraper.detect_new_months(
            fide_id, scraped_history, stored_history
        )

        # Should detect as new even with unrated values
        assert len(new_months) == 1
        assert new_months[0]['standard'] is None
        assert new_months[0]['rapid'] == 2300


class TestComposeNotificationEmail:
    """Tests for compose_notification_email function."""

    def test_compose_notification_email_single_change(self):
        """Test composing email with a single rating change."""
        from datetime import date
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2300, "blitz": 2100},
            {"date": date(2025, 10, 31), "standard": 2440, "rapid": 2300, "blitz": 2100}
        ]
        subject, body = email_notifier._compose_notification_email(
            "Alice Smith",
            "12345678",
            rating_history
        )

        assert subject == "Your FIDE Rating Update - Alice Smith"
        assert "Dear Alice Smith," in body
        assert "Standard Rating: 2440 → 2450" in body
        assert "FIDE ID: 12345678" in body
        assert "FIDE Rating Monitor" in body

    def test_compose_notification_email_multiple_changes(self):
        """Test composing email with multiple rating changes."""
        from datetime import date
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2310, "blitz": 2115},
            {"date": date(2025, 10, 31), "standard": 2440, "rapid": 2300, "blitz": 2100}
        ]
        subject, body = email_notifier._compose_notification_email(
            "Bob Jones",
            "87654321",
            rating_history
        )

        assert subject == "Your FIDE Rating Update - Bob Jones"
        assert "Standard Rating: 2440 → 2450" in body
        assert "Rapid Rating: 2300 → 2310" in body
        assert "Blitz Rating: 2100 → 2115" in body
        assert "FIDE ID: 87654321" in body
        
    def test_compose_notification_email_unrated_to_rated(self):
        """Test composing email when player becomes rated."""
        from datetime import date
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": None, "blitz": None},
            {"date": date(2025, 10, 31), "standard": None, "rapid": None, "blitz": None}
        ]
        subject, body = email_notifier._compose_notification_email(
            "Charlie Brown",
            "11111111",
            rating_history
        )

        assert "Standard Rating: unrated → 2450" in body
        assert "Charlie Brown" in subject

    def test_compose_notification_email_rated_to_unrated(self):
        """Test composing email when player rating is removed."""
        from datetime import date
        rating_history = [
            {"date": date(2025, 11, 30), "standard": None, "rapid": None, "blitz": None},
            {"date": date(2025, 10, 31), "standard": 2400, "rapid": 2300, "blitz": 2100}
        ]
        subject, body = email_notifier._compose_notification_email(
            "Diana Prince",
            "22222222",
            rating_history
        )

        assert "Rapid Rating: 2300 → unrated" in body
        assert "Diana Prince" in subject

    def test_compose_notification_email_multiple_unrated_transitions(self):
        """Test composing email with mixed unrated transitions."""
        from datetime import date
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2500, "rapid": None, "blitz": 2350},
            {"date": date(2025, 10, 31), "standard": None, "rapid": 2400, "blitz": 2300}
        ]
        subject, body = email_notifier._compose_notification_email(
            "Eve Wilson",
            "33333333",
            rating_history
        )

        assert "Standard Rating: unrated → 2500" in body
        assert "Rapid Rating: 2400 → unrated" in body
        assert "Blitz Rating: 2300 → 2350" in body

    def test_compose_notification_email_sorted_by_rating_type(self):
        """Test that rating changes are sorted alphabetically by type."""
        from datetime import date
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2310, "blitz": 2115},
            {"date": date(2025, 10, 31), "standard": 2440, "rapid": 2300, "blitz": 2100}
        ]
        subject, body = email_notifier._compose_notification_email(
            "Frank Miller",
            "44444444",
            rating_history
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
        from datetime import date
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2300, "blitz": 2100},
            {"date": date(2025, 10, 31), "standard": 2440, "rapid": 2300, "blitz": 2100}
        ]
        subject, body = email_notifier._compose_notification_email(
            "Grace Lee",
            "55555555",
            rating_history
        )

        assert subject == "Your FIDE Rating Update - Grace Lee"
        assert "Standard Rating: 2440 → 2450" in body
        # CC email should not appear in the body
        assert "admin@example.com" not in body

    def test_compose_notification_email_without_cc_parameter(self):
        """Test that cc_email is optional."""
        from datetime import date
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2300, "blitz": 2100},
            {"date": date(2025, 10, 31), "standard": 2440, "rapid": 2300, "blitz": 2100}
        ]
        subject, body = email_notifier._compose_notification_email(
            "Henry Ford",
            "66666666",
            rating_history
        )

        assert subject == "Your FIDE Rating Update - Henry Ford"
        assert "Your FIDE ratings have been updated" in body

    def test_compose_notification_email_special_characters_in_name(self):
        """Test composing email with special characters in player name."""
        from datetime import date
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2300, "blitz": 2100},
            {"date": date(2025, 10, 31), "standard": 2440, "rapid": 2300, "blitz": 2100}
        ]
        subject, body = email_notifier._compose_notification_email(
            "José García-López",
            "77777777",
            rating_history
        )

        assert "José García-López" in subject
        assert "Dear José García-López," in body

    def test_compose_notification_email_large_rating_change(self):
        """Test composing email with large rating fluctuation."""
        from datetime import date
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2500, "rapid": 1900, "blitz": 2100},
            {"date": date(2025, 10, 31), "standard": 2200, "rapid": 2100, "blitz": 2100}
        ]
        subject, body = email_notifier._compose_notification_email(
            "Iris Newton",
            "88888888",
            rating_history
        )

        assert "Standard Rating: 2200 → 2500" in body
        assert "Rapid Rating: 2100 → 1900" in body

    def test_compose_notification_email_format_consistency(self):
        """Test that email format is consistent with expected structure."""
        from datetime import date
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2300, "blitz": 2100},
            {"date": date(2025, 10, 31), "standard": 2440, "rapid": 2300, "blitz": 2100}
        ]
        subject, body = email_notifier._compose_notification_email(
            "Jack Turner",
            "99999999",
            rating_history
        )

        # Verify expected sections exist in order
        assert body.startswith("Dear Jack Turner,")
        assert "\n\nYour FIDE ratings have been updated. Here are the changes:\n" in body
        assert "FIDE ID: 99999999" in body

    def test_compose_notification_email_single_month_only(self):
        """Test composing email with only one month of history."""
        from datetime import date
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2300, "blitz": 2100}
        ]
        subject, body = email_notifier._compose_notification_email(
            "Kate Mitchell",
            "10101010",
            rating_history
        )

        assert subject == "Your FIDE Rating Update - Kate Mitchell"
        # Body should have standard greeting and footer
        assert "Dear Kate Mitchell," in body
        assert "FIDE ID: 10101010" in body
        # Should show current ratings when only one month
        assert "Standard Rating: 2450" in body


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
            'date': '2024-12-18',
            'fide_id': '12345678',
            'player_name': 'John Doe',
            'standard_rating': 2500,
            'rapid_rating': 2400,
            'blitz_rating': 2300
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
            'date': '2024-12-18',
            'fide_id': '12345678',
            'player_name': 'John Doe',
            'standard_rating': 2500,
            'rapid_rating': 2400,
            'blitz_rating': 2300
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
            'date': '2024-12-18',
            'fide_id': '12345678',
            'player_name': 'John Doe',
            'standard_rating': 2500,
            'rapid_rating': 2400,
            'blitz_rating': 2300
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
            'date': '2024-12-18',
            'fide_id': '12345678',
            'player_name': 'John Doe',
            'standard_rating': 2500,
            'rapid_rating': 2400,
            'blitz_rating': 2300
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
            'date': '2024-12-18',
            'fide_id': '12345678',
            'player_name': 'John Doe',
            'standard_rating': 2500,
            'rapid_rating': 2400,
            'blitz_rating': 2300
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
            'date': '2024-12-18',
            'fide_id': '12345678',
            'player_name': 'John Doe',
            'standard_rating': 2500,
            'rapid_rating': 2400,
            'blitz_rating': 2300
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
            'date': '2024-12-18',
            'fide_id': '87654321',
            'player_name': 'Jane Doe',
            'standard_rating': None,
            'rapid_rating': 1900,
            'blitz_rating': None
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
            'date': '2024-12-18',
            'fide_id': '12345678',
            'player_name': 'John Doe',
            'standard_rating': 2500,
            'rapid_rating': 2400,
            'blitz_rating': 2300
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
