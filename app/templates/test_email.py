#!/usr/bin/env python3
import smtplib
import logging
from email.message import EmailMessage

# Logging for debug
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Mail configuration
#MAIL_SERVER = "eng-mail.arubanetworks.com"
MAIL_SERVER = "10.249.101.1"
MAIL_PORT = 25
MAIL_USE_TLS = False  # Set to False if relay does not support STARTTLS
MAIL_USERNAME = None
MAIL_PASSWORD = None
MAIL_DEFAULT_SENDER = ("Premium Services", "Premium_Automations@hpe.com")

def send_test_email():
    msg = EmailMessage()
    msg["Subject"] = "Test Email from Python"
    msg["From"] = MAIL_DEFAULT_SENDER[1]
    msg["To"] = "superbot@hpe.com"
    msg.set_content("This is a test email sent from a Python script using a relay.")

    try:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10) as server:
            server.set_debuglevel(1)
            if MAIL_USE_TLS:
                server.starttls()
            if MAIL_USERNAME and MAIL_PASSWORD:
                server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
            logging.info("Test email sent successfully.")
    except Exception as e:
        logging.error("Failed to send email: %s", e)

if __name__ == "__main__":
    send_test_email()
