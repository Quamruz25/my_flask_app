# Location: /opt/my_flask_app/app/cleanup.py
import os
import shutil
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="/opt/my_flask_app/logs/cleanup.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def cleanup_files(app):
    with app.app_context():
        upload_folder = app.config["UPLOAD_FOLDER"]
        now = datetime.utcnow()
        raw_retention = timedelta(days=app.config.get("RAW_RETENTION_DAYS", 30))
        io_retention = timedelta(days=app.config.get("IO_RETENTION_DAYS", 360))

        # Walk through the UPLOAD_FOLDER recursively
        for root, dirs, files in os.walk(upload_folder, topdown=False):
            # Clean up files
            for file in files:
                file_path = os.path.join(root, file)
                mtime = datetime.utcfromtimestamp(os.path.getmtime(file_path))
                if file.endswith((".tar", ".tar.gz", ".tgz", ".gz")):
                    if now - mtime > raw_retention:
                        try:
                            os.remove(file_path)
                            logger.info("Deleted raw file: %s", file_path)
                        except Exception as e:
                            logger.error("Error deleting file %s: %s", file_path, e)
                elif file.endswith((".html", ".json", ".txt", ".log")):
                    if now - mtime > io_retention:
                        try:
                            os.remove(file_path)
                            logger.info("Deleted I/O file: %s", file_path)
                        except Exception as e:
                            logger.error("Error deleting file %s: %s", file_path, e)

            # Clean up directories
            for d in dirs:
                folder_path = os.path.join(root, d)
                mtime = datetime.utcfromtimestamp(os.path.getmtime(folder_path))
                if d in ["input", "output", "log"]:
                    if now - mtime > io_retention:
                        try:
                            shutil.rmtree(folder_path)
                            logger.info("Deleted I/O folder: %s", folder_path)
                        except Exception as e:
                            logger.error("Error deleting folder %s: %s", folder_path, e)
                elif d != "config":  # Keep config folder for keyword script
                    if now - mtime > raw_retention:
                        try:
                            shutil.rmtree(folder_path)
                            logger.info("Deleted intermediate folder: %s", folder_path)
                        except Exception as e:
                            logger.error("Error deleting folder %s: %s", folder_path, e)

def init_cleanup_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=lambda: cleanup_files(app), trigger='cron', hour=2, minute=0)
    scheduler.start()
    app.logger.info("Cleanup scheduler started to run daily at 2 AM.")