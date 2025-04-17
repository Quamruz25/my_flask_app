# Location: /opt/my_flask_app/app/routes/employee_routes.py
import os
import uuid
import tarfile
import subprocess
import logging
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, current_app
from flask_login import login_required, current_user
from flask_mail import Message
from app.models import User, SessionMetadata
from app import db, mail

employee_bp = Blueprint('employee_bp', __name__, template_folder='templates')
logger = logging.getLogger('app.routes.employee_routes')

# Maximum recursion depth for nested tar extraction
MAX_DEPTH = 10

def extract_tar_file(tar_path, extract_path, depth=0):
    """Recursively extract tar files up to a maximum depth."""
    if depth > MAX_DEPTH:
        logger.error(f"Max recursion depth ({MAX_DEPTH}) exceeded for {tar_path}")
        raise ValueError(f"Max recursion depth ({MAX_DEPTH}) exceeded for {tar_path}")

    try:
        logger.debug(f"Extracting tar file: {tar_path} to {extract_path} (depth {depth})")
        with tarfile.open(tar_path, 'r:*') as tar:
            tar.extractall(path=extract_path)
            logger.debug(f"Extracted {tar_path} to {extract_path}")
            for member in tar.getmembers():
                if member.name.endswith(('.tar', '.tar.gz', '.tgz')):
                    nested_tar_path = os.path.join(extract_path, member.name)
                    logger.debug(f"Processing nested tar file: {nested_tar_path} (depth {depth + 1})")
                    extract_tar_file(nested_tar_path, extract_path, depth + 1)
    except Exception as e:
        logger.error(f"Failed to extract nested tar: {tar_path} - {str(e)}")
        raise

@employee_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def employee_dashboard():
    if current_user.role != 'employee':
        flash('Access denied: Employees only.')
        return redirect(url_for('auth_bp.login'))

    tar_extracted = False
    output_html = None
    chr_output_html = None
    bucket_output_html = None
    keyword_output_html = None

    if request.method == 'POST':
        if 'tar_file' not in request.files:
            flash('No file uploaded.')
            return redirect(url_for('employee_bp.employee_dashboard'))

        file = request.files['tar_file']
        if file.filename == '':
            flash('No file selected.')
            return redirect(url_for('employee_bp.employee_dashboard'))

        # Validate file name
        if not file.filename.endswith(('.tar', '.tar.gz', '.tgz')):
            flash('Invalid file type. Please upload a .tar, .tar.gz, or .tgz file.')
            return redirect(url_for('employee_bp.employee_dashboard'))

        # Get script options
        script_options = request.form.getlist('script_option')
        if not script_options:
            flash('Please select at least one script to run.')
            return redirect(url_for('employee_bp.employee_dashboard'))

        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        username = current_user.email.split('@')[0]
        case_number = request.form.get('case_number', 'unknown')

        # Create directories
        transaction_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], username, case_number, session_id)
        input_folder = os.path.join(transaction_folder, 'input')
        output_folder = os.path.join(transaction_folder, 'output')
        log_folder = os.path.join(transaction_folder, 'log')

        try:
            os.makedirs(transaction_folder, exist_ok=True)
            os.makedirs(input_folder, exist_ok=True)
            os.makedirs(output_folder, exist_ok=True)
            os.makedirs(log_folder, exist_ok=True)
            logger.debug(f"Folders created: transaction={transaction_folder}, input={input_folder}, output={output_folder}, log={log_folder}")
        except Exception as e:
            logger.error(f"Failed to create directories: {str(e)}")
            flash(f"Failed to create directories: {str(e)}")
            return redirect(url_for('employee_bp.employee_dashboard'))

        # Save the uploaded file
        upload_path = os.path.join(transaction_folder, file.filename)
        try:
            file.save(upload_path)
            logger.debug(f"File saved: {upload_path}")
            if not os.path.exists(upload_path):
                logger.error(f"File save failed: {upload_path} does not exist after save")
                flash('Failed to save the uploaded file.')
                return redirect(url_for('employee_bp.employee_dashboard'))
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            flash(f"Error saving file: {str(e)}")
            return redirect(url_for('employee_bp.employee_dashboard'))

        try:
            # Extract the uploaded tar file
            extract_tar_file(upload_path, transaction_folder)
            tar_extracted = True

            # Find tech-support.log
            tech_support_path = None
            for root, _, files in os.walk(transaction_folder):
                if 'tech-support.log' in files:
                    tech_support_path = os.path.join(root, 'tech-support.log')
                    logger.debug(f"Found tech-support.log at: {tech_support_path}")
                    break

            if not tech_support_path:
                flash('tech-support.log not found in the uploaded file.')
                return redirect(url_for('employee_bp.employee_dashboard'))

            # Process scripts based on selected options
            scripts = {
                'ccr': {
                    'cmd': ['python3.8', '/opt/my_flask_app/scripts/CCR/script_ccr.py', input_folder, output_folder],
                    'output': os.path.join(output_folder, 'ccr.html')
                },
                'chr': {
                    'cmd': ['python3.8', '/opt/my_flask_app/scripts/CHR/run_chr.sh', input_folder, output_folder, log_folder],
                    'output': os.path.join(output_folder, 'chr.html')
                },
                'bucket': {
                    'cmd': ['python3.8', '/opt/my_flask_app/scripts/Bucket/script_bucket.py', input_folder, output_folder],
                    'output': os.path.join(output_folder, 'bucket.html')
                },
                'keyword': {
                    'cmd': ['python3.8', '/opt/my_flask_app/scripts/KeyWord/script_keyword.py', transaction_folder, output_folder, upload_path, session_id],
                    'output': os.path.join(output_folder, 'keywordsearch.html')
                }
            }

            for script in script_options:
                if script not in scripts:
                    logger.warning(f"Unknown script option: {script}")
                    continue

                script_info = scripts[script]
                try:
                    # Generate input files for the script
                    if script != 'keyword':  # Keyword script uses the tar file directly
                        input_file = os.path.join(input_folder, f"{script.upper()}_input.txt")
                        with open(tech_support_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        with open(input_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        logger.debug(f"Input file created for {script}: {input_file}")

                    # Run the script
                    result = subprocess.run(script_info['cmd'], capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.debug(f"{script.upper()} script executed successfully: {result.stdout}")
                        if os.path.exists(script_info['output']):
                            if script == 'ccr':
                                output_html = script_info['output']
                            elif script == 'chr':
                                chr_output_html = script_info['output']
                            elif script == 'bucket':
                                bucket_output_html = script_info['output']
                            elif script == 'keyword':
                                keyword_output_html = script_info['output']
                        else:
                            logger.error(f"Output file not generated for {script}: {script_info['output']}")
                            flash(f"Output file not generated for {script.upper()} script.")
                    else:
                        logger.error(f"{script.upper()} script failed: {result.stderr}")
                        flash(f"Error processing {script.upper()} script: {result.stderr}")
                except Exception as e:
                    logger.error(f"{script.upper()} script failed: {str(e)}")
                    flash(f"Error processing {script.upper()} script: {str(e)}")

            # Save session metadata
            session_metadata = SessionMetadata(
                session_id=session_id,
                username=username,
                case_number=case_number,
                transaction_folder=transaction_folder,
                upload_timestamp=datetime.utcnow()
            )
            db.session.add(session_metadata)
            db.session.commit()
            logger.debug(f"Session metadata saved for session: {session_id}")

            flash('File uploaded and processed successfully.')
        except ValueError as ve:
            flash(str(ve))
            return redirect(url_for('employee_bp.employee_dashboard'))
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            flash(f"Error processing file: {str(e)}")
            return redirect(url_for('employee_bp.employee_dashboard'))

    # GET request or after POST: Render the dashboard with results
    return render_template(
        'employee_dashboard.html',
        tar_extracted=tar_extracted,
        output_html=output_html,
        chr_output_html=chr_output_html,
        bucket_output_html=bucket_output_html,
        keyword_output_html=keyword_output_html
    )

@employee_bp.route('/historical')
@login_required
def historical():
    if current_user.role != 'employee':
        flash('Access denied: Employees only.')
        return redirect(url_for('auth_bp.login'))
    
    sessions = SessionMetadata.query.filter_by(username=current_user.email.split('@')[0]).all()
    return render_template('historical.html', sessions=sessions)

@employee_bp.route('/view_output')
@login_required
def view_output():
    if current_user.role != 'employee':
        flash('Access denied: Employees only.')
        return redirect(url_for('auth_bp.login'))

    file_path = request.args.get('file_path')
    if not file_path:
        flash('File path not provided.')
        return redirect(url_for('employee_bp.employee_dashboard'))

    # Security check: Ensure the file is within the user's session directory
    username = current_user.email.split('@')[0]
    if username not in file_path or not file_path.startswith(current_app.config['UPLOAD_FOLDER']):
        flash('Access denied: Invalid file path.')
        return redirect(url_for('employee_bp.employee_dashboard'))

    if not os.path.exists(file_path):
        flash('File not found.')
        return redirect(url_for('employee_bp.employee_dashboard'))

    return send_file(file_path)

@employee_bp.route('/download_output')
@login_required
def download_output():
    if current_user.role != 'employee':
        flash('Access denied: Employees only.')
        return redirect(url_for('auth_bp.login'))

    file_path = request.args.get('file_path')
    if not file_path:
        flash('File path not provided.')
        return redirect(url_for('employee_bp.employee_dashboard'))

    # Security check: Ensure the file is within the user's session directory
    username = current_user.email.split('@')[0]
    if username not in file_path or not file_path.startswith(current_app.config['UPLOAD_FOLDER']):
        flash('Access denied: Invalid file path.')
        return redirect(url_for('employee_bp.employee_dashboard'))

    if not os.path.exists(file_path):
        flash('File not found.')
        return redirect(url_for('employee_bp.employee_dashboard'))

    return send_file(file_path, as_attachment=True)

@employee_bp.route('/email_output')
@login_required
def email_output():
    if current_user.role != 'employee':
        flash('Access denied: Employees only.')
        return redirect(url_for('auth_bp.login'))

    file_path = request.args.get('file_path')
    script = request.args.get('script')

    if not file_path or not script:
        flash('File path or script not provided.')
        return redirect(url_for('employee_bp.employee_dashboard'))

    # Security check: Ensure the file is within the user's session directory
    username = current_user.email.split('@')[0]
    if username not in file_path or not file_path.startswith(current_app.config['UPLOAD_FOLDER']):
        flash('Access denied: Invalid file path.')
        return redirect(url_for('employee_bp.employee_dashboard'))

    if not os.path.exists(file_path):
        flash('File not found.')
        return redirect(url_for('employee_bp.employee_dashboard'))

    try:
        # Send email with the output file as an attachment
        msg = Message(
            subject=f"{script} Report - HPE Aruba Intelligence",
            recipients=[current_user.email],
            bcc=current_app.config['ADMIN_EMAILS'],
            body=f"Dear {current_user.email},\n\nAttached is the {script} report generated by the HPE Aruba Intelligence platform."
        )
        with open(file_path, 'rb') as f:
            msg.attach(
                filename=os.path.basename(file_path),
                content_type='application/octet-stream',
                data=f.read()
            )
        mail.send(msg)
        flash(f'{script} report emailed successfully.')
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        flash(f'Failed to send email: {str(e)}')

    return redirect(url_for('employee_bp.employee_dashboard'))