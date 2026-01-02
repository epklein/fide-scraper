"""
Email notification module for FIDE Rating Scraper.

Handles composing and sending email notifications to players about rating changes.
"""

import os
import sys
import logging
import smtplib
from typing import Optional, Tuple, List, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _compose_notification_email(
    player_name: str,
    fide_id: str,
    rating_history: List[Dict],
    fide_profile_url: Optional[str] = None
) -> Tuple[str, str]:
    """
    Compose a notification email about rating changes.

    Generates an email subject and body informing a player about their FIDE rating updates.
    The email includes their name, FIDE ID, and details of changed ratings between the two
    most recent entries in their rating history.

    Args:
        player_name: Player's full name (e.g., "Alice Smith")
        fide_id: Player's FIDE ID (e.g., "12345678")
        rating_history: List of rating history records (most recent first).
                       Each record contains: {date: date_obj, standard: int|None, rapid: int|None, blitz: int|None}
                       Example: [
                           {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2310, "blitz": 1900},
                           {"date": date(2025, 10, 31), "standard": 2440, "rapid": 2300, "blitz": 1890}
                       ]
        fide_profile_url: Optional full URL to FIDE profile. If not provided, will be constructed from fide_id.

    Returns:
        Tuple of (subject, body) containing the email subject line and body content

    Examples:
        rating_history = [
            {"date": date(2025, 11, 30), "standard": 2450, "rapid": 2310, "blitz": 1900},
            {"date": date(2025, 10, 31), "standard": 2440, "rapid": 2300, "blitz": 1890}
        ]
        subject, body = _compose_notification_email(
            "Alice Smith",
            "12345678",
            rating_history
        )
        # subject: "Your FIDE Rating Update - Alice Smith"
        # body: Contains formatted rating changes between the two most recent months
    """
    # Construct FIDE profile URL if not provided
    if fide_profile_url is None:
        fide_profile_url = f"https://ratings.fide.com/profile/{fide_id}"

    # Compose subject
    subject = f"Your FIDE Rating Update - {player_name}"
    # Compose body
    lines = [
        "Dear " + player_name + ",",
        "",
        "Your FIDE ratings have been updated. Here are the changes:",
        ""
    ]

    # Extract changes from the two most recent history entries
    if len(rating_history) >= 2:
        # Most recent month (index 0) and previous month (index 1)
        current = rating_history[0]
        previous = rating_history[1]

        # Build changes dictionary from the two most recent entries
        changes = {
            "Standard": (previous.get("standard"), current.get("standard")),
            "Rapid": (previous.get("rapid"), current.get("rapid")),
            "Blitz": (previous.get("blitz"), current.get("blitz"))
        }

        # Add rating changes (sorted by rating type for consistency)
        for rating_type in sorted(changes.keys()):
            old_value, new_value = changes[rating_type]

            # Format old rating (handle None as "unrated")
            old_str = str(old_value) if old_value is not None else "unrated"
            # Format new rating (handle None as "unrated")
            new_str = str(new_value) if new_value is not None else "unrated"

            # Format the change line
            lines.append(f"{rating_type} Rating: {old_str} → {new_str}")
    elif len(rating_history) == 1:
        # Only one month available, show the ratings
        current = rating_history[0]
        standard = current.get("standard")
        rapid = current.get("rapid")
        blitz = current.get("blitz")

        standard_str = str(standard) if standard is not None else "unrated"
        rapid_str = str(rapid) if rapid is not None else "unrated"
        blitz_str = str(blitz) if blitz is not None else "unrated"

        lines.append(f"Standard Rating: {standard_str}")
        lines.append(f"Rapid Rating: {rapid_str}")
        lines.append(f"Blitz Rating: {blitz_str}")

    # Add footer with FIDE profile URL
    lines.extend([
        "",
        "FIDE ID: " + fide_id,
        "Profile: " + fide_profile_url,
        "",
        "Best regards,",
        "FIDE Rating Monitor",
        "Written by Eduardo Klein (https://eduklein.com.br/)"
    ])

    body = "\n".join(lines)

    return subject, body


def _send_email_notification(
    recipient: str,
    cc: Optional[str],
    subject: str,
    body: str
) -> bool:
    """
    Send an email notification via SMTP.

    Sends an email with the given subject and body to the recipient, optionally CC'ing another address.
    Uses SMTP configuration from environment variables. All errors are logged and handled gracefully
    without raising exceptions.

    Args:
        recipient: Email address of the primary recipient (required)
        cc: Optional email address to CC on the message
        subject: Email subject line
        body: Email body content (plain text)

    Returns:
        True if email was sent successfully, False if any error occurred during sending

    Environment Variables (read from .env):
        SMTP_SERVER: SMTP server hostname (default: localhost)
        SMTP_PORT: SMTP server port (default: 587)
        SMTP_USERNAME: Optional username for SMTP authentication
        SMTP_PASSWORD: Optional password for SMTP authentication
        FROM_EMAIL: Email address to use as the sender (From field). If not set, falls back to SMTP_USERNAME or default.

    Examples:
        success = _send_email_notification(
            "alice@example.com",
            "admin@example.com",
            "Your FIDE Rating Update - Alice Smith",
            "Dear Alice Smith,\nYour ratings have changed..."
        )
        if success:
            print("Email sent successfully")
        else:
            print("Failed to send email")
    """
    try:
        # Get SMTP configuration from environment
        smtp_server = os.getenv('SMTP_SERVER', 'localhost')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME', '').strip() or None
        smtp_password = os.getenv('SMTP_PASSWORD', '').strip() or None
        from_email = os.getenv('FROM_EMAIL', '').strip() or None

        # Validate recipient email
        if not recipient or not isinstance(recipient, str):
            logging.error(f"Invalid recipient email: {recipient}")
            return False

        # Determine From email address: FROM_EMAIL > SMTP_USERNAME > default
        sender_email = from_email if from_email else (smtp_username if smtp_username else 'noreply@chesshub.cloud')

        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient

        # Add CC if provided
        if cc and isinstance(cc, str) and cc.strip():
            msg['Cc'] = cc.strip()

        # Attach plain text body
        msg.attach(MIMEText(body, 'plain'))

        # Build recipient list for sending (recipient + cc)
        recipient_list = [recipient]
        if cc and isinstance(cc, str) and cc.strip():
            recipient_list.append(cc.strip())

        # Connect to SMTP server and send
        try:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.starttls()

            # Authenticate if credentials provided
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)

            # Send email (use sender_email for the envelope sender)
            server.sendmail(
                sender_email,
                recipient_list,
                msg.as_string()
            )

            server.quit()
            logging.info(f"Email sent successfully to {recipient}" + (f" (CC: {cc})" if cc else ""))
            return True

        except smtplib.SMTPAuthenticationError as e:
            logging.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logging.error(f"SMTP error occurred: {e}")
            return False
        except ConnectionError as e:
            logging.error(f"Connection error to SMTP server: {e}")
            return False
        except TimeoutError as e:
            logging.error(f"SMTP connection timeout: {e}")
            return False

    except (ValueError, TypeError) as e:
        logging.error(f"Invalid configuration or parameters: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error sending email: {e}")
        return False


def send_batch_notifications(
    results: List[Dict],
    player_data: Dict[str, Dict[str, str]]
) -> Tuple[int, int]:
    """
    Send email notifications to players with new rating history months.

    Processes batch results and sends notification emails to players who:
    1. Have detected new months in their rating history
    2. Have a valid email address configured
    3. Have not opted out (email field not empty)

    Args:
        results: List of player results from process_batch() with 'new_months' key
        player_data: Dictionary of player data with emails {fide_id: {"email": "..."}, ...}

    Returns:
        Tuple of (sent_count, failed_count) for logging and reporting

    Side Effects:
        Sends SMTP emails for players with new months. Logs all attempts. Continues on errors.
    """
    # Read admin CC email from environment variable
    admin_cc_email = os.getenv('ADMIN_CC_EMAIL', '').strip() or None

    sent_count = 0
    failed_count = 0

    for result in results:
        fide_id = result.get('FIDE ID')
        player_name = result.get('Player Name', '')
        rating_history = result.get('Rating History', [])
        new_months = result.get('New Months', [])

        # Skip if no new months detected
        if not new_months:
            continue

        # Get player email
        if fide_id not in player_data:
            continue

        player_email = player_data[fide_id].get('email', '').strip()

        # Skip if player has no email (opted out)
        if not player_email:
            continue

        try:
            # Compose email
            subject, body = _compose_notification_email(
                player_name,
                fide_id,
                rating_history
            )

            # Send email
            success = _send_email_notification(
                player_email,
                admin_cc_email,
                subject,
                body
            )

            if success:
                sent_count += 1
                print(f"✓ Email sent to {player_name} ({player_email})", file=sys.stderr)
            else:
                failed_count += 1
                print(f"✗ Failed to send email to {player_name} ({player_email})", file=sys.stderr)

        except Exception as e:
            failed_count += 1
            print(f"✗ Error sending email to {fide_id}: {e}", file=sys.stderr)

    return sent_count, failed_count
