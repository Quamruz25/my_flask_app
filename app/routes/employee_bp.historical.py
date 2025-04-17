from flask import Blueprint, current_app, render_template, flash
from flask_login import login_required
import os
from datetime import datetime

# Assuming this function exists in employee_routes.py, import it
from employee_routes import get_username  

# Ensure Blueprint is correctly set up (if not already in another file)
employee_bp = Blueprint("employee", __name__)




@employee_bp.route("/historical", methods=["GET"])
@login_required
def historical():
    import os
    from datetime import datetime

    username = get_username()
    user_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], username)
    uploads = []

    if not os.path.exists(user_folder):
        flash("No uploads found for user.", "info")
        return render_template("historical_files.html", uploads=uploads)

    # For each case folder (e.g., "1234" or "nocasenumber")
    for case_folder in os.listdir(user_folder):
        case_path = os.path.join(user_folder, case_folder)
        if os.path.isdir(case_path):
            # For each timestamp folder in the case folder
            for timestamp_folder in os.listdir(case_path):
                ts_path = os.path.join(case_path, timestamp_folder)
                if os.path.isdir(ts_path):
                    # Look for a tar file in this timestamp folder (non-recursive)
                    tar_files = [f for f in os.listdir(ts_path) if f.lower().endswith(".tar")]
                    if tar_files:
                        # For simplicity, assume one tar file per transaction
                        tar_filename = tar_files[0]
                        tar_file_path = os.path.join(ts_path, tar_filename)
                        # Use the file's modification time as the upload time
                        mod_time = os.path.getmtime(tar_file_path)
                        upload_time = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                        uploads.append({
                            "case_number": case_folder,
                            "filename": tar_filename,
                            "upload_time": upload_time,
                            "username": username,
                            "timestamp": timestamp_folder
                        })

    # Sort uploads by timestamp descending
    uploads = sorted(uploads, key=lambda x: x["timestamp"], reverse=True)
    return render_template("historical_files.html", uploads=uploads)
