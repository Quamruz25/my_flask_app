import os
import uuid
import json
import shutil
import subprocess
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, current_app
from flask_login import login_required, current_user
from app import db
from app.models import User, SessionMetadata
import logging
from werkzeug.utils import secure_filename
import threading
import time

employee_bp = Blueprint('employee_bp', __name__, template_folder='templates')
logger = logging.getLogger('app.routes.employee_routes')

def extract_with_7zip(tar_path, extract_path, depth=0, max_depth=10, processed_files=None, session_id=None):
    """Recursively extract archives using 7zip, up to a specified depth, for specific paths."""
    if processed_files is None:
        processed_files = set()

    if depth > max_depth:
        logger.warning(f"Max extraction depth reached at {tar_path}")
        return

    if tar_path in processed_files:
        logger.debug(f"Skipping already processed archive: {tar_path}")
        return

    if not os.path.exists(tar_path):
        logger.debug(f"Skipping non-existent archive: {tar_path}")
        return

    # Determine if we should recursively extract this file
    should_recurse = False
    # Always extract the root logs.tar or logs.tar.gz
    if os.path.basename(tar_path).startswith('logs.tar'):
        should_recurse = True
    # Extract configs.tar.gz and its nested archives
    elif tar_path.endswith('configs.tar.gz') or 'configs.tar' in tar_path:
        should_recurse = True
    # Extract files under var/log/oslog/memlogs
    elif f"{session_id}/var/log/oslog/memlogs" in tar_path:
        should_recurse = True

    if not should_recurse:
        logger.debug(f"Skipping recursive extraction for {tar_path} (not in configs.tar.gz or memlogs)")
        return

    processed_files.add(tar_path)
    logger.debug(f"Extracting archive: {tar_path} at depth {depth} using 7zip")

    try:
        # Use 7zip to extract the archive
        command = f"7z x {tar_path} -o{extract_path} -y"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Failed to extract {tar_path} with 7zip: {result.stderr}")
            return
        logger.debug(f"Extracted {tar_path} to {extract_path}: {result.stdout}")

        # Log the folder structure after extraction
        extracted_contents = os.listdir(extract_path)
        logger.debug(f"Contents of {extract_path} after extraction: {extracted_contents}")

        # Fix permissions: set ownership to the 'manish' user
        command = f"chown -R manish:manish {extract_path}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Failed to set ownership for {extract_path}: {result.stderr}")
        else:
            logger.debug(f"Set ownership of {extract_path} to manish:manish")
    except Exception as e:
        logger.error(f"Error extracting {tar_path} with 7zip: {str(e)}")
        return

    # Find nested archives, but only process .tar, .tar.gz, .tgz (not plain .gz)
    nested_tar_files = []
    for root, _, files in os.walk(extract_path):
        for file in files:
            if file.endswith(('.tar', '.tar.gz', '.tgz')):
                nested_tar_path = os.path.join(root, file)
                if nested_tar_path not in processed_files:
                    nested_tar_files.append((nested_tar_path, root))
                else:
                    logger.debug(f"Skipping nested file: {nested_tar_path} (already processed)")

    # Process nested archives
    for nested_tar_path, nested_extract_path in nested_tar_files:
        logger.debug(f"Processing nested archive: {nested_tar_path} (depth {depth + 1})")
        extract_with_7zip(nested_tar_path, nested_extract_path, depth + 1, max_depth, processed_files, session_id)

    # After extracting configs.tar.gz or configs.tar, handle the folder structure
    if tar_path.endswith('configs.tar.gz') or 'configs.tar' in tar_path:
        # Find the root transaction folder
        root_transaction_folder = extract_path
        while not os.path.basename(root_transaction_folder) == session_id:
            root_transaction_folder = os.path.dirname(root_transaction_folder)
        config_path = os.path.join(root_transaction_folder, 'config')

        # Look for 'flash' folder
        flash_path = os.path.join(extract_path, 'flash')
        if os.path.exists(flash_path):
            os.makedirs(config_path, exist_ok=True)
            # Move contents of flash to config
            flash_contents = os.listdir(flash_path)
            logger.debug(f"Contents of flash folder {flash_path}: {flash_contents}")
            for item in os.listdir(flash_path):
                src_path = os.path.join(flash_path, item)
                dst_path = os.path.join(config_path, item)
                try:
                    shutil.move(src_path, dst_path)
                    logger.debug(f"Moved {src_path} to {dst_path}")
                except Exception as e:
                    logger.error(f"Failed to move {src_path} to {dst_path}: {str(e)}")
            # Remove the empty flash folder
            try:
                os.rmdir(flash_path)
                logger.debug(f"Removed empty flash folder: {flash_path}")
            except Exception as e:
                logger.warning(f"Failed to remove flash folder {flash_path}: {str(e)}")
        else:
            logger.warning(f"Flash folder not found after extracting {tar_path}")

    # Preserve archives for debugging
    logger.debug(f"Preserving archive: {tar_path} (not removing)")

def run_script_async(command, script_name, output_files, key, output_path, log_file):
    """Run a script asynchronously and update output_files."""
    start_time = time.time()
    try:
        logger.debug(f"Running {script_name} script with command: {command}")
        process = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=900)  # 15-minute timeout
        elapsed_time = time.time() - start_time
        if process.returncode == 0:
            logger.debug(f"{script_name} script executed successfully in {elapsed_time:.2f} seconds: {process.stdout}")
            if process.stderr:
                logger.warning(f"{script_name} script warnings: {process.stderr}")
            output_files[key] = output_path
        else:
            logger.error(f"{script_name} script failed with return code {process.returncode} after {elapsed_time:.2f} seconds: {process.stderr}")
    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        logger.error(f"{script_name} script timed out after 15 minutes (elapsed: {elapsed_time:.2f} seconds)")
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Error running {script_name} script after {elapsed_time:.2f} seconds: {str(e)}")

@employee_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        tar_file = request.files.get('tar_file')
        case_number = request.form.get('case_number', 'default_case')
        script_options = request.form.getlist('script_option')

        if not tar_file:
            flash('No file uploaded.', 'error')
            return redirect(url_for('employee_bp.dashboard'))

        if not (tar_file.filename.endswith('.tar') or tar_file.filename.endswith('.tar.gz')):
            flash('Please upload a .tar or .tar.gz file.', 'error')
            return redirect(url_for('employee_bp.dashboard'))

        # Clean username for folder structure
        username = current_user.email.split('@')[0]  # e.g., 'quamruz'
        session_id = str(uuid.uuid4())
        transaction_folder = os.path.join('/home/manish/flask_uploads', username, case_number, session_id)
        input_folder = os.path.join(transaction_folder, 'input')
        output_folder = os.path.join(transaction_folder, 'output')
        log_folder = os.path.join(transaction_folder, 'log')

        os.makedirs(input_folder, exist_ok=True)
        os.makedirs(output_folder, exist_ok=True)
        os.makedirs(log_folder, exist_ok=True)

        # Clean up the input folder to ensure no stale files
        if os.path.exists(input_folder):
            shutil.rmtree(input_folder)
            logger.debug(f"Cleaned up input folder: {input_folder}")
        os.makedirs(input_folder, exist_ok=True)

        # Save the uploaded file with its original extension
        tar_path = os.path.join(transaction_folder, f"logs{tar_file.filename[-7:] if tar_file.filename.endswith('.tar.gz') else '.tar'}")
        tar_file.save(tar_path)

        # Log session metadata immediately
        session_db = SessionMetadata(
            session_id=session_id,
            username=current_user.email,
            case_number=case_number,
            upload_timestamp=datetime.now(),
            transaction_folder=transaction_folder,
            script_options=','.join(script_options)  # Store selected scripts
        )
        db.session.add(session_db)
        db.session.commit()
        logger.debug(f"Session metadata logged for session {session_id}")

        # Extract archive using 7zip
        try:
            extract_with_7zip(tar_path, transaction_folder, session_id=session_id)
        except Exception as e:
            logger.error(f"Failed to extract archive: {str(e)}")
            flash(f"Failed to extract archive: {str(e)}", 'error')
            return redirect(url_for('employee_bp.dashboard'))

        # Log contents of memlogs folder for debugging
        memlogs_path = os.path.join(transaction_folder, 'var/log/oslog/memlogs')
        if os.path.exists(memlogs_path):
            memlogs_contents = os.listdir(memlogs_path)
            logger.debug(f"Contents of memlogs folder ({memlogs_path}): {memlogs_contents}")
        else:
            logger.debug(f"Memlogs folder does not exist at {memlogs_path}")

        # Log contents of config folder for debugging
        config_path = os.path.join(transaction_folder, 'config')
        if os.path.exists(config_path):
            config_contents = os.listdir(config_path)
            logger.debug(f"Contents of config folder ({config_path}): {config_contents}")
        else:
            logger.debug(f"Config folder does not exist at {config_path}")

        # Prepare inputs for scripts
        output_files = {'CCR': None, 'CHR': None, 'BUCKET': None, 'KEYWORD': None}

        def read_file_safely(file_path):
            """Read a file safely, handling potential encoding issues."""
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError as e:
                logger.warning(f"Failed to decode {file_path} as UTF-8: {str(e)}")
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    return content.decode('utf-8', errors='replace')
                except Exception as e:
                    logger.error(f"Failed to read {file_path} even with error handling: {str(e)}")
                    return None

        # Find tech-support.log for CCR, CHR, and BUCKET scripts
        tech_support_path = None
        for root, _, files in os.walk(transaction_folder):
            if 'tech-support.log' in files:
                tech_support_path = os.path.join(root, 'tech-support.log')
                break

        if tech_support_path:
            logger.debug(f"Found tech-support.log at: {tech_support_path}")
            content = read_file_safely(tech_support_path)
            if content is None:
                logger.error(f"Skipping scripts due to unreadable tech-support.log")
                flash('Could not process tech-support.log due to encoding issues.', 'error')
                return redirect(url_for('employee_bp.dashboard'))

            lines = content.splitlines()
            # Log the first 20 lines of tech-support.log to verify format
            logger.debug(f"First 20 lines of tech-support.log:\n{chr(10).join(lines[:20])}")
            # Search for the exact markers
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if 'show running-config' in line_lower or 'show running config' in line_lower:
                    logger.debug(f"Exact match for 'show running-config' at line {i}: {line}")
                if 'show vrrp stats all' in line_lower:
                    logger.debug(f"Exact match for 'show vrrp stats all' at line {i}: {line}")
                if 'show ap active' in line_lower:
                    logger.debug(f"Exact match for 'show ap active' at line {i}: {line}")
        else:
            logger.error(f"tech-support.log not found in {transaction_folder}")
            flash('tech-support.log not found.', 'error')
            return redirect(url_for('employee_bp.dashboard'))

        # CCR Script: Extract specific blocks
        if 'ccr' in script_options:
            ccr_content = []
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                line_lower = line.lower()
                # Match variations of "show running-config"
                if 'show running-config' in line_lower or 'show running config' in line_lower:
                    block = [line]
                    logger.debug(f"Found 'show running-config' at line {i}: {line}")
                    i += 1
                    while i < len(lines):
                        next_line = lines[i].strip()
                        next_line_lower = next_line.lower()
                        block.append(next_line)
                        if next_line_lower == "end":
                            logger.debug(f"Found 'end' at line {i}")
                            break
                        i += 1
                    ccr_content.append("\n".join(block))
                # Match "show vrrp stats all"
                elif 'show vrrp stats all' in line_lower:
                    block = [line]
                    logger.debug(f"Found 'show vrrp stats all' at line {i}")
                    i += 1
                    while i < len(lines):
                        next_line = lines[i].strip()
                        next_line_lower = next_line.lower()
                        if next_line_lower.startswith("show"):
                            logger.debug(f"Found next 'show' command at line {i}: {next_line}")
                            break
                        block.append(next_line)
                        i += 1
                    ccr_content.append("\n".join(block))
                # Match "show ap active"
                elif 'show ap active' in line_lower:
                    block = [line]
                    logger.debug(f"Found 'show ap active' at line {i}")
                    i += 1
                    while i < len(lines):
                        next_line = lines[i].strip()
                        next_line_lower = next_line.lower()
                        if next_line_lower.startswith("show"):
                            logger.debug(f"Found next 'show' command at line {i}: {next_line}")
                            break
                        block.append(next_line)
                        i += 1
                    ccr_content.append("\n".join(block))
                i += 1

            ccr_input_path = os.path.join(input_folder, 'CCR_input.txt')
            with open(ccr_input_path, 'w', encoding='utf-8') as f:
                if ccr_content:
                    f.write("\n\n".join(ccr_content))
                    logger.debug(f"Generated CCR input with {len(ccr_content)} blocks")
                else:
                    f.write("No relevant blocks found for CCR.")
                    logger.warning(f"No relevant blocks found for CCR in tech-support.log")
                    flash('No relevant blocks found for CCR in tech-support.log.', 'warning')
            logger.debug(f"Input file created for CCR: {ccr_input_path}")

        # CHR Script: Extract only "show running-config" block
        if 'chr' in script_options:
            chr_content = []
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                line_lower = line.lower()
                if 'show running-config' in line_lower or 'show running config' in line_lower:
                    block = [line]
                    logger.debug(f"Found 'show running-config' for CHR at line {i}: {line}")
                    i += 1
                    while i < len(lines):
                        next_line = lines[i].strip()
                        next_line_lower = next_line.lower()
                        block.append(next_line)
                        if next_line_lower == "end":
                            logger.debug(f"Found 'end' for CHR at line {i}")
                            break
                        i += 1
                    chr_content.append("\n".join(block))
                    break  # Only need the first occurrence
                i += 1

            chr_input_path = os.path.join(input_folder, 'CHR_input.txt')
            with open(chr_input_path, 'w', encoding='utf-8') as f:
                if chr_content:
                    f.write(chr_content[0])
                    logger.debug(f"Generated CHR input with show running-config block")
                else:
                    f.write("No show running-config block found for CHR.")
                    logger.warning(f"No show running-config block found for CHR in tech-support.log")
                    flash('No show running-config block found for CHR in tech-support.log.', 'warning')
            logger.debug(f"Input file created for CHR: {chr_input_path}")

        # BUCKET Script: Use the complete tech-support.log
        if 'bucket' in script_options:
            bucket_input_path = os.path.join(input_folder, 'bucket_input.txt')
            with open(bucket_input_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.debug(f"Generated Bucket input length: {len(content)} characters")
            logger.debug(f"Input file created for BUCKET: {bucket_input_path}")

        # KEYWORD Script: Scan specific directories
        if 'keyword' in script_options:
            keyword_input = []
            target_dirs = [
                os.path.join(transaction_folder, 'flash'),
                os.path.join(transaction_folder, 'mswitch'),
                os.path.join(transaction_folder, 'var'),
                os.path.join(transaction_folder, 'config')
            ]
            try:
                for target_dir in target_dirs:
                    if not os.path.exists(target_dir):
                        logger.debug(f"Directory {target_dir} does not exist, skipping for KEYWORD script")
                        continue
                    logger.debug(f"Scanning directory for KEYWORD: {target_dir}")
                    for root, dirs, files in os.walk(target_dir):
                        logger.debug(f"Walking directory: {root}, dirs: {dirs}, files: {files}")
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                if os.path.isfile(file_path) and not file.endswith(('.tar', '.tar.gz', '.tgz', '.gz')):
                                    keyword_input.append(file_path)
                                    logger.debug(f"Added file to keyword_input: {file_path}")
                            except Exception as e:
                                logger.error(f"Error accessing file {file_path} for KEYWORD script: {str(e)}")
                                continue
                # Write JSON atomically and validate
                keyword_input_path = os.path.join(input_folder, 'keyword_input.json')
                temp_keyword_path = keyword_input_path + '.tmp'
                with open(temp_keyword_path, 'w', encoding='utf-8') as f:
                    json.dump(keyword_input, f, indent=2)
                os.rename(temp_keyword_path, keyword_input_path)
                # Validate JSON
                with open(keyword_input_path, 'r', encoding='utf-8') as f:
                    json.load(f)  # This will raise an error if JSON is invalid
                logger.debug(f"Generated Keyword input dataset with {len(keyword_input)} files")
                logger.debug(f"Input file created for KEYWORD: {keyword_input_path}")
            except json.JSONDecodeError as e:
                logger.error(f"Generated keyword_input.json is invalid: {str(e)}")
                flash(f"KEYWORD input file is invalid JSON: {str(e)}", 'error')
            except Exception as e:
                logger.error(f"Failed to generate keyword_input.json: {str(e)}")
                flash(f"Failed to generate KEYWORD input file: {str(e)}", 'error')

        # Redirect to processing page with session details
        return redirect(url_for('employee_bp.process_scripts', session_id=session_id, script_options=','.join(script_options)))

    # GET request: Render the dashboard
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
    return render_template('employee_dashboard.html', tar_extracted=False, sessions=sessions)

@employee_bp.route('/process_scripts/<session_id>/<script_options>')
@login_required
def process_scripts(session_id, script_options):
    script_options = script_options.split(',')
    session = SessionMetadata.query.filter_by(session_id=session_id, username=current_user.email).first()
    if not session:
        flash('Session not found.', 'error')
        return redirect(url_for('employee_bp.dashboard'))

    transaction_folder = session.transaction_folder
    input_folder = os.path.join(transaction_folder, 'input')
    output_folder = os.path.join(transaction_folder, 'output')
    log_folder = os.path.join(transaction_folder, 'log')
    log_file = os.path.join(log_folder, f"{session_id}.log")

    output_files = {'CCR': None, 'CHR': None, 'BUCKET': None, 'KEYWORD': None}
    threads = []

    # CCR Script
    if 'ccr' in script_options:
        ccr_input_path = os.path.join(input_folder, 'CCR_input.txt')
        if os.path.exists(ccr_input_path):
            ccr_output_path = os.path.join(output_folder, 'ccr_output.html')
            command = f"python3.8 /opt/my_flask_app/scripts/CCR/Script-with-Default-Profile.py {ccr_input_path} {ccr_output_path} {log_file}"
            thread = threading.Thread(target=run_script_async, args=(command, "CCR", output_files, 'CCR', ccr_output_path, log_file))
            threads.append(thread)
            thread.start()
        else:
            logger.warning(f"CCR input file not found: {ccr_input_path}, skipping CCR script")
            flash('CCR script skipped due to missing input file.', 'warning')

    # CHR Script
    if 'chr' in script_options:
        chr_input_path = os.path.join(input_folder, 'CHR_input.txt')
        if os.path.exists(chr_input_path):
            chr_output_path = os.path.join(output_folder, 'chr_output.html')
            command = f"python3.8 /opt/my_flask_app/scripts/CHR/script_chr.py {chr_input_path} {chr_output_path} {log_file}"
            thread = threading.Thread(target=run_script_async, args=(command, "CHR", output_files, 'CHR', chr_output_path, log_file))
            threads.append(thread)
            thread.start()
        else:
            logger.warning(f"CHR input file not found: {chr_input_path}, skipping CHR script")
            flash('CHR script skipped due to missing input file.', 'warning')

    # BUCKET Script
    if 'bucket' in script_options:
        bucket_input_path = os.path.join(input_folder, 'bucket_input.txt')
        if os.path.exists(bucket_input_path):
            bucket_output_path = os.path.join(output_folder, 'bucket_output.html')
            command = f"python3.8 /opt/my_flask_app/scripts/Bucket/script_bucket.py {bucket_input_path} {bucket_output_path} {log_file}"
            thread = threading.Thread(target=run_script_async, args=(command, "BUCKET", output_files, 'BUCKET', bucket_output_path, log_file))
            threads.append(thread)
            thread.start()
        else:
            logger.warning(f"BUCKET input file not found: {bucket_input_path}, skipping BUCKET script")
            flash('BUCKET script skipped due to missing input file.', 'warning')

    # KEYWORD Script
    if 'keyword' in script_options:
        keyword_input_path = os.path.join(input_folder, 'keyword_input.json')
        if os.path.exists(keyword_input_path):
            keyword_output_path = os.path.join(output_folder, 'keywordsearch.html')
            command = f"python3.8 /opt/my_flask_app/scripts/KeyWord/script_keyword.py {input_folder} {output_folder} {log_file} {session_id}"
            thread = threading.Thread(target=run_script_async, args=(command, "KEYWORD", output_files, 'KEYWORD', keyword_output_path, log_file))
            threads.append(thread)
            thread.start()
        else:
            logger.warning(f"KEYWORD input file not found: {keyword_input_path}, skipping KEYWORD script")
            flash('KEYWORD script skipped due to missing input file.', 'warning')

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # If only KEYWORD was selected and it succeeded, redirect to the output
    if script_options == ['keyword'] and output_files['KEYWORD']:
        return redirect(url_for('employee_bp.serve_output', session_id=session_id, filename='keywordsearch.html'))

    # Otherwise, render the dashboard with results
    return render_template('employee_dashboard.html', tar_extracted=True, output_files=output_files, session_id=session_id, script_options=script_options)

@employee_bp.route('/output/<session_id>/<filename>')
@login_required
def serve_output(session_id, filename):
    session = SessionMetadata.query.filter_by(session_id=session_id, username=current_user.email).first()
    if not session:
        flash('Session not found.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    file_path = os.path.join(session.transaction_folder, 'output', secure_filename(filename))
    if not os.path.exists(file_path):
        flash('File not found.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))

@employee_bp.route('/static/<session_id>/<script>')
@login_required
def serve_static(session_id, script):
    session = SessionMetadata.query.filter_by(session_id=session_id, username=current_user.email).first()
    if not session:
        flash('Session not found.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    filename_map = {
        'ccr': 'ccr_output.html',
        'chr': 'chr_output.html',
        'bucket': 'bucket_output.html',
        'keyword': 'keywordsearch.html'
    }
    filename = filename_map.get(script)
    if not filename:
        flash('Invalid script type.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    file_path = os.path.join(session.transaction_folder, 'output', filename)
    if not os.path.exists(file_path):
        flash('File not found.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    return send_from_directory(os.path.dirname(file_path), filename)

@employee_bp.route('/download/<session_id>/<script>')
@login_required
def download_output(session_id, script):
    session = SessionMetadata.query.filter_by(session_id=session_id, username=current_user.email).first()
    if not session:
        flash('Session not found.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    filename_map = {
        'ccr': 'ccr_output.html',
        'chr': 'chr_output.html',
        'bucket': 'bucket_output.html',
        'keyword': 'keywordsearch.html'
    }
    filename = filename_map.get(script)
    if not filename:
        flash('Invalid script type.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    file_path = os.path.join(session.transaction_folder, 'output', filename)
    if not os.path.exists(file_path):
        flash('File not found.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    return send_from_directory(os.path.dirname(file_path), filename, as_attachment=True)

@employee_bp.route('/email/<session_id>/<script>')
@login_required
def email_output(session_id, script):
    session = SessionMetadata.query.filter_by(session_id=session_id, username=current_user.email).first()
    if not session:
        flash('Session not found.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    filename_map = {
        'ccr': 'ccr_output.html',
        'chr': 'chr_output.html',
        'bucket': 'bucket_output.html',
        'keyword': 'keywordsearch.html'
    }
    filename = filename_map.get(script)
    if not filename:
        flash('Invalid script type.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    file_path = os.path.join(session.transaction_folder, 'output', filename)
    if not os.path.exists(file_path):
        flash('File not found.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    from flask_mail import Message
    from app import mail
    msg = Message(
        subject=f"Script Output: {script.upper()} for Session {session_id}",
        recipients=[current_user.email],
        body=f"Attached is the output file for the {script.upper()} script from session {session_id}."
    )
    with open(file_path, 'rb') as f:
        msg.attach(filename, 'text/html', f.read())
    try:
        mail.send(msg)
        flash(f"Output file for {script.upper()} has been emailed to {current_user.email}.", 'success')
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        flash(f"Failed to send email: {str(e)}", 'error')
    return redirect(url_for('employee_bp.dashboard'))

@employee_bp.route('/output_view/<session_id>')
@login_required
def output_view(session_id):
    session = SessionMetadata.query.filter_by(session_id=session_id, username=current_user.email).first()
    if not session:
        flash('Session not found.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    output_folder = os.path.join(session.transaction_folder, 'output')
    if not os.path.exists(output_folder):
        flash('Output folder not found.', 'error')
        return redirect(url_for('employee_bp.dashboard'))
    zip_path = os.path.join(session.transaction_folder, f"output_{session_id}.zip")
    shutil.make_archive(os.path.splitext(zip_path)[0], 'zip', output_folder)
    return send_from_directory(os.path.dirname(zip_path), os.path.basename(zip_path), as_attachment=True)

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

@employee_bp.route('/logout')
@login_required
def logout():
    from flask_login import logout_user
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth_bp.login'))