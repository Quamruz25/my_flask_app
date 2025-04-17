#!/usr/bin/python3.8
# Location: /opt/my_flask_app/run.py
# Last updated: 2025-04-14
# Entry point for the Flask app.
# This version sets the timezone, frees port 5000 if needed,
# and then starts the app with the reloader disabled.

import os
import subprocess
from app import create_app
from flask_migrate import Migrate  # Explicitly import to ensure CLI recognition

# Set the time zone explicitly
os.environ["TZ"] = "America/Los_Angeles"

def free_port(port=5000):
    try:
        # Use fuser to list PIDs using the port (Python 3.6 compatible)
        result = subprocess.run(["fuser", f"{port}/tcp"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        pids = result.stdout.strip().split()
        current_pid = str(os.getpid())
        if pids:
            pids_to_kill = [pid for pid in pids if pid != current_pid]
            if pids_to_kill:
                for pid in pids_to_kill:
                    try:
                        subprocess.run(["kill", "-9", pid], check=True)
                        print(f"Killed process {pid} on port {port}.")
                    except subprocess.CalledProcessError as e:
                        print(f"Error killing process {pid}: {e}")
            else:
                print(f"No external process found using port {port}.")
        else:
            print(f"No process using port {port} found.")
    except Exception as e:
        print(f"Error checking port {port}: {e}")

# Create the Flask app
app = create_app()

if __name__ == "__main__":
    free_port(5000)
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)