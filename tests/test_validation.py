"""
Unit tests for FIDE ID and email validation functions.

Tests the validate_fide_id() and validate_email() functions
with various valid and invalid inputs.
"""

import pytest
import sys
import os

# Add parent directory to path to import fide_scraper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fide_scraper import validate_fide_id, validate_email


class TestValidateFideId:
    """Test cases for validate_fide_id() function."""

    def test_valid_fide_ids(self):
        """Test that valid FIDE IDs pass validation."""
        valid_ids = [
            "12345678",  # 8 digits
            "1234",      # 4 digits (minimum)
            "1234567890",  # 10 digits (maximum)
            "538026660",  # Real example
            "1503014",    # 7 digits
        ]
        for fide_id in valid_ids:
            assert validate_fide_id(fide_id) is True, f"Expected {fide_id} to be valid"

    def test_invalid_length(self):
        """Test that FIDE IDs with invalid lengths fail."""
        invalid_ids = [
            "123",        # 3 digits (too short)
            "12345678901",  # 11 digits (too long)
            "",           # empty string
        ]
        for fide_id in invalid_ids:
            assert validate_fide_id(fide_id) is False, f"Expected {fide_id} to be invalid"

    def test_non_numeric(self):
        """Test that non-numeric FIDE IDs fail."""
        invalid_ids = [
            "abcd1234",   # contains letters
            "1234-5678",  # contains dash
            "1234 5678",  # contains space
            "12.34.5678", # contains dots
            "0x12345678", # hex notation
        ]
        for fide_id in invalid_ids:
            assert validate_fide_id(fide_id) is False, f"Expected {fide_id} to be invalid"

    def test_none_and_non_string(self):
        """Test that None and non-string inputs fail."""
        invalid_inputs = [
            None,
            12345678,     # integer instead of string
            12.345,       # float
            [],           # list
            {},           # dict
        ]
        for invalid_input in invalid_inputs:
            assert validate_fide_id(invalid_input) is False, f"Expected {invalid_input} to be invalid"


class TestValidateEmail:
    """Test cases for validate_email() function."""

    def test_valid_emails(self):
        """Test that valid email addresses pass validation."""
        valid_emails = [
            "alice@example.com",
            "bob@example.co.uk",
            "charlie.brown@test.org",
            "dave_smith@company.io",
            "eve123@sub.domain.com",
            "user+tag@example.com",
            "a@b.co",
        ]
        for email in valid_emails:
            assert validate_email(email) is True, f"Expected {email} to be valid"

    def test_empty_email(self):
        """Test that empty string is treated as valid (opt-out)."""
        assert validate_email("") is True
        assert validate_email(None) is True

    def test_invalid_emails(self):
        """Test that invalid email addresses fail."""
        invalid_emails = [
            "notanemail",           # no @ symbol
            "@example.com",         # missing username
            "alice@",               # missing domain
            "alice@@example.com",   # double @
            "alice@example",        # no TLD
            "alice @example.com",   # space in username
            "alice@ example.com",   # space in domain
            "alice@example .com",   # space in TLD
        ]
        for email in invalid_emails:
            assert validate_email(email) is False, f"Expected {email} to be invalid"

    def test_edge_cases(self):
        """Test edge cases for email validation."""
        # Single character username and domain
        assert validate_email("a@b.c") is True

        # Hyphenated domain
        assert validate_email("user@my-domain.com") is True

        # Multiple dots in domain
        assert validate_email("user@mail.co.uk") is True


class TestValidationIntegration:
    """Integration tests combining FIDE ID and email validation."""

    def test_validate_player_data(self):
        """Test validating a player record with both FIDE ID and email."""
        player_data = {
            "fide_id": "12345678",
            "email": "player@example.com",
        }
        assert validate_fide_id(player_data["fide_id"]) is True
        assert validate_email(player_data["email"]) is True

    def test_validate_player_with_empty_email(self):
        """Test validating a player without an email (opted out)."""
        player_data = {
            "fide_id": "12345678",
            "email": "",
        }
        assert validate_fide_id(player_data["fide_id"]) is True
        assert validate_email(player_data["email"]) is True

    def test_validate_invalid_player(self):
        """Test validating a player with invalid data."""
        player_data = {
            "fide_id": "123",  # too short
            "email": "invalid-email",
        }
        assert validate_fide_id(player_data["fide_id"]) is False
        assert validate_email(player_data["email"]) is False
