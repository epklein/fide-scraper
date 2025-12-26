"""
Integration tests for fide_scraper.py

These tests require network access and may make actual HTTP requests.
"""

import pytest
import sys
import os
import smtplib
from unittest.mock import patch, MagicMock

# Add parent directory to path to import fide_scraper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fide_scraper
import email_notifier
import ratings_api


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
        history = fide_scraper.extract_rating_history(html)
        
        # First month should have at least one non-None rating
        assert (history[0].get('standard') is not None or
                history[0].get('rapid') is not None or
                history[0].get('blitz') is not None)
    
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
            history = fide_scraper.extract_rating_history(html)
            # Should be empty for non-existent player
            assert len(history) == 0


@pytest.mark.integration
class TestBatchProcessing:
    """Integration tests for batch processing functionality."""
    
    def test_end_to_end_batch_processing(self, tmp_path):
        """Test end-to-end batch processing with real FIDE IDs."""
        # Create input CSV file with valid FIDE IDs and emails
        input_file = tmp_path / "players.csv"
        input_file.write_text("FIDE ID,email\n538026660,player1@example.com\n2016892,player2@example.com\n")

        # Load player data from CSV
        player_data = fide_scraper.load_player_data_from_csv(str(input_file))
        assert len(player_data) == 2

        # Extract FIDE IDs from player data
        fide_ids = list(player_data.keys())

        # Process batch
        results, errors = fide_scraper.process_batch(fide_ids)

        # Should have results
        assert len(results) > 0

        # Write CSV output
        output_file = tmp_path / "fide_ratings.csv"
        fide_scraper.write_csv_output(str(output_file), results)

        # Verify CSV file exists and has content
        assert output_file.exists()
        content = output_file.read_text(encoding='utf-8')
        assert 'Date,FIDE ID,Player Name,Standard,Rapid,Blitz' in content
        # Verify that monthly dates are present (not today's date, but month-end dates)
        # The CSV should contain multiple months of history for the players
        assert '538026660' in content  # FIDE ID present
        # Check that we have multiple date entries (monthly history)
        lines = content.strip().split('\n')
        assert len(lines) > 2  # Header + at least one data row

        # Verify console output
        console_output = fide_scraper.format_console_output(results)
        assert 'Date' in console_output
        assert 'FIDE ID' in console_output
        assert 'Player Name' in console_output
    
    def test_batch_processing_mixed_valid_invalid(self, tmp_path):
        """Test batch processing with CSV-loaded player data."""
        # Create input CSV file with multiple valid FIDE IDs
        input_file = tmp_path / "players.csv"
        input_file.write_text("FIDE ID,email\n538026660,player1@example.com\n2016892,player2@example.com\n")

        # Load player data from CSV
        player_data = fide_scraper.load_player_data_from_csv(str(input_file))
        assert len(player_data) == 2

        # Extract FIDE IDs from player data
        fide_ids = list(player_data.keys())
        assert len(fide_ids) == 2

        # Process batch
        results, errors = fide_scraper.process_batch(fide_ids)

        # Should have some results (valid IDs that fetch successfully)
        assert len(results) > 0

        # Results should include both processed IDs
        assert len(results) >= 1

        # Verify that player data was loaded correctly from CSV
        assert "538026660" in player_data
        assert "2016892" in player_data
        assert player_data["538026660"]["email"] == "player1@example.com"
        assert player_data["2016892"]["email"] == "player2@example.com"


class TestEmailNotificationIntegration:
    """Integration tests for email notification workflow."""

    def test_email_notification_workflow_compose_and_send(self):
        """Test complete email notification workflow: compose and send."""
        from datetime import date

        # Create sample rating history
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2310, "blitz": 2100},
            {"date": date(2025, 10, 31), "standard": 2440, "rapid": 2300, "blitz": 2100}
        ]

        # Compose email
        subject, body = email_notifier._compose_notification_email(
            "Test Player",
            "12345678",
            rating_history
        )

        # Verify email content
        assert "Test Player" in subject
        assert "Standard Rating: 2440 → 2450" in body
        assert "Rapid Rating: 2300 → 2310" in body

    @patch('email_notifier.smtplib.SMTP')
    def test_email_notification_workflow_with_smtp_mock(self, mock_smtp_class):
        """Test complete email workflow with mocked SMTP."""
        from unittest.mock import MagicMock
        from datetime import date

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Compose email
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2300, "blitz": 2100},
            {"date": date(2025, 10, 31), "standard": 2440, "rapid": 2300, "blitz": 2100}
        ]
        subject, body = email_notifier._compose_notification_email(
            "Alice Smith",
            "12345678",
            rating_history
        )

        # Send email
        result = email_notifier._send_email_notification(
            "alice@example.com",
            "admin@example.com",
            subject,
            body
        )

        assert result is True
        mock_server.sendmail.assert_called_once()

    def test_player_data_to_email_pipeline(self, tmp_path):
        """Test pipeline: load player data -> detect new months -> compose email."""
        from datetime import date

        # Create player data CSV
        players_file = tmp_path / "players.csv"
        players_file.write_text("FIDE ID,email\n12345678,alice@example.com\n87654321,bob@example.com\n")

        # Create historical ratings CSV
        history_file = tmp_path / "history.csv"
        history_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-10-31,12345678,Alice Smith,2440,2300,2100\n"
            "2025-10-31,87654321,Bob Jones,2500,2400,\n"
        )

        # Load player data
        player_data = fide_scraper.load_player_data_from_csv(str(players_file))
        assert len(player_data) == 2
        assert player_data["12345678"]["email"] == "alice@example.com"

        # Load historical ratings
        historical_data = fide_scraper.load_historical_ratings_by_player(str(history_file))
        assert len(historical_data) == 2

        # Detect new months for Alice (new month with different rating)
        alice_scraped_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2300, "blitz": 2100}
        ]
        alice_new_months = fide_scraper.detect_new_months(
            "12345678",
            alice_scraped_history,
            historical_data
        )
        assert len(alice_new_months) == 1
        assert alice_new_months[0]["date"] == date(2025, 11, 30)
        assert alice_new_months[0]["standard"] == 2450

        # Verify email notification would be sent for Alice (has new month)
        assert len(alice_new_months) > 0
        assert player_data["12345678"]["email"] == "alice@example.com"

        # Detect new months for Bob (same month, no new months)
        bob_scraped_history = [
            {"date": date(2025, 10, 31), "standard": 2500, "rapid": 2400, "blitz": None}
        ]
        bob_new_months = fide_scraper.detect_new_months(
            "87654321",
            bob_scraped_history,
            historical_data
        )
        # Bob has no new months (same as stored)
        assert len(bob_new_months) == 0

    def test_batch_processing_with_change_detection(self, tmp_path):
        """Test batch processing with integrated change detection."""
        # Create input data
        players_file = tmp_path / "players.csv"
        players_file.write_text("FIDE ID,email\n94157,player@example.com\n")

        # Create historical data (empty for first run)
        history_file = tmp_path / "history.csv"
        history_file.write_text("Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n")
        # Load player data
        player_data = fide_scraper.load_player_data_from_csv(str(players_file))
        fide_ids = list(player_data.keys())

        # Load historical ratings (empty on first run)
        historical_data = fide_scraper.load_historical_ratings_by_player(str(history_file))

        # Process batch
        results, errors = fide_scraper.process_batch(fide_ids, historical_data)

        # Should have processed the player
        assert len(results) > 0 or len(errors) > 0

    @patch('email_notifier.smtplib.SMTP')
    def test_complete_email_notification_workflow(self, mock_smtp_class, tmp_path):
        """Test complete workflow: load data -> detect new months -> send emails."""
        from unittest.mock import MagicMock
        from datetime import date

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Create player data
        players_file = tmp_path / "players.csv"
        players_file.write_text(
            "FIDE ID,email\n"
            "12345678,alice@example.com\n"
            "87654321,\n"
        )

        # Create historical ratings
        history_file = tmp_path / "history.csv"
        history_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-10-31,12345678,Alice Smith,2440,2300,2100\n"
            "2025-10-31,87654321,Bob Jones,2500,2400,\n"
        )

        # Load player data
        player_data = fide_scraper.load_player_data_from_csv(str(players_file))

        # Load historical ratings
        historical_data = fide_scraper.load_historical_ratings_by_player(str(history_file))

        # Simulate scraped history with new month for Alice
        alice_scraped_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2300, "blitz": 2100}
        ]

        # Detect new months
        alice_new_months = fide_scraper.detect_new_months(
            "12345678", alice_scraped_history, historical_data
        )

        # Only Alice has email and has new months, so send notification
        if alice_new_months and player_data["12345678"]["email"]:
            # Build mock result for send_batch_notifications
            results = [{
                "FIDE ID": "12345678",
                "Player Name": "Alice Smith",
                "Rating History": alice_scraped_history,
                "New Months": alice_new_months
            }]

            # Use the actual send_batch_notifications function
            sent, failed = email_notifier.send_batch_notifications(results, player_data)

            assert sent == 1
            assert failed == 0
            mock_server.sendmail.assert_called()

            # Verify email was sent to correct recipients
            call_args = mock_server.sendmail.call_args
            recipients = call_args[0][1]
            assert "alice@example.com" in recipients


@patch('email_notifier.smtplib.SMTP')
class TestFullEmailNotificationPipeline:
    """Full end-to-end pipeline test for email notifications."""

    def test_full_pipeline_load_process_send(self, mock_smtp_class, tmp_path):
        """Test complete pipeline: load → process → detect new months → send emails."""
        from datetime import date

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Setup file paths
        players_file = tmp_path / "players.csv"
        history_file = tmp_path / "history.csv"
        output_file = tmp_path / "ratings_output.csv"

        # Create player data (mix of opted-in, opted-out, and different emails)
        players_file.write_text(
            "FIDE ID,email\n"
            "12345678,alice@example.com\n"
            "87654321,bob@example.com\n"
            "11111111,\n"
            "22222222,charlie@example.com\n"
        )

        # Create historical ratings (baseline data - October)
        history_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-10-31,12345678,Alice Smith,2440,2300,2100\n"
            "2025-10-31,87654321,Bob Jones,2500,2400,2200\n"
            "2025-10-31,11111111,Charlie Brown,2340,2240,2140\n"
            "2025-10-31,22222222,Diana Prince,2600,2550,2500\n"
        )

        # Step 1: Load player data
        player_data = fide_scraper.load_player_data_from_csv(str(players_file))
        assert len(player_data) == 4

        # Verify players are loaded correctly
        assert player_data["12345678"]["email"] == "alice@example.com"
        assert player_data["87654321"]["email"] == "bob@example.com"
        assert player_data["11111111"]["email"] == ""  # Opted out
        assert player_data["22222222"]["email"] == "charlie@example.com"

        # Step 2: Load historical ratings
        historical_data = fide_scraper.load_historical_ratings_by_player(str(history_file))
        assert len(historical_data) == 4

        # Step 3: Simulate scraped history (some with new months, some without)
        scraped_histories = {
            "12345678": [{"date": date(2025, 11, 30), "standard": 2450, "rapid": 2300, "blitz": 2100}],  # New month
            "87654321": [{"date": date(2025, 11, 30), "standard": 2500, "rapid": 2410, "blitz": 2200}],  # New month
            "11111111": [{"date": date(2025, 10, 31), "standard": 2340, "rapid": 2240, "blitz": 2140}],  # Same month
            "22222222": [{"date": date(2025, 10, 31), "standard": 2600, "rapid": 2550, "blitz": 2500}],  # Same month
        }

        # Step 4: Detect new months for each player
        all_new_months = {}
        for fide_id, scraped_history in scraped_histories.items():
            new_months = fide_scraper.detect_new_months(
                fide_id, scraped_history, historical_data
            )
            all_new_months[fide_id] = new_months

        # Verify new month detection
        assert len(all_new_months["12345678"]) == 1  # Alice has new month
        assert len(all_new_months["87654321"]) == 1  # Bob has new month
        assert len(all_new_months["11111111"]) == 0  # Charlie no new months
        assert len(all_new_months["22222222"]) == 0  # Diana no new months

        # Step 5: Build results for batch notifications
        player_names = {
            "12345678": "Alice Smith",
            "87654321": "Bob Jones",
            "11111111": "Charlie Brown",
            "22222222": "Diana Prince"
        }

        results = []
        for fide_id, new_months in all_new_months.items():
            results.append({
                "FIDE ID": fide_id,
                "Player Name": player_names[fide_id],
                "Rating History": scraped_histories[fide_id],
                "New Months": new_months
            })

        # Send batch notifications
        sent, failed = email_notifier.send_batch_notifications(results, player_data)

        # Verify emails were sent
        assert sent == 2  # Only Alice and Bob should get emails (have new months and emails)
        assert failed == 0
        assert mock_server.sendmail.call_count == 2

        # Step 6: Verify email recipients
        all_calls = mock_server.sendmail.call_args_list

        # Extract all recipients from all calls
        all_recipients = set()
        for call in all_calls:
            recipients = call[0][1]
            all_recipients.update(recipients)

        # Verify correct recipients received emails
        assert "alice@example.com" in all_recipients
        assert "bob@example.com" in all_recipients
        # Opted-out and unchanged players should not be recipients
        assert "charlie@example.com" not in all_recipients or len([c for c in all_calls if "charlie@example.com" in c[0][1]]) == 0

    def test_full_pipeline_first_run_no_history(self, mock_smtp_class, tmp_path):
        """Test pipeline on first run with no historical data."""
        from datetime import date

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Setup files
        players_file = tmp_path / "players.csv"
        history_file = tmp_path / "history.csv"

        # Create player data
        players_file.write_text(
            "FIDE ID,email\n"
            "12345678,alice@example.com\n"
            "87654321,\n"
        )

        # Create empty history (first run)
        history_file.write_text("Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n")

        # Load data
        player_data = fide_scraper.load_player_data_from_csv(str(players_file))
        historical_data = fide_scraper.load_historical_ratings_by_player(str(history_file))
        # Historical data should be empty
        assert len(historical_data) == 0

        # Simulate scraped history (first run - all months are new)
        scraped_history = [{"date": date(2025, 11, 30), "standard": 2400, "rapid": 2300, "blitz": 2100}]

        # Detect new months (all months should be new on first run)
        new_months = fide_scraper.detect_new_months(
            "12345678", scraped_history, historical_data
        )

        # All months should be detected as new (first run)
        assert len(new_months) == 1
        assert new_months[0]["date"] == date(2025, 11, 30)
        assert new_months[0]["standard"] == 2400

        # Emails SHOULD be sent on first run (new months detected)
        results = [{
            "FIDE ID": "12345678",
            "Player Name": "Alice Smith",
            "Rating History": scraped_history,
            "New Months": new_months
        }]

        sent, failed = email_notifier.send_batch_notifications(results, player_data)
        assert sent == 1  # Email sent for first run with new month
        assert mock_server.sendmail.call_count == 1

    def test_full_pipeline_with_all_rating_types_changed(self, mock_smtp_class, tmp_path):
        """Test pipeline with new month showing all rating types."""
        from datetime import date

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Setup files
        players_file = tmp_path / "players.csv"
        history_file = tmp_path / "history.csv"

        players_file.write_text("FIDE ID,email\n12345678,alice@example.com\n")

        history_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-10-31,12345678,Alice Smith,2440,2300,2100\n"
        )

        # Load data
        player_data = fide_scraper.load_player_data_from_csv(str(players_file))
        historical_data = fide_scraper.load_historical_ratings_by_player(str(history_file))

        # Simulate scraped history with new month showing large rating changes
        scraped_history = [{"date": date(2025, 11, 30), "standard": 2500, "rapid": 2400, "blitz": 2250}]

        # Detect new months
        new_months = fide_scraper.detect_new_months(
            "12345678", scraped_history, historical_data
        )

        # Should detect one new month
        assert len(new_months) == 1
        assert new_months[0]["date"] == date(2025, 11, 30)
        assert new_months[0]["standard"] == 2500
        assert new_months[0]["rapid"] == 2400
        assert new_months[0]["blitz"] == 2250

        # Send notification
        results = [{
            "FIDE ID": "12345678",
            "Player Name": "Alice Smith",
            "Rating History": scraped_history,
            "New Months": new_months
        }]

        sent, failed = email_notifier.send_batch_notifications(results, player_data)

        # Email should be sent successfully
        assert sent == 1
        assert failed == 0
        assert mock_server.sendmail.call_count == 1

    def test_full_pipeline_unrated_becomes_rated(self, mock_smtp_class, tmp_path):
        """Test pipeline when player gets first rated month."""
        from datetime import date

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Setup files
        players_file = tmp_path / "players.csv"
        history_file = tmp_path / "history.csv"

        players_file.write_text("FIDE ID,email\n12345678,alice@example.com\n")

        history_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-10-31,12345678,Alice Smith,,,\n"
        )

        # Load data
        player_data = fide_scraper.load_player_data_from_csv(str(players_file))
        historical_data = fide_scraper.load_historical_ratings_by_player(str(history_file))

        # Player now has ratings in a new month
        scraped_history = [{"date": date(2025, 11, 30), "standard": 2400, "rapid": 2300, "blitz": 2100}]

        # Detect new months
        new_months = fide_scraper.detect_new_months(
            "12345678", scraped_history, historical_data
        )

        # Should detect the new month with ratings
        assert len(new_months) == 1
        assert new_months[0]["date"] == date(2025, 11, 30)
        assert new_months[0]["standard"] == 2400
        assert new_months[0]["rapid"] == 2300
        assert new_months[0]["blitz"] == 2100

        # Send notification
        results = [{
            "FIDE ID": "12345678",
            "Player Name": "Alice Smith",
            "Rating History": scraped_history,
            "New Months": new_months
        }]

        sent, failed = email_notifier.send_batch_notifications(results, player_data)

        # Email should be sent
        assert sent == 1
        assert failed == 0


class TestSendBatchNotifications:
    """Tests for send_batch_notifications integration function."""

    @patch('email_notifier.smtplib.SMTP')
    def test_send_batch_notifications_with_changes(self, mock_smtp_class):
        """Test sending batch notifications to players with new months."""
        from datetime import date

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Setup test data
        player_data = {
            "12345678": {"email": "alice@example.com"},
            "87654321": {"email": "bob@example.com"},
            "11111111": {"email": ""},  # Opted out
        }

        results = [
            {
                "FIDE ID": "12345678",
                "Player Name": "Alice Smith",
                "Standard": 2450,
                "Rapid": 2300,
                "Blitz": 2100,
                "Rating History": [
                    {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2300, "blitz": 2100},
                    {"date": date(2025, 10, 31), "standard": 2440, "rapid": 2300, "blitz": 2100}
                ],
                "New Months": [{"date": date(2025, 11, 30), "standard": 2450, "rapid": 2300, "blitz": 2100}]  # Has new month
            },
            {
                "FIDE ID": "87654321",
                "Player Name": "Bob Jones",
                "Standard": 2500,
                "Rapid": 2400,
                "Blitz": 2200,
                "Rating History": [
                    {"date": date(2025, 11, 30), "standard": 2500, "rapid": 2400, "blitz": 2200}
                ],
                "New Months": []  # No new months
            },
            {
                "FIDE ID": "11111111",
                "Player Name": "Charlie Brown",
                "Standard": 2340,
                "Rapid": 2240,
                "Blitz": 2140,
                "Rating History": [
                    {"date": date(2025, 11, 30), "standard": 2340, "rapid": 2240, "blitz": 2140}
                ],
                "New Months": [{"date": date(2025, 11, 30), "standard": 2340, "rapid": 2240, "blitz": 2140}]  # Has new month but no email
            }
        ]

        # Send notifications
        sent, failed = email_notifier.send_batch_notifications(
            results,
            player_data
        )

        # Should send 1 (Alice), skip Bob (no new months), skip Charlie (no email)
        assert sent == 1
        assert failed == 0
        assert mock_server.sendmail.call_count == 1

    @patch('email_notifier.smtplib.SMTP')
    def test_send_batch_notifications_all_changes(self, mock_smtp_class):
        """Test sending notifications when all players have new months."""
        from datetime import date

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        player_data = {
            "12345678": {"email": "alice@example.com"},
            "87654321": {"email": "bob@example.com"},
        }

        results = [
            {
                "FIDE ID": "12345678",
                "Player Name": "Alice Smith",
                "Standard": 2450,
                "Rating History": [
                    {"date": date(2025, 11, 30), "standard": 2450, "rapid": None, "blitz": None},
                    {"date": date(2025, 10, 31), "standard": 2440, "rapid": None, "blitz": None}
                ],
                "New Months": [{"date": date(2025, 11, 30), "standard": 2450, "rapid": None, "blitz": None}]
            },
            {
                "FIDE ID": "87654321",
                "Player Name": "Bob Jones",
                "Standard": 2510,
                "Rating History": [
                    {"date": date(2025, 11, 30), "standard": 2510, "rapid": None, "blitz": None},
                    {"date": date(2025, 10, 31), "standard": 2500, "rapid": None, "blitz": None}
                ],
                "New Months": [{"date": date(2025, 11, 30), "standard": 2510, "rapid": None, "blitz": None}]
            },
        ]

        sent, failed = email_notifier.send_batch_notifications(
            results,
            player_data
        )

        assert sent == 2
        assert failed == 0
        assert mock_server.sendmail.call_count == 2

    @patch('email_notifier.smtplib.SMTP')
    def test_send_batch_notifications_no_changes(self, mock_smtp_class):
        """Test sending notifications when no players have new months."""
        from datetime import date

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        player_data = {
            "12345678": {"email": "alice@example.com"},
            "87654321": {"email": "bob@example.com"},
        }

        results = [
            {
                "FIDE ID": "12345678",
                "Player Name": "Alice Smith",
                "Standard": 2440,
                "Rating History": [
                    {"date": date(2025, 11, 30), "standard": 2440, "rapid": None, "blitz": None}
                ],
                "New Months": []  # No new months
            },
            {
                "FIDE ID": "87654321",
                "Player Name": "Bob Jones",
                "Standard": 2500,
                "Rating History": [
                    {"date": date(2025, 11, 30), "standard": 2500, "rapid": None, "blitz": None}
                ],
                "New Months": []  # No new months
            },
        ]

        sent, failed = email_notifier.send_batch_notifications(
            results,
            player_data
        )

        assert sent == 0
        assert failed == 0
        assert mock_server.sendmail.call_count == 0

    @patch('email_notifier.smtplib.SMTP')
    def test_send_batch_notifications_with_errors(self, mock_smtp_class):
        """Test handling errors during batch notification sending."""
        from datetime import date

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server
        # First call succeeds, second fails
        mock_server.sendmail.side_effect = [None, smtplib.SMTPException("Error")]

        player_data = {
            "12345678": {"email": "alice@example.com"},
            "87654321": {"email": "bob@example.com"},
        }

        results = [
            {
                "FIDE ID": "12345678",
                "Player Name": "Alice Smith",
                "Standard": 2450,
                "Rating History": [
                    {"date": date(2025, 11, 30), "standard": 2450, "rapid": None, "blitz": None},
                    {"date": date(2025, 10, 31), "standard": 2440, "rapid": None, "blitz": None}
                ],
                "New Months": [{"date": date(2025, 11, 30), "standard": 2450, "rapid": None, "blitz": None}]
            },
            {
                "FIDE ID": "87654321",
                "Player Name": "Bob Jones",
                "Standard": 2510,
                "Rating History": [
                    {"date": date(2025, 11, 30), "standard": 2510, "rapid": None, "blitz": None},
                    {"date": date(2025, 10, 31), "standard": 2500, "rapid": None, "blitz": None}
                ],
                "New Months": [{"date": date(2025, 11, 30), "standard": 2510, "rapid": None, "blitz": None}]
            },
        ]

        sent, failed = email_notifier.send_batch_notifications(
            results,
            player_data
        )

        assert sent == 1
        assert failed == 1

    @patch('email_notifier.smtplib.SMTP')
    def test_send_batch_notifications_empty_results(self, mock_smtp_class):
        """Test sending notifications with empty results."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        player_data = {}
        results = []

        sent, failed = email_notifier.send_batch_notifications(
            results,
            player_data
        )

        assert sent == 0
        assert failed == 0
        assert mock_server.sendmail.call_count == 0


@pytest.mark.integration
class TestFideIdsApiIntegration:
    """Integration tests for FIDE IDs API augmentation feature."""

    @patch('fide_scraper.requests.get')
    def test_fetch_fide_ids_api_success(self, mock_get):
        """Test successful API fetch with valid response."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fide_ids": ["12345678", "23456789", "34567890"],
            "count": 3
        }
        mock_get.return_value = mock_response

        # Test fetch
        result = fide_scraper.fetch_fide_ids_from_api(
            "https://eduklein.cloud/api/fide-ids/",
            "test_token"
        )

        assert result is not None
        assert len(result) == 3
        assert "12345678" in result
        assert "23456789" in result
        assert "34567890" in result
        
        # Verify API was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "Authorization" in call_args[1]["headers"]
        assert call_args[1]["headers"]["Authorization"] == "Token test_token"

    @patch('fide_scraper.requests.get')
    def test_fetch_fide_ids_api_empty_response(self, mock_get):
        """Test API fetch with empty fide_ids array."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fide_ids": [],
            "count": 0
        }
        mock_get.return_value = mock_response

        result = fide_scraper.fetch_fide_ids_from_api(
            "https://eduklein.cloud/api/fide-ids/",
            "test_token"
        )

        # Empty array should return None
        assert result is None

    @patch('fide_scraper.requests.get')
    def test_fetch_fide_ids_api_auth_error(self, mock_get):
        """Test API fetch with authentication failure (401)."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = fide_scraper.fetch_fide_ids_from_api(
            "https://eduklein.cloud/api/fide-ids/",
            "invalid_token"
        )

        assert result is None

    @patch('fide_scraper.requests.get')
    def test_fetch_fide_ids_api_timeout(self, mock_get):
        """Test API fetch with timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        result = fide_scraper.fetch_fide_ids_from_api(
            "https://eduklein.cloud/api/fide-ids/",
            "test_token"
        )

        assert result is None

    def test_merge_player_ids_no_duplicates(self):
        """Test merge with no overlapping IDs."""
        csv_ids = ["100", "200", "300"]
        api_ids = ["400", "500"]

        all_ids, new_ids = fide_scraper.merge_player_ids(csv_ids, api_ids)

        assert len(all_ids) == 5
        assert new_ids == ["400", "500"]

    def test_merge_player_ids_with_duplicates(self):
        """Test merge with overlapping IDs."""
        csv_ids = ["100", "200", "300"]
        api_ids = ["200", "300", "400", "500"]

        all_ids, new_ids = fide_scraper.merge_player_ids(csv_ids, api_ids)

        assert len(all_ids) == 5
        assert set(all_ids) == {"100", "200", "300", "400", "500"}
        assert new_ids == ["400", "500"]

    def test_merge_player_ids_empty_csv(self):
        """Test merge with empty CSV."""
        csv_ids = []
        api_ids = ["100", "200", "300"]

        all_ids, new_ids = fide_scraper.merge_player_ids(csv_ids, api_ids)

        assert len(all_ids) == 3
        assert new_ids == ["100", "200", "300"]

    def test_augment_players_file_creates_new_file(self, tmp_path):
        """Test augment_players_file creates file if it doesn't exist."""
        csv_file = tmp_path / "players.csv"
        new_ids = ["12345678", "23456789"]

        result = fide_scraper.augment_players_file(str(csv_file), new_ids)

        assert result is True
        assert csv_file.exists()

        # Verify file content
        with open(csv_file, 'r') as f:
            content = f.read()
            assert "FIDE ID" in content
            assert "12345678" in content
            assert "23456789" in content

    def test_augment_players_file_appends_to_existing(self, tmp_path):
        """Test augment_players_file appends to existing file."""
        # Create initial file
        csv_file = tmp_path / "players.csv"
        with open(csv_file, 'w') as f:
            f.write("FIDE ID,email\n")
            f.write("11111111,alice@example.com\n")
            f.write("22222222,bob@example.com\n")

        # Augment with new IDs
        new_ids = ["33333333", "44444444"]
        result = fide_scraper.augment_players_file(str(csv_file), new_ids)

        assert result is True

        # Verify all IDs are present
        with open(csv_file, 'r') as f:
            content = f.read()
            assert "11111111" in content  # Original
            assert "22222222" in content  # Original
            assert "33333333" in content  # New
            assert "44444444" in content  # New

    def test_augment_players_file_empty_new_ids(self, tmp_path):
        """Test augment_players_file with no new IDs."""
        csv_file = tmp_path / "players.csv"
        
        result = fide_scraper.augment_players_file(str(csv_file), [])

        # Should succeed but not create file
        assert result is True

    @patch('fide_scraper.requests.get')
    def test_api_augmentation_full_flow(self, mock_get, tmp_path):
        """Test complete API augmentation flow."""
        # Setup
        csv_file = tmp_path / "players.csv"
        with open(csv_file, 'w') as f:
            f.write("FIDE ID,email\n")
            f.write("11111111,alice@example.com\n")

        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fide_ids": ["11111111", "22222222", "33333333"],
            "count": 3
        }
        mock_get.return_value = mock_response

        # Execute flow
        api_ids = fide_scraper.fetch_fide_ids_from_api(
            "https://eduklein.cloud/api/fide-ids/",
            "test_token"
        )
        assert api_ids is not None

        player_data = fide_scraper.load_player_data_from_csv(str(csv_file))
        csv_ids = list(player_data.keys())
        all_ids, new_ids = fide_scraper.merge_player_ids(csv_ids, api_ids)

        assert new_ids == ["22222222", "33333333"]

        result = fide_scraper.augment_players_file(str(csv_file), new_ids)
        assert result is True

        # Verify final file
        player_data = fide_scraper.load_player_data_from_csv(str(csv_file))
        final_ids = list(player_data.keys())
        assert set(final_ids) == {"11111111", "22222222", "33333333"}

    @patch('fide_scraper.requests.get')
    def test_graceful_degradation_api_unavailable(self, mock_get, tmp_path):
        """Test scraper continues when API is unavailable."""
        import requests
        
        # Setup
        csv_file = tmp_path / "players.csv"
        with open(csv_file, 'w') as f:
            f.write("FIDE ID,email\n")
            f.write("12345678,test@example.com\n")

        # Mock API failure
        mock_get.side_effect = requests.exceptions.ConnectionError()

        # API fetch should fail gracefully
        api_ids = fide_scraper.fetch_fide_ids_from_api(
            "https://eduklein.cloud/api/fide-ids/",
            "test_token"
        )
        assert api_ids is None

        # But loading existing file should still work
        player_data = fide_scraper.load_player_data_from_csv(str(csv_file))
        csv_ids = list(player_data.keys())
        assert csv_ids == ["12345678"]

class TestEdgeCases:
    """Tests for edge cases and deployment readiness."""

    @patch('fide_scraper.requests.get')
    def test_missing_api_configuration(self, mock_get, tmp_path):
        """T024: Test with missing/invalid API configuration to verify graceful handling."""
        # Setup CSV file
        csv_file = tmp_path / "players.csv"
        with open(csv_file, 'w') as f:
            f.write("FIDE ID,email\n")
            f.write("11111111,test@example.com\n")

        # Test with empty endpoint
        result = fide_scraper.fetch_fide_ids_from_api("", "test_token")
        assert result is None
        assert not mock_get.called, "API should not be called with empty endpoint"

        # Test with empty token
        result = fide_scraper.fetch_fide_ids_from_api(
            "https://eduklein.cloud/api/fide-ids/", ""
        )
        assert result is None
        assert not mock_get.called, "API should not be called with empty token"

        # Test with None values
        result = fide_scraper.fetch_fide_ids_from_api(None, None)
        assert result is None

        # CSV should still be loadable
        player_data = fide_scraper.load_player_data_from_csv(str(csv_file))
        csv_ids = list(player_data.keys())
        assert csv_ids == ["11111111"]

    def test_malformed_csv_file_handling(self, tmp_path):
        """T025: Test with malformed CSV file to verify error recovery."""
        # Test 1: CSV with missing FIDE ID column
        malformed_csv = tmp_path / "malformed1.csv"
        with open(malformed_csv, 'w') as f:
            f.write("email,name\n")
            f.write("test@example.com,Test Player\n")

        with pytest.raises(ValueError, match="missing required headers"):
            fide_scraper.load_player_data_from_csv(str(malformed_csv))

        # Test 2: CSV with invalid FIDE IDs
        malformed_csv2 = tmp_path / "malformed2.csv"
        with open(malformed_csv2, 'w') as f:
            f.write("FIDE ID,email\n")
            f.write("abc,test@example.com\n")
            f.write("123,invalid@example.com\n")  # Too short
            f.write("11111111,valid@example.com\n")  # Valid

        player_data = fide_scraper.load_player_data_from_csv(str(malformed_csv2))
        result = list(player_data.keys())
        assert result == ["11111111"], "Should skip invalid IDs and return only valid ones"

        # Test 3: Empty CSV
        empty_csv = tmp_path / "empty.csv"
        with open(empty_csv, 'w') as f:
            f.write("")

        with pytest.raises(ValueError, match="CSV file is empty"):
            fide_scraper.load_player_data_from_csv(str(empty_csv))

        # Test 4: CSV with only headers
        header_only_csv = tmp_path / "headers_only.csv"
        with open(header_only_csv, 'w') as f:
            f.write("FIDE ID,email\n")

        player_data = fide_scraper.load_player_data_from_csv(str(header_only_csv))
        assert player_data == {}, "Should return empty dict for CSV with only headers"

    @patch('fide_scraper.requests.get')
    def test_large_api_response_performance(self, mock_get, tmp_path):
        """T026: Test with large API response (1000+ IDs) to verify performance (<10 seconds)."""
        import time

        # Setup CSV with some existing IDs
        csv_file = tmp_path / "players.csv"
        with open(csv_file, 'w') as f:
            f.write("FIDE ID,email\n")
            for i in range(100):
                f.write(f"{1000000 + i},player{i}@example.com\n")

        # Create large API response (1000 IDs)
        large_fide_ids = [f"{2000000 + i}" for i in range(1000)]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"fide_ids": large_fide_ids, "count": 1000}
        mock_get.return_value = mock_response

        # Measure performance
        start_time = time.time()

        # API fetch
        api_ids = fide_scraper.fetch_fide_ids_from_api(
            "https://eduklein.cloud/api/fide-ids/",
            "test_token"
        )
        assert api_ids is not None
        assert len(api_ids) == 1000

        # CSV load
        player_data = fide_scraper.load_player_data_from_csv(str(csv_file))
        csv_ids = list(player_data.keys())
        assert len(csv_ids) == 100

        # Merge
        all_ids, new_ids = fide_scraper.merge_player_ids(csv_ids, api_ids)
        assert len(all_ids) == 1100
        assert len(new_ids) == 1000

        # Augment
        result = fide_scraper.augment_players_file(str(csv_file), new_ids)
        assert result is True

        elapsed_time = time.time() - start_time

        # Verify performance requirement: <10 seconds
        assert elapsed_time < 10, f"Performance test failed: took {elapsed_time:.2f}s (must be <10s)"

        # Verify file integrity
        player_data = fide_scraper.load_player_data_from_csv(str(csv_file))
        final_ids = list(player_data.keys())
        assert len(final_ids) == 1100

    def test_error_message_clarity(self, tmp_path):
        """T027: Verify error messages are clear and actionable for operators."""
        # Test 1: Missing file raises FileNotFoundError
        with pytest.raises(FileNotFoundError, match="not found"):
            fide_scraper.load_player_data_from_csv("/nonexistent/path/players.csv")

        # Test 2: Invalid CSV column raises ValueError
        invalid_csv = tmp_path / "invalid.csv"
        with open(invalid_csv, 'w') as f:
            f.write("email,name\n")

        with pytest.raises(ValueError, match="missing required headers"):
            fide_scraper.load_player_data_from_csv(str(invalid_csv))

        # Test 3: Verify error handling in API calls
        # Empty endpoint should gracefully return None
        result = fide_scraper.fetch_fide_ids_from_api("", "token")
        assert result is None, "Should return None for empty endpoint"

        # Empty token should gracefully return None
        result = fide_scraper.fetch_fide_ids_from_api("https://example.com/api/", "")
        assert result is None, "Should return None for empty token"

        # Test 4: CSV with invalid IDs logs warning but continues
        invalid_ids_csv = tmp_path / "invalid_ids.csv"
        with open(invalid_ids_csv, 'w') as f:
            f.write("FIDE ID,email\n")
            f.write("abc,test@example.com\n")  # Invalid: non-numeric
            f.write("12,test2@example.com\n")  # Invalid: too short
            f.write("11111111,valid@example.com\n")  # Valid

        player_data = fide_scraper.load_player_data_from_csv(str(invalid_ids_csv))
        result = list(player_data.keys())
        assert result == ["11111111"], "Should skip invalid IDs and continue"

    def test_graceful_degradation_mixed_scenario(self, tmp_path):
        """T029: Verify system degradation when components fail (CSV exists, API fails)."""
        # Setup CSV file
        csv_file = tmp_path / "players.csv"
        with open(csv_file, 'w') as f:
            f.write("FIDE ID,email\n")
            f.write("11111111,test@example.com\n")
            f.write("22222222,test2@example.com\n")

        # API fails
        api_ids = None  # Simulates API failure

        # Merge should handle None API gracefully
        player_data = fide_scraper.load_player_data_from_csv(str(csv_file))
        csv_ids = list(player_data.keys())
        if api_ids is None:
            api_ids = []

        all_ids, new_ids = fide_scraper.merge_player_ids(csv_ids, api_ids)
        assert all_ids == ["11111111", "22222222"]
        assert new_ids == []

        # Augment with no new IDs (should be no-op)
        result = fide_scraper.augment_players_file(str(csv_file), new_ids)
        assert result is True

        # File should be unchanged
        player_data = fide_scraper.load_player_data_from_csv(str(csv_file))
        final_ids = list(player_data.keys())
        assert set(final_ids) == {"11111111", "22222222"}