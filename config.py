# Location: /opt/my_flask_app/config.py
# Last updated: 2025-03-28

# Mail settings
MAIL_SERVER = "eng-mail.arubanetworks.com"
MAIL_PORT = 25
MAIL_USE_TLS = True
MAIL_USE_SSL = False
MAIL_USERNAME = None  # No authentication required
MAIL_PASSWORD = None
MAIL_DEFAULT_SENDER = ("Premium Services", "Premium_Automations@hpe.com")
# Additional email settings for notifications and output emailing
ADMIN_EMAILS = ["superbot@hpe.com", "admin2@hpe.com"]
EMAIL_SUBJECT = "Your Script Output from HPE Aruba Intelligence"
EMAIL_BODY = "Please find attached your requested output files."

# Database configuration (using MySQL with PyMySQL)
SQLALCHEMY_DATABASE_URI = "mysql+pymysql://flask_user:whopee@localhost/my_flask_db"
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = "CHANGE_ME_PLEASE"  # Change this to a unique, secure value!

# File Upload Configuration
UPLOAD_FOLDER = "/home/manish/flask_uploads"
ALLOWED_EXTENSIONS = {"tar", "tgz", "gz"}

# 7-Zip command (for non-POSIX systems; on Ubuntu, tar is used)
SEVEN_ZIP_CMD = "/usr/bin/7z"

# Retention settings
RAW_RETENTION_DAYS = 30    # Retain raw tar files and untarred intermediate data for 30 days
IO_RETENTION_DAYS = 360    # Retain generated input and output folders for 360 days
