"""
Handles email rendering and delivery.
Supports local dry-run (writing to file/console) and SMTP transmission via environment credentials.
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

def deliver_report(
    html_content: str,
    markdown_content: str,
    config: Any,
    dry_run: bool = False
) -> bool:
    """
    Delivers the report.
    If dry_run is True, writes the reports to files inside the state/ directory and logs the action.
    If dry_run is False, attempts to transmit the email using SMTP credentials from env variables.
    
    Returns True if delivery succeeded (or was skipped in dry-run/delegated), and False otherwise.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    subject = f"Competitive Intelligence Digest - {date_str}"
    
    # Ensure state directory exists
    state_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "state"))
    os.makedirs(state_dir, exist_ok=True)
    
    # 1. Handle Dry Run
    if dry_run:
        logger.info("DRY-RUN MODE: Writing report output files to state/ directory.")
        md_path = os.path.join(state_dir, "latest_report.md")
        html_path = os.path.join(state_dir, "latest_report.html")
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print(f"\n--- DRY RUN: REPORT PREPARED ---")
        print(f"Markdown report saved to: {md_path}")
        print(f"HTML report saved to: {html_path}")
        print(f"Subject: {subject}")
        print(f"Featured Updates Count: {markdown_content.count('####')}")
        print(f"---------------------------------\n")
        return True

    # 2. Save latest files on disk anyway (for GHA step upload or mail action support)
    md_path = os.path.join(state_dir, "latest_report.md")
    html_path = os.path.join(state_dir, "latest_report.html")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 3. Extract Delivery Targets
    to_email = os.environ.get("REPORT_TO_EMAIL") or config.delivery.to_email
    if not to_email:
        logger.error("No recipient email specified in config or environment. Skipping transmission.")
        return False
        
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    
    # If no SMTP credentials are provided in the environment, we assume the GHA workflow
    # will handle email delivery using the generated report file. We log this and return True
    # to allow the state file commit to proceed.
    if not smtp_user or not smtp_pass:
        logger.info(
            "SMTP credentials not found in environment. Email delivery is delegated "
            "to the subsequent GitHub Action workflow step."
        )
        return True
        
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    try:
        smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    except ValueError:
        smtp_port = 465
        
    logger.info(f"Attempting to send email via SMTP to {to_email}...")
    
    # Build Multipart Email Message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    
    # Attach plain text and HTML versions for client compatibility
    msg.attach(MIMEText(markdown_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))
    
    try:
        # Connect to SMTP server (SSL vs TLS based on port)
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
            server.starttls()
            
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        logger.info("Email delivered successfully via SMTP.")
        return True
    except Exception as e:
        logger.exception(f"Failed to deliver email via SMTP: {e}")
        return False
