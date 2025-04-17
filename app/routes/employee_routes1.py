# Location: /opt/my_flask_app/app/routes/employee_routes.py
import logging
import os
import shutil
import subprocess
import tarfile
import uuid
import json
from datetime import datetime
from pathlib import Path
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, send_file, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import SessionMetadata
from app import db
from flask_mail import Mail, Message

employee_bp = Blueprint('employee_bp', __name__, template_folder='templates')
logger = logging.getLogger('app.routes.employee_routes')

def extract_tar_recursive(file_path, extract_path, depth=0, max_depth=5):
    if depth > max_depth:
        logger.warning(f"Max extraction depth reached at {file_path}")
        return
    
    try:
        with tarfile.open(file_path, 'r:*') as tar:
            tar.extractall(path=extract_path)
        logger.debug(f"Extracted {file_path} to {extract_path} (depth {depth})")
    except Exception as e:
        logger.error(f"Error extracting {file_path}: {str(e)}")
        return
    
    for root, dirs, files in os.walk(extract_path):
        for file in files:
            if file.endswith(('.tar', '.tar.gz', '.tgz')):
                nested_tar_path = os.path.join(root, file)
                logger.debug(f"Processing nested tar file: {nested_tar_path} (depth {depth + 1})")
                extract_tar_recursive(nested_tar_path, extract_path, depth + 1, max_depth)
                try:
                    os.remove(nested_tar_path)
                    logger.debug(f"Removed nested tar file: {nested_tar_path}")
                except Exception as e:
                    logger.error(f"Error removing nested tar file {nested_tar_path}: {str(e)}")

def find_techsupport_log(transaction_folder):
    for root, dirs, files in os.walk(transaction_folder):
        for file in files:
            if file == "tech-support.log":
                logger.debug(f"Found tech-support.log at: {os.path.join(root, file)}")
                return os.path.join(root, file)
    logger.warning(f"tech-support.log not found in transaction folder: {transaction_folder}")
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
    log_path = find_techsupport_log(transaction_folder)
    if not log_path:
        return ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Error reading tech-support.log: {str(e)}")
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
    logger.debug(f"Generated CCR input length: {len(combined)} characters")
    return combined

def generate_chr_input(transaction_folder):
    log_path = find_techsupport_log(transaction_folder)
    if not log_path:
        return ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Error reading tech-support.log for CHR: {str(e)}")
        return ""
    running_config = extract_block_from_lines(
        lines,
        "show running-config",
        lambda line: line.strip().lower() == "end"
    )
    logger.debug(f"Generated CHR input length: {len(running_config)} characters")
    return running_config

def generate_bucket_input(transaction_folder):
    log_path = find_techsupport_log(transaction_folder)
    if not log_path:
        return ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        logger.debug(f"Generated Bucket input length: {len(content)} characters")
        return content
    except Exception as e:
        logger.error(f"Error reading tech-support.log for Bucket: {str(e)}")
        return ""

def generate_keyword_input(transaction_folder):
    config_dir = os.path.join(transaction_folder, "config")
    os.makedirs(config_dir, exist_ok=True)
    configs_tar_gz_path = os.path.join(transaction_folder, "configs.tar.gz")
    if os.path.exists(configs_tar_gz_path):
        new_configs_path = os.path.join(config_dir, "configs.tar.gz")
        os.rename(configs_tar_gz_path, new_configs_path)
        logger.debug(f"Moved configs.tar.gz to config folder: {config_dir}")
        extract_tar_recursive(new_configs_path, config_dir)

    base_dirs = ["flash", "var", "config"]
    file_data = {}
    for d in base_dirs:
        dir_path = os.path.join(transaction_folder, d)
        if not os.path.exists(dir_path):
            logger.warning(f"Directory not found for keyword input: {dir_path}")
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
                    logger.error(f"Error reading file {full_path}: {str(e)}")
    dataset = json.dumps(file_data, indent=2)
    logger.debug(f"Generated Keyword input dataset with {len(file_data)} files")
    return dataset

@employee_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if current_user.role != 'employee':
        logger.warning(f"Access denied for user {current_user.email}: Not an employee.")
        flash('Access denied: Employees only.')
        return redirect(url_for('auth_bp.login'))

    sessions_db = SessionMetadata.query.filter_by(username=current_user.email).all()
    sessions = []
    for session in sessions_db:
        output_dir = os.path.join(session.transaction_folder, 'output')
        session_info = {
            'session_id': session.session_id,
            'case_number': session.case_number,
            'upload_time': session.upload_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'file_name': 'logs.tar',
            'results_exist': os.path.exists(os.path.join(output_dir, 'keywordsearch.html'))
        }
        sessions.append(session_info)
    
    sessions.sort(key=lambda x: x['upload_time'], reverse=True)

    tar_extracted = False
    output_files = {}

    if request.method == 'POST':
        case_number = request.form.get('case_number')
        file = request.files.get('tar_file')  # Updated to match form field name
        script_options = request.form.getlist('script_option')

        if not case_number:
            logger.warning("File upload attempt failed: Case number is empty.")
            flash('Case number is required.')
            return redirect(url_for('employee_bp.dashboard'))

        if not file:
            logger.warning("File upload attempt failed: No file selected.")
            flash('No file uploaded.')
            return redirect(url_for('employee_bp.dashboard'))

        if not file.filename.endswith('.tar'):
            logger.warning(f"File upload attempt failed: Invalid file type {file.filename}.")
            flash('Only .tar files are allowed.')
            return redirect(url_for('employee_bp.dashboard'))

        session_id = str(uuid.uuid4())
        base_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.email, case_number)
        transaction_dir = os.path.join(base_upload_dir, session_id)
        input_dir = os.path.join(transaction_dir, 'input')
        output_dir = os.path.join(transaction_dir, 'output')
        log_dir = os.path.join(transaction_dir, 'log')

        try:
            os.makedirs(transaction_dir, exist_ok=True)
            os.makedirs(input_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(log_dir, exist_ok=True)
            logger.debug(f"Folders created: transaction={transaction_dir}, input={input_dir}, output={output_dir}, log={log_dir}")
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            flash(f'Error creating directories: {e}')
            return redirect(url_for('employee_bp.dashboard'))

        filename = secure_filename(file.filename)
        original_file_path = os.path.join(transaction_dir, filename)
        try:
            file.save(original_file_path)
            logger.debug(f"File saved: {original_file_path}")
        except Exception as e:
            logger.error(f"Error saving file {original_file_path}: {e}")
            flash(f'Error saving file: {e}')
            return redirect(url_for('employee_bp.dashboard'))

        renamed_file_path = os.path.join(transaction_dir, 'logs.tar')
        try:
            os.rename(original_file_path, renamed_file_path)
            logger.debug(f"Renamed {original_file_path} to {renamed_file_path}")
        except Exception as e:
            logger.error(f"Error renaming {original_file_path} to {renamed_file_path}: {e}")
            flash('Error processing file.')
            return redirect(url_for('employee_bp.dashboard'))

        logger.debug(f"Extracting tar file: {renamed_file_path} to {transaction_dir} (depth 0)")
        extract_tar_recursive(renamed_file_path, transaction_dir)

        scripts = []
        if 'ccr' in script_options:
            scripts.append('CCR')
        if 'chr' in script_options:
            scripts.append('CHR')
        if 'bucket' in script_options:
            scripts.append('BUCKET')
        if 'keyword' in script_options:
            scripts.append('KEYWORD')

        log_file = os.path.join(log_dir, f"{session_id}.log")
        for script in scripts:
            input_file = None
            content = None
            if script == 'CCR':
                input_file = os.path.join(input_dir, 'CCR_input.txt')
                content = generate_ccr_input(transaction_dir)
            elif script == 'CHR':
                input_file = os.path.join(input_dir, 'CHR_input.txt')
                content = generate_chr_input(transaction_dir)
            elif script == 'BUCKET':
                input_file = os.path.join(input_dir, 'bucket_input.txt')
                content = generate_bucket_input(transaction_dir)
            elif script == 'KEYWORD':
                input_file = os.path.join(input_dir, 'keyword_input.json')
                content = generate_keyword_input(transaction_dir)

            if input_file and content:
                try:
                    with open(input_file, 'w') as f:
                        f.write(content)
                    logger.debug(f"Input file created for {script.lower()}: {input_file}")
                except Exception as e:
                    logger.error(f"Error creating input file for {script}: {e}")
                    flash(f'Error creating input file for {script}: {e}')
                    continue

        for script in scripts:
            script_path = None
            script_cmd = None
            scripts_base_dir = '/opt/my_flask_app/scripts'
            output_file = os.path.join(output_dir, f"{script.lower()}_output.html")
            if script == 'CCR':
                script_path = os.path.join(scripts_base_dir, 'CCR', 'Script-with-Default-Profile.py')
                script_cmd = ['python3.8', script_path, os.path.join(input_dir, 'CCR_input.txt'), output_file, log_file]
            elif script == 'CHR':
                script_path = os.path.join(scripts_base_dir, 'CHR', 'script_chr.py')
                script_cmd = ['python3.8', script_path, os.path.join(input_dir, 'CHR_input.txt'), output_file, log_file]
            elif script == 'BUCKET':
                script_path = os.path.join(scripts_base_dir, 'Bucket', 'script_bucket.py')
                script_cmd = ['python3.8', script_path, os.path.join(input_dir, 'bucket_input.txt'), output_file, log_file]
            elif script == 'KEYWORD':
                script_path = os.path.join(scripts_base_dir, 'KeyWord', 'script_keyword.py')
                script_cmd = ['python3.8', script_path, input_dir, output_dir, log_file, session_id]
                output_file = os.path.join(output_dir, 'keywordsearch.html')

            output_files[script] = output_file
            logger.debug(f"Running {script} script with command: {' '.join(script_cmd)}")
            try:
                if not os.path.exists(script_path):
                    raise FileNotFoundError(f"Script not found: {script_path}")
                result = subprocess.run(script_cmd, capture_output=True, text=True, check=True)
                logger.debug(f"{script} script executed successfully: {result.stdout}")
                if result.stderr:
                    logger.warning(f"{script} script warnings: {result.stderr}")
            except subprocess.CalledProcessError as e:
                logger.error(f"{script} script failed: {e}\nOutput: {e.output}")
                flash(f"{script} script failed: {e.output}")
            except Exception as e:
                logger.error(f"Unexpected error running {script} script: {e}")
                flash(f"Unexpected error running {script} script: {e}")

        try:
            session_metadata = SessionMetadata(
                session_id=session_id,
                username=current_user.email,
                case_number=case_number,
                transaction_folder=transaction_dir,
                upload_timestamp=datetime.utcnow(),
                log_file=log_file
            )
            db.session.add(session_metadata)
            db.session.commit()
            logger.debug(f"Session metadata saved for session: {session_id}")
        except Exception as e:
            logger.error(f"Error saving session metadata for session {session_id}: {e}")
            db.session.rollback()
            flash(f'Error saving session metadata: {e}')
            return redirect(url_for('employee_bp.dashboard'))

        tar_extracted = True

        logger.debug(f"Rendering employee dashboard for user {current_user.email} with results.")
        return render_template('employee_dashboard.html', 
                             tar_extracted=tar_extracted,
                             session_id=session_id,
                             output_files=output_files,
                             sessions=sessions)

    logger.debug(f"Rendering employee dashboard for user {current_user.email} with {len(sessions)} sessions.")
    return render_template('employee_dashboard.html', 
                         tar_extracted=tar_extracted,
                         session_id=None,
                         output_files=output_files,
                         sessions=sessions)

@employee_bp.route('/static/<session_id>/<script>')
@login_required
def serve_static(session_id, script):
    session = SessionMetadata.query.filter_by(session_id=session_id, username=current_user.email).first()
    if not session:
        logger.warning(f"Output view attempt failed: Session {session_id} not found")
        flash('Session not found.', 'danger')
        return redirect(url_for('employee_bp.dashboard'))
    transaction_folder = session.transaction_folder
    output_file = os.path.join(transaction_folder, 'output', f"{script.lower()}_output.html")
    if script.lower() == 'keyword':
        output_file = os.path.join(transaction_folder, 'output', 'keywordsearch.html')
    if not os.path.exists(output_file):
        logger.warning(f"Output file not found: {output_file}")
        flash('Output file not found.', 'danger')
        return redirect(url_for('employee_bp.dashboard'))
    logger.debug(f"Serving file: {output_file}")
    return send_file(output_file)

@employee_bp.route('/download/<session_id>/<script>')
@login_required
def download_output(session_id, script):
    session = SessionMetadata.query.filter_by(session_id=session_id, username=current_user.email).first()
    if not session:
        logger.warning(f"Download attempt failed: Session {session_id} not found")
        flash('Session not found.', 'danger')
        return redirect(url_for('employee_bp.dashboard'))
    transaction_folder = session.transaction_folder
    output_file = os.path.join(transaction_folder, 'output', f"{script.lower()}_output.html")
    if script.lower() == 'keyword':
        output_file = os.path.join(transaction_folder, 'output', 'keywordsearch.html')
    if not os.path.exists(output_file):
        logger.warning(f"Output file not found: {output_file}")
        flash('Output file not found.', 'danger')
        return redirect(url_for('employee_bp.dashboard'))
    logger.debug(f"Downloading file: {output_file}")
    return send_file(output_file, as_attachment=True)

@employee_bp.route('/email/<session_id>/<script>')
@login_required
def email_output(session_id, script):
    mail = Mail(current_app)
    session = SessionMetadata.query.filter_by(session_id=session_id, username=current_user.email).first()
    if not session:
        logger.warning(f"Email attempt failed: Session {session_id} not found")
        flash('Session not found.', 'danger')
        return redirect(url_for('employee_bp.dashboard'))
    transaction_folder = session.transaction_folder
    output_file = os.path.join(transaction_folder, 'output', f"{script.lower()}_output.html")
    if script.lower() == 'keyword':
        output_file = os.path.join(transaction_folder, 'output', 'keywordsearch.html')
    if not os.path.exists(output_file):
        logger.warning(f"Output file not found: {output_file}")
        flash('Output file not found.', 'danger')
        return redirect(url_for('employee_bp.dashboard'))
    try:
        msg = Message(current_app.config['EMAIL_SUBJECT'],
                      sender=current_app.config['MAIL_DEFAULT_SENDER'],
                      recipients=[current_user.email])
        with open(output_file, 'rb') as f:
            msg.attach(script.lower() + "_output.html", "text/html", f.read())
        mail.send(msg)
        logger.debug(f"Email sent for {script} output to {current_user.email}")
        flash(f'Email sent for {script} output.', 'success')
    except Exception as e:
        logger.error(f"Error sending email for {script}: {e}")
        flash(f'Error sending email: {e}', 'danger')
    return redirect(url_for('employee_bp.dashboard'))

@employee_bp.route('/historical', methods=['GET'])
@login_required
def historical():
    sessions = SessionMetadata.query.filter_by(username=current_user.email).all()
    uploads = []
    for s in sessions:
        folder_basename = os.path.basename(s.transaction_folder)
        uploads.append({
            'session_id': s.session_id,
            'case_number': s.case_number,
            'upload_time': s.upload_timestamp,
            'upload_folder': folder_basename,
            'filename': 'logs.tar'
        })
    logger.debug(f"Rendering historical files page with {len(uploads)} uploads for user {current_user.email}")
    return render_template('historical_files.html', uploads=uploads)

@employee_bp.route('/output_view', methods=['GET'])
@login_required
def output_view():
    session_id = request.args.get('session_id')
    session = SessionMetadata.query.filter_by(session_id=session_id, username=current_user.email).first()
    if not session:
        logger.warning(f"Output view attempt failed: Session {session_id} not found")
        flash('Session not found.', 'danger')
        return redirect(url_for('employee_bp.historical'))
    output_folder = os.path.join(session.transaction_folder, 'output')
    zip_path = os.path.join(session.transaction_folder, 'output.zip')
    try:
        logger.debug(f"Creating zip archive of {output_folder} at {zip_path}")
        subprocess.run(['zip', '-r', zip_path, output_folder], check=True)
    except Exception as e:
        logger.error(f'Error creating zip archive: {str(e)}')
        flash('Error creating zip archive.', 'danger')
        return redirect(url_for('employee_bp.historical'))
    logger.debug(f"Serving zip file: {zip_path}")
    return send_file(zip_path, as_attachment=True)

@employee_bp.route('/logout')
@login_required
def logout():
    from flask import get_flashed_messages
    get_flashed_messages()
    from flask_login import logout_user
    logger.debug(f"User {current_user.email} logged out")
    logout_user()
    return redirect(url_for('auth_bp.login'))