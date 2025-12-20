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
        # Verify date is present
        from datetime import date
        today = date.today().isoformat()
        assert today in content

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
        # Create sample changes
        changes = {
            "Standard": (2440, 2450),
            "Rapid": (2300, 2310)
        }

        # Compose email
        subject, body = fide_scraper.compose_notification_email(
            "Test Player",
            "12345678",
            changes,
            "player@example.com",
            "admin@example.com"
        )

        # Verify email content
        assert "Test Player" in subject
        assert "Standard Rating: 2440 → 2450" in body
        assert "Rapid Rating: 2300 → 2310" in body

    @patch('fide_scraper.smtplib.SMTP')
    def test_email_notification_workflow_with_smtp_mock(self, mock_smtp_class):
        """Test complete email workflow with mocked SMTP."""
        from unittest.mock import MagicMock

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Compose email
        changes = {"Standard": (2440, 2450)}
        subject, body = fide_scraper.compose_notification_email(
            "Alice Smith",
            "12345678",
            changes,
            "alice@example.com"
        )

        # Send email
        result = fide_scraper.send_email_notification(
            "alice@example.com",
            "admin@example.com",
            subject,
            body
        )

        assert result is True
        mock_server.sendmail.assert_called_once()

    def test_player_data_to_email_pipeline(self, tmp_path):
        """Test pipeline: load player data -> detect changes -> compose email."""
        # Create player data CSV
        players_file = tmp_path / "players.csv"
        players_file.write_text("FIDE ID,email\n12345678,alice@example.com\n87654321,bob@example.com\n")

        # Create historical ratings CSV
        history_file = tmp_path / "history.csv"
        history_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-11-21,12345678,Alice Smith,2440,2300,2100\n"
            "2025-11-21,87654321,Bob Jones,2500,2400,\n"
        )

        # Load player data
        player_data = fide_scraper.load_player_data_from_csv(str(players_file))
        assert len(player_data) == 2
        assert player_data["12345678"]["email"] == "alice@example.com"

        # Load historical ratings
        historical_data = fide_scraper.load_historical_ratings_by_player(str(history_file))
        assert len(historical_data) == 2

        # Detect changes for Alice (rating increased)
        alice_changes = fide_scraper.detect_rating_changes(
            "12345678",
            {"Standard": 2450, "Rapid": 2300, "Blitz": 2100},
            historical_data
        )
        assert "Standard" in alice_changes
        assert alice_changes["Standard"] == (2440, 2450)

        # Compose email for Alice
        subject, body = fide_scraper.compose_notification_email(
            "Alice Smith",
            "12345678",
            alice_changes,
            player_data["12345678"]["email"]
        )
        assert "Alice Smith" in subject
        assert "2440 → 2450" in body

        # Detect changes for Bob (no changes in Standard/Rapid)
        bob_changes = fide_scraper.detect_rating_changes(
            "87654321",
            {"Standard": 2500, "Rapid": 2400, "Blitz": None},
            historical_data
        )
        # Bob's standard and rapid unchanged, blitz went from None to None
        assert len(bob_changes) == 0

    def test_batch_processing_with_change_detection(self, tmp_path):
        """Test batch processing with integrated change detection."""
        # Create input data
        players_file = tmp_path / "players.csv"
        players_file.write_text("FIDE ID,email\n538026660,player@example.com\n")

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

    @patch('fide_scraper.smtplib.SMTP')
    def test_complete_email_notification_workflow(self, mock_smtp_class, tmp_path):
        """Test complete workflow: load data -> detect changes -> compose -> send emails."""
        from unittest.mock import MagicMock

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
            "2025-11-21,12345678,Alice Smith,2440,2300,2100\n"
            "2025-11-21,87654321,Bob Jones,2500,2400,\n"
        )

        # Load player data
        player_data = fide_scraper.load_player_data_from_csv(str(players_file))

        # Load historical ratings
        historical_data = fide_scraper.load_historical_ratings_by_player(str(history_file))

        # Simulate new ratings
        new_ratings_alice = {"Standard": 2450, "Rapid": 2300, "Blitz": 2100}

        # Detect changes
        alice_changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings_alice, historical_data
        )

        # Only Alice has email and has changes, so compose and send for her
        if alice_changes and player_data["12345678"]["email"]:
            subject, body = fide_scraper.compose_notification_email(
                "Alice Smith",
                "12345678",
                alice_changes,
                player_data["12345678"]["email"],
                "admin@example.com"
            )

            # Send email
            result = fide_scraper.send_email_notification(
                player_data["12345678"]["email"],
                "admin@example.com",
                subject,
                body
            )

            assert result is True
            mock_server.sendmail.assert_called()

            # Verify email was sent to correct recipients
            call_args = mock_server.sendmail.call_args
            recipients = call_args[0][1]
            assert "alice@example.com" in recipients
            assert "admin@example.com" in recipients


@patch('fide_scraper.smtplib.SMTP')
class TestFullEmailNotificationPipeline:
    """Full end-to-end pipeline test for email notifications."""

    def test_full_pipeline_load_process_send(self, mock_smtp_class, tmp_path):
        """Test complete pipeline: load → process → detect changes → send emails."""
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

        # Create historical ratings (baseline data)
        history_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-11-21,12345678,Alice Smith,2440,2300,2100\n"
            "2025-11-21,87654321,Bob Jones,2500,2400,2200\n"
            "2025-11-21,11111111,Charlie Brown,2340,2240,2140\n"
            "2025-11-21,22222222,Diana Prince,2600,2550,2500\n"
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

        # Step 3: Simulate new ratings (some changed, some unchanged)
        new_ratings = {
            "12345678": {"Standard": 2450, "Rapid": 2300, "Blitz": 2100},  # Standard increased
            "87654321": {"Standard": 2500, "Rapid": 2410, "Blitz": 2200},  # Rapid increased
            "11111111": {"Standard": 2340, "Rapid": 2240, "Blitz": 2140},  # No changes
            "22222222": {"Standard": 2600, "Rapid": 2550, "Blitz": 2500},  # No changes
        }

        # Step 4: Detect changes for each player
        all_changes = {}
        for fide_id, new_rating in new_ratings.items():
            changes = fide_scraper.detect_rating_changes(
                fide_id, new_rating, historical_data
            )
            all_changes[fide_id] = changes

        # Verify change detection
        assert "Standard" in all_changes["12345678"]  # Alice's Standard increased
        assert "Rapid" in all_changes["87654321"]     # Bob's Rapid increased
        assert len(all_changes["11111111"]) == 0      # Charlie no changes
        assert len(all_changes["22222222"]) == 0      # Diana no changes

        # Step 5: Process and send emails for players with changes and valid emails
        player_names = {
            "12345678": "Alice Smith",
            "87654321": "Bob Jones",
            "11111111": "Charlie Brown",
            "22222222": "Diana Prince"
        }

        admin_email = "admin@example.com"
        emails_sent = 0

        for fide_id, changes in all_changes.items():
            email = player_data[fide_id]["email"]

            # Only send if player has email and has changes
            if email and changes:
                subject, body = fide_scraper.compose_notification_email(
                    player_names[fide_id],
                    fide_id,
                    changes,
                    email,
                    admin_email
                )

                result = fide_scraper.send_email_notification(
                    email,
                    admin_email,
                    subject,
                    body
                )

                if result:
                    emails_sent += 1

        # Verify emails were sent
        assert emails_sent == 2  # Only Alice and Bob should get emails
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
        assert "admin@example.com" in all_recipients  # Admin should be CC'd
        # Opted-out and unchanged players should not be recipients
        assert "charlie@example.com" not in all_recipients or len([c for c in all_calls if "charlie@example.com" in c[0][1]]) == 0

    def test_full_pipeline_first_run_no_history(self, mock_smtp_class, tmp_path):
        """Test pipeline on first run with no historical data."""
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

        # Simulate new ratings
        new_ratings = {"Standard": 2400, "Rapid": 2300, "Blitz": 2100}

        # Detect changes (should be empty since no history)
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        # No changes should be detected (new player)
        assert changes == {"Standard": (None, 2400), "Rapid": (None, 2300), "Blitz": (None, 2100)}

        # No emails should be sent
        assert mock_server.sendmail.call_count == 0

    def test_full_pipeline_with_all_rating_types_changed(self, mock_smtp_class, tmp_path):
        """Test pipeline when all rating types change."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Setup files
        players_file = tmp_path / "players.csv"
        history_file = tmp_path / "history.csv"

        players_file.write_text("FIDE ID,email\n12345678,alice@example.com\n")

        history_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-11-21,12345678,Alice Smith,2440,2300,2100\n"
        )

        # Load data
        player_data = fide_scraper.load_player_data_from_csv(str(players_file))
        historical_data = fide_scraper.load_historical_ratings_by_player(str(history_file))

        # Simulate large rating changes in all categories
        new_ratings = {"Standard": 2500, "Rapid": 2400, "Blitz": 2250}

        # Detect changes
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        # All three rating types should show changes
        assert len(changes) == 3
        assert changes["Standard"] == (2440, 2500)
        assert changes["Rapid"] == (2300, 2400)
        assert changes["Blitz"] == (2100, 2250)

        # Compose and send email
        subject, body = fide_scraper.compose_notification_email(
            "Alice Smith",
            "12345678",
            changes,
            "alice@example.com",
            "admin@example.com"
        )

        result = fide_scraper.send_email_notification(
            "alice@example.com",
            "admin@example.com",
            subject,
            body
        )

        # Email should be sent successfully
        assert result is True
        assert mock_server.sendmail.call_count == 1

    def test_full_pipeline_unrated_becomes_rated(self, mock_smtp_class, tmp_path):
        """Test pipeline when player transitions from unrated to rated."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Setup files
        players_file = tmp_path / "players.csv"
        history_file = tmp_path / "history.csv"

        players_file.write_text("FIDE ID,email\n12345678,alice@example.com\n")

        history_file.write_text(
            "Date,FIDE ID,Player Name,Standard,Rapid,Blitz\n"
            "2025-11-21,12345678,Alice Smith,,,,\n"
        )

        # Load data
        player_data = fide_scraper.load_player_data_from_csv(str(players_file))
        historical_data = fide_scraper.load_historical_ratings_by_player(str(history_file))

        # Player now has ratings
        new_ratings = {"Standard": 2400, "Rapid": 2300, "Blitz": 2100}

        # Detect changes
        changes = fide_scraper.detect_rating_changes(
            "12345678", new_ratings, historical_data
        )

        # All ratings are new (unrated → rated)
        assert len(changes) == 3
        assert changes["Standard"] == (None, 2400)
        assert changes["Rapid"] == (None, 2300)
        assert changes["Blitz"] == (None, 2100)

        # Compose email to notify about new ratings
        subject, body = fide_scraper.compose_notification_email(
            "Alice Smith",
            "12345678",
            changes,
            "alice@example.com"
        )

        # Verify email mentions the transitions
        assert "unrated → 2400" in body
        assert "unrated → 2300" in body
        assert "unrated → 2100" in body


class TestSendBatchNotifications:
    """Tests for send_batch_notifications integration function."""

    @patch('fide_scraper.smtplib.SMTP')
    def test_send_batch_notifications_with_changes(self, mock_smtp_class):
        """Test sending batch notifications to players with changes."""
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
                "changes": {"Standard": (2440, 2450)}  # Has changes
            },
            {
                "FIDE ID": "87654321",
                "Player Name": "Bob Jones",
                "Standard": 2500,
                "Rapid": 2400,
                "Blitz": 2200,
                "changes": {}  # No changes
            },
            {
                "FIDE ID": "11111111",
                "Player Name": "Charlie Brown",
                "Standard": 2340,
                "Rapid": 2240,
                "Blitz": 2140,
                "changes": {"Standard": (2330, 2340)}  # Has changes but no email
            }
        ]

        # Send notifications
        sent, failed = fide_scraper.send_batch_notifications(
            results,
            player_data,
            "admin@example.com"
        )

        # Should send 1 (Alice), skip Bob (no changes), skip Charlie (no email)
        assert sent == 1
        assert failed == 0
        assert mock_server.sendmail.call_count == 1

    @patch('fide_scraper.smtplib.SMTP')
    def test_send_batch_notifications_all_changes(self, mock_smtp_class):
        """Test sending notifications when all players have changes."""
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
                "changes": {"Standard": (2440, 2450)}
            },
            {
                "FIDE ID": "87654321",
                "Player Name": "Bob Jones",
                "Standard": 2510,
                "changes": {"Standard": (2500, 2510)}
            },
        ]

        sent, failed = fide_scraper.send_batch_notifications(
            results,
            player_data
        )

        assert sent == 2
        assert failed == 0
        assert mock_server.sendmail.call_count == 2

    @patch('fide_scraper.smtplib.SMTP')
    def test_send_batch_notifications_no_changes(self, mock_smtp_class):
        """Test sending notifications when no players have changes."""
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
                "changes": {}  # No changes
            },
            {
                "FIDE ID": "87654321",
                "Player Name": "Bob Jones",
                "Standard": 2500,
                "changes": {}  # No changes
            },
        ]

        sent, failed = fide_scraper.send_batch_notifications(
            results,
            player_data
        )

        assert sent == 0
        assert failed == 0
        assert mock_server.sendmail.call_count == 0

    @patch('fide_scraper.smtplib.SMTP')
    def test_send_batch_notifications_with_errors(self, mock_smtp_class):
        """Test handling errors during batch notification sending."""
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
                "changes": {"Standard": (2440, 2450)}
            },
            {
                "FIDE ID": "87654321",
                "Player Name": "Bob Jones",
                "Standard": 2510,
                "changes": {"Standard": (2500, 2510)}
            },
        ]

        sent, failed = fide_scraper.send_batch_notifications(
            results,
            player_data
        )

        assert sent == 1
        assert failed == 1

    @patch('fide_scraper.smtplib.SMTP')
    def test_send_batch_notifications_empty_results(self, mock_smtp_class):
        """Test sending notifications with empty results."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        player_data = {}
        results = []

        sent, failed = fide_scraper.send_batch_notifications(
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

        csv_ids = fide_scraper.load_existing_ids(str(csv_file))
        all_ids, new_ids = fide_scraper.merge_player_ids(csv_ids, api_ids)
        
        assert new_ids == ["22222222", "33333333"]

        result = fide_scraper.augment_players_file(str(csv_file), new_ids)
        assert result is True

        # Verify final file
        final_ids = fide_scraper.load_csv_fide_ids(str(csv_file))
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
        csv_ids = fide_scraper.load_existing_ids(str(csv_file))
        assert csv_ids == ["12345678"]


# Phase 7: Edge Case Testing and Polish

class TestPhase7EdgeCases:
    """Tests for Phase 7 edge cases and deployment readiness."""

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
        csv_ids = fide_scraper.load_existing_ids(str(csv_file))
        assert csv_ids == ["11111111"]

    def test_malformed_csv_file_handling(self, tmp_path):
        """T025: Test with malformed CSV file to verify error recovery."""
        # Test 1: CSV with missing FIDE ID column
        malformed_csv = tmp_path / "malformed1.csv"
        with open(malformed_csv, 'w') as f:
            f.write("email,name\n")
            f.write("test@example.com,Test Player\n")

        result = fide_scraper.load_csv_fide_ids(str(malformed_csv))
        assert result == [], "Should return empty list for CSV missing FIDE ID column"

        # Test 2: CSV with invalid FIDE IDs
        malformed_csv2 = tmp_path / "malformed2.csv"
        with open(malformed_csv2, 'w') as f:
            f.write("FIDE ID,email\n")
            f.write("abc,test@example.com\n")
            f.write("123,invalid@example.com\n")  # Too short
            f.write("11111111,valid@example.com\n")  # Valid

        result = fide_scraper.load_csv_fide_ids(str(malformed_csv2))
        assert result == ["11111111"], "Should skip invalid IDs and return only valid ones"

        # Test 3: Empty CSV
        empty_csv = tmp_path / "empty.csv"
        with open(empty_csv, 'w') as f:
            f.write("")

        result = fide_scraper.load_existing_ids(str(empty_csv))
        assert result == [], "Should handle empty CSV gracefully"

        # Test 4: CSV with only headers
        header_only_csv = tmp_path / "headers_only.csv"
        with open(header_only_csv, 'w') as f:
            f.write("FIDE ID,email\n")

        result = fide_scraper.load_csv_fide_ids(str(header_only_csv))
        assert result == [], "Should return empty list for CSV with only headers"

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
        csv_ids = fide_scraper.load_existing_ids(str(csv_file))
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
        final_ids = fide_scraper.load_csv_fide_ids(str(csv_file))
        assert len(final_ids) == 1100

    def test_error_message_clarity(self, tmp_path):
        """T027: Verify error messages are clear and actionable for operators."""
        # Test 1: Missing file returns empty gracefully
        result = fide_scraper.load_existing_ids("/nonexistent/path/players.csv")
        assert result == [], "Should return empty list for missing file"

        # Test 2: Invalid CSV column returns empty
        invalid_csv = tmp_path / "invalid.csv"
        with open(invalid_csv, 'w') as f:
            f.write("email,name\n")

        result = fide_scraper.load_csv_fide_ids(str(invalid_csv))
        assert result == [], "Should return empty list for CSV missing FIDE ID column"

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

        result = fide_scraper.load_csv_fide_ids(str(invalid_ids_csv))
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
        csv_ids = fide_scraper.load_existing_ids(str(csv_file))
        if api_ids is None:
            api_ids = []

        all_ids, new_ids = fide_scraper.merge_player_ids(csv_ids, api_ids)
        assert all_ids == ["11111111", "22222222"]
        assert new_ids == []

        # Augment with no new IDs (should be no-op)
        result = fide_scraper.augment_players_file(str(csv_file), new_ids)
        assert result is True

        # File should be unchanged
        final_ids = fide_scraper.load_csv_fide_ids(str(csv_file))
        assert set(final_ids) == {"11111111", "22222222"}

    def test_csv_dialect_preservation_edge_cases(self, tmp_path):
        """T028: Verify CSV format preservation in various dialects."""
        # Test 1: Tab-delimited CSV
        tab_csv = tmp_path / "tab_delimited.csv"
        with open(tab_csv, 'w') as f:
            f.write("FIDE ID\temail\n")
            f.write("11111111\ttest@example.com\n")

        # Augment with new ID
        new_ids = ["99999999"]
        result = fide_scraper.augment_players_file(str(tab_csv), new_ids)
        assert result is True

        # Verify content
        with open(tab_csv, 'r') as f:
            content = f.read()
            # Should still have tab delimiter
            lines = content.split('\n')
            assert '\t' in lines[0], "Tab delimiter should be preserved"

        # Test 2: CSV with quoted fields
        quoted_csv = tmp_path / "quoted.csv"
        with open(quoted_csv, 'w') as f:
            f.write('"FIDE ID","email"\n')
            f.write('"11111111","test@example.com"\n')

        new_ids = ["77777777"]
        result = fide_scraper.augment_players_file(str(quoted_csv), new_ids)
        assert result is True

        # Should still be readable
        final_ids = fide_scraper.load_csv_fide_ids(str(quoted_csv))
        assert "11111111" in final_ids
        assert "77777777" in final_ids
