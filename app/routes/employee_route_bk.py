# Location: /opt/my_flask_app/app/routes/employee_routes.py
#provied by Grok

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
import os
import subprocess
import uuid
import json
import logging
from app import db
from app.models import SessionMetadata

employee_bp = Blueprint("employee_bp", __name__, url_prefix="/employee")
# Use current_app.logger if within an app context; otherwise, use a module-level logger.
logger = current_app.logger if current_app else logging.getLogger(__name__)

def find_techsupport_log(transaction_folder):
    """
    Recursively search for a file named 'tech-support.log' within the transaction_folder.
    Returns the full path if found, or None.
    """
    for root, dirs, files in os.walk(transaction_folder):
        for file in files:
            if file == "tech-support.log":
                logger.debug("Found tech-support.log at: %s", os.path.join(root, file))
                return os.path.join(root, file)
    logger.warning("tech-support.log not found in transaction folder: %s", transaction_folder)
    return None

def extract_block_from_lines(lines, start_phrase, stop_condition):
    block = []
    capturing = False
    for line in lines:
        if not capturing and line.strip() == start_phrase:
            capturing = True
        if capturing:
            block.append(line)
            if stop_condition(line):
                break
    return "".join(block)

def generate_ccr_input(transaction_folder):
    """
    Generate CCR_input.txt by extracting:
      - The "show running-config" block (from that line until a line exactly "end")
      - The "show vrrp stats all" block (from that line until the next line starting with "show")
      - The "show ap active" block (from that line until the next line starting with "show")
    """
    log_path = find_techsupport_log(transaction_folder)
    if not log_path:
        return ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error("Error reading tech-support.log: %s", e)
        return ""
    
    running_config = extract_block_from_lines(
        lines,
        "show running-config",
        lambda line: line.strip().lower() == "end"
    )
    vrrp_block = extract_block_from_lines(
        lines,
        "show vrrp stats all",
        lambda line: line.strip().startswith("show") and line.strip() != "show vrrp stats all"
    )
    ap_active = extract_block_from_lines(
        lines,
        "show ap active",
        lambda line: line.strip().startswith("show") and line.strip() != "show ap active"
    )
    combined = running_config + "\n" + vrrp_block + "\n" + ap_active
    logger.debug("Generated CCR input length: %d characters", len(combined))
    return combined

def generate_chr_input(transaction_folder):
    """
    Generate CHR_input.txt by extracting only the "show running-config" block (until "end").
    """
    log_path = find_techsupport_log(transaction_folder)
    if not log_path:
        return ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error("Error reading tech-support.log for CHR: %s", e)
        return ""
    running_config = extract_block_from_lines(
        lines,
        "show running-config",
        lambda line: line.strip().lower() == "end"
    )
    logger.debug("Generated CHR input length: %d characters", len(running_config))
    return running_config

def generate_bucket_input(transaction_folder):
    """
    For Bucket, return the complete content of tech-support.log.
    """
    log_path = find_techsupport_log(transaction_folder)
    if not log_path:
        return ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        logger.debug("Generated Bucket input length: %d characters", len(content))
        return content
    except Exception as e:
        logger.error("Error reading tech-support.log for Bucket: %s", e)
        return ""

def generate_keyword_input(transaction_folder):
    """
    Recursively scan directories: flash, mswitch, var, and config (if exists)
    under transaction_folder and build a JSON dataset mapping each file's relative path to its content.
    """
    base_dirs = ["flash", "mswitch", "var"]
    config_dir = os.path.join(transaction_folder, "config")
    if os.path.exists(config_dir):
        base_dirs.append("config")
    
    file_data = {}
    for d in base_dirs:
        dir_path = os.path.join(transaction_folder, d)
        if not os.path.exists(dir_path):
            logger.warning("Directory not found for keyword input: %s", dir_path)
            continue
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, transaction_folder)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    file_data[rel_path] = content
                except Exception as e:
                    logger.error("Error reading file %s: %s", full_path, e)
    dataset = json.dumps(file_data, indent=2)
    logger.debug("Generated Keyword input dataset with %d files", len(file_data))
    return dataset

@employee_bp.route("/dashboard", methods=["GET", "POST"])
@login_required
def employee_dashboard():
    if request.method == "POST":
        case_number = request.form.get("case_number") or "nocasenumber"
        selected_scripts = request.form.getlist("script_option")
        if not selected_scripts:
            selected_scripts = ["ccr", "chr", "bucket", "keyword"]

        file = request.files.get("tar_file")
        if not file:
            flash("Please select a file.", "danger")
            return redirect(url_for("employee_bp.employee_dashboard"))
        filename = file.filename

        # Use the part before '@' as the user folder
        user_folder = current_user.email.split('@')[0]
        session_id = str(uuid.uuid4())
        # CHANGED: Fixed typo 'session​​​​id' to 'session_id' and corrected variable name 'session' to 'session_id'
        transaction_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], user_folder, case_number, session_id)
        os.makedirs(transaction_folder, exist_ok=True)
        current_app.logger.debug("Transaction folder created: %s", transaction_folder)

        saved_tar_path = os.path.join(transaction_folder, filename)
        file.save(saved_tar_path)
        current_app.logger.debug("Saved tar file to %s", saved_tar_path)

        # Extract the uploaded tar file using 7z (command configurable via SEVEN_ZIP_CMD)
        extract_cmd = [current_app.config.get("SEVEN_ZIP_CMD", "7z"), "x", saved_tar_path, f"-o{transaction_folder}"]
        result = subprocess.run(extract_cmd, universal_newlines=True)
        if result.returncode != 0:
            flash("Error extracting file. Check server logs.", "danger")
            current_app.logger.error("Extraction failed for %s", saved_tar_path)
            return redirect(url_for("employee_bp.employee_dashboard"))
        current_app.logger.debug("Extraction completed for %s", saved_tar_path)

        # Additional step: Process configs.tar.gz if present
        configs_tar_gz_path = os.path.join(transaction_folder, "configs.tar.gz")
        if os.path.exists(configs_tar_gz_path):
            config_folder = os.path.join(transaction_folder, "config")
            os.makedirs(config_folder, exist_ok=True)
            new_configs_path = os.path.join(config_folder, "configs.tar.gz")
            os.rename(configs_tar_gz_path, new_configs_path)
            current_app.logger.debug("Moved configs.tar.gz to config folder: %s", config_folder)
            extract_cmd_config = [current_app.config.get("SEVEN_ZIP_CMD", "7z"), "x", new_configs_path, f"-o{config_folder}"]
            result_config = subprocess.run(extract_cmd_config, universal_newlines=True)
            if result_config.returncode != 0:
                current_app.logger.error("Extraction failed for configs.tar.gz in config folder.")
            else:
                current_app.logger.debug("Extraction completed for configs.tar.gz in config folder.")

        # Create an 'input' folder in the transaction folder and generate inputs
        input_folder = os.path.join(transaction_folder, "input")
        os.makedirs(input_folder, exist_ok=True)
        current_app.logger.debug("Input folder created: %s", input_folder)

        ccr_data = generate_ccr_input(transaction_folder)
        ccr_input_path = os.path.join(input_folder, "CCR_input.txt")
        with open(ccr_input_path, "w") as f:
            f.write(ccr_data)
        current_app.logger.debug("CCR input file created: %s", ccr_input_path)

        chr_data = generate_chr_input(transaction_folder)
        chr_input_path = os.path.join(input_folder, "CHR_input.txt")
        with open(chr_input_path, "w") as f:
            f.write(chr_data)
        current_app.logger.debug("CHR input file created: %s", chr_input_path)

        bucket_data = generate_bucket_input(transaction_folder)
        bucket_input_path = os.path.join(input_folder, "bucket_input.txt")
        with open(bucket_input_path, "w") as f:
            f.write(bucket_data)
        current_app.logger.debug("Bucket input file created: %s", bucket_input_path)

        keyword_data = generate_keyword_input(transaction_folder)
        keyword_input_path = os.path.join(input_folder, "keyword_input.json")
        with open(keyword_input_path, "w") as f:
            f.write(keyword_data)
        current_app.logger.debug("Keyword input file created: %s", keyword_input_path)

        # Save session metadata in the database
        new_session = SessionMetadata(
            session_id=session_id,
            username=current_user.email,
            case_number=case_number,
            transaction_folder=transaction_folder
        )
        db.session.add(new_session)
        db.session.commit()
        current_app.logger.debug("Session metadata saved for session: %s", session_id)

        # Prepare output and log folders
        output_folder = os.path.join(transaction_folder, "output")
        log_folder = os.path.join(transaction_folder, "log")
        os.makedirs(output_folder, exist_ok=True)
        os.makedirs(log_folder, exist_ok=True)

        # Generate placeholders for output paths based on selected scripts
        output_html = os.path.join(output_folder, "ccr.html") if "ccr" in selected_scripts else None
        chr_output_html = os.path.join(output_folder, "chr.html") if "chr" in selected_scripts else None
        bucket_output_html = os.path.join(output_folder, "bucket.html") if "bucket" in selected_scripts else None
        keyword_output_html = os.path.join(output_folder, "keyword.html") if "keyword" in selected_scripts else None

        # Execute scripts based on selected_scripts
        script_mappings = {
            "ccr": {
                "script_path": "/opt/my_flask_app/scripts/CCR/Script-with-Default-Profile.py",
                "input_file": ccr_input_path,
                "output_file": output_html,
                "log_file": os.path.join(log_folder, "CCR_script.log")
            },
            "chr": {
                "script_path": "/opt/my_flask_app/scripts/CHR/script_chr.py",  # Adjust path as needed
                "input_file": chr_input_path,
                "output_file": chr_output_html,
                "output_file": chr_output_html,
                "log_file": os.path.join(log_folder, "CHR_script.log")
            },
            "bucket": {
                "script_path": "/opt/my_flask_app/scripts/Bucket/script_bucket.py",  # Adjust path as needed
                "input_file": bucket_input_path,
                "output_file": bucket_output_html,
                "log_file": os.path.join(log_folder, "Bucket_script.log")
            },
            "keyword": {
                "script_path": "/opt/my_flask_app/scripts/KeyWord/script_keyword.py",  # Adjust path as needed
                "input_file": keyword_input_path,
                "output_file": keyword_output_html,
                "log_file": os.path.join(log_folder, "Keyword_script.log")
            }
        }
        # CHANGED: Added newline after script_mappings to fix syntax error
        for script in selected_scripts:
            if script in script_mappings:
                config = script_mappings[script]
                if config["output_file"]:  # Only run if selected and output path exists
                    try:
                        result = subprocess.run(
                            ['/opt/my_flask_app/.venv/bin/python', config["script_path"], config["input_file"], config["output_file"], config["log_file"]],
                            cwd=transaction_folder,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True,
                            check=True
                        )
                        current_app.logger.debug(f"{script.upper()} script executed successfully: {result.stdout}")
                    except subprocess.CalledProcessError as e:
                        current_app.logger.error(f"{script.upper()} script failed: {e.stderr}")
                        flash(f"Error processing {script.upper()} script. Check logs.", "danger")
                    except Exception as e:
                        current_app.logger.error(f"Unexpected error running {script.upper()} script: {str(e)}")
                        flash(f"Unexpected error running {script.upper()} script.", "danger")

        flash("File uploaded and processed successfully.", "success")
        return render_template("employee_dashboard.html",
                               tar_extracted=True,
                               output_html=output_html,
                               chr_output_html=chr_output_html,
                               bucket_output_html=bucket_output_html,
                               keyword_output_html=keyword_output_html,
                               transaction_folder=transaction_folder)
    return render_template("employee_dashboard.html", tar_extracted=False)

@employee_bp.route("/download_output", methods=["GET"])
@login_required
def download_output():
    file_path = request.args.get("file_path")
    if not file_path or not os.path.exists(file_path):
        flash("File not found.", "danger")
        return redirect(url_for("employee_bp.employee_dashboard"))
    return send_file(file_path, as_attachment=True)

@employee_bp.route("/email_output", methods=["GET"])
@login_required
def email_output():
    file_path = request.args.get("file_path")
    script = request.args.get("script")
    # Implement your email sending logic (e.g., using Flask-Mail) here.
    flash(f"Email sent for {script} output.", "success")
    return redirect(url_for("employee_bp.employee_dashboard"))

@employee_bp.route("/historical", methods=["GET"])
@login_required
def historical():
    sessions = SessionMetadata.query.filter_by(username=current_user.email).all()
    uploads = []
    for s in sessions:
        # Only display the basename of the transaction folder
        folder_basename = os.path.basename(s.transaction_folder)
        uploads.append({
            "session_id": s.session_id,
            "case_number": s.case_number,
            "upload_time": s.upload_timestamp,
            "upload_folder": folder_basename,
            "filename": "logs.tar"  # Adjust if needed
        })
    return render_template("historical_files.html", uploads=uploads)

@employee_bp.route("/output_view", methods=["GET"])
@login_required
def output_view():
    session_id = request.args.get("session_id")
    session = SessionMetadata.query.filter_by(session_id=session_id).first()
    if not session:
        flash("Session not found.", "danger")
        return redirect(url_for("employee_bp.historical"))
    output_folder = os.path.join(session.transaction_folder, "output")
    zip_path = os.path.join(session.transaction_folder, "output.zip")
    try:
        subprocess.run(["zip", "-r", zip_path, output_folder], check=True)
    except Exception as e:
        current_app.logger.error("Error creating zip archive: %s", e)
        flash("Error creating zip archive.", "danger")
        return redirect(url_for("employee_bp.historical"))
    return send_file(zip_path, as_attachment=True)