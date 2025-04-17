#!/usr/bin/env python3
# Location: /home/manish/call_flask_employee_dashboard.py
"""
Script to simulate a UI POST request to /employee/dashboard, uploading logs.tar
and selecting all 4 scripts (CCR, CHR, Bucket, Keyword).
"""

import requests
import os
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/home/manish/call_flask_employee_dashboard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def call_employee_dashboard(tar_path, case_number="123", url="http://127.0.0.1:5000/employee/dashboard"):
    """
    Simulate a POST request to /employee/dashboard with logs.tar and all scripts selected.
    
    Args:
        tar_path (str): Path to logs.tar file.
        case_number (str): Case number for the request (default: "123").
        url (str): Flask app URL (default: local development server).
    """
    if not os.path.exists(tar_path):
        logger.error("logs.tar not found at %s", tar_path)
        print("Error: logs.tar not found.")
        sys.exit(1)

    # Define form data (simulating UI input)
    form_data = {
        "case_number": case_number,
        "script_option": ["ccr", "chr", "bucket", "keyword"]  # All scripts selected
    }

    # Prepare the file for upload
    files = {
        "tar_file": ("logs.tar", open(tar_path, "rb"), "application/x-tar")
    }

    # Simulate an authenticated session (adjust based on your Flask-Login setup)
    session = requests.Session()

    # If your app requires login, uncomment and adjust the login step
    # login_url = "http://127.0.0.1:5000/login"  # Adjust if your login route differs
    # login_data = {
    #     "email": "your_email@example.com",  # Replace with a valid employee email
    #     "password": "your_password"         # Replace with the password
    # }
    # login_response = session.post(login_url, data=login_data)
    # if login_response.status_code != 200 and "dashboard" not in login_response.url:
    #     logger.error("Login failed: %s", login_response.text)
    #     print("Error: Login failed. Check credentials or login route.")
    #     sys.exit(1)
    # logger.info("Logged in successfully")

    # Send the POST request to /employee/dashboard
    try:
        response = session.post(url, data=form_data, files=files)
        if response.status_code == 200:
            logger.info("Request to %s successful", url)
            logger.debug("Response content: %s", response.text[:500])  # First 500 chars for brevity
            print("Request successful. Check Flask logs or transaction folder for outputs.")
            # Extract transaction folder from response if needed (e.g., from HTML or redirect)
            if "transaction_folder" in response.text:
                start_idx = response.text.find("transaction_folder=") + len("transaction_folder=")
                end_idx = response.text.find('"', start_idx) or response.text.find("'", start_idx)
                transaction_folder = response.text[start_idx:end_idx]
                print(f"Transaction folder: {transaction_folder}")
                print(f"Outputs should be in: {os.path.join(transaction_folder, 'output')}")
        else:
            logger.error("Request failed with status %d: %s", response.status_code, response.text)
            print(f"Error: Request failed with status {response.status_code}. Check logs.")
    except requests.RequestException as e:
        logger.error("Request exception: %s", str(e))
        print(f"Error: Request failed - {str(e)}")
        sys.exit(1)

def main():
    # Define the path to logs.tar
    transaction_folder = "/home/manish/flask_uploads/quamruz/123/1861946b-154a-426b-8032-f3e7157193c4"
    tar_path = os.path.join(transaction_folder, "logs.tar")
    
    logger.info("Starting manual call to Flask employee_dashboard")
    call_employee_dashboard(tar_path, case_number="123")
    logger.info("Manual call completed")

if __name__ == "__main__":
    main()