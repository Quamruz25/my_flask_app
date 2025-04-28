# Location: /opt/my_flask_app/app/routes/auth_routes.py
import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, get_flashed_messages, current_app
from flask_login import login_user, logout_user, login_required
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db, mail

auth_bp = Blueprint('auth_bp', __name__, template_folder='templates')
logger = logging.getLogger('app.routes.auth_routes')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        logger.debug(f"Registration attempt for email: {email}")

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already registered.')
            return redirect(url_for('auth_bp.register'))

        # Hash the password explicitly with pbkdf2:sha256
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')

        # Create new user (role is always 'employee')
        new_user = User(
            email=email,
            password_hash=password_hash,
            role='employee',  # Hardcode role to employee
            enabled=False,  # Employees need admin approval
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            logger.debug(f"User {email} registered successfully in database")

            # Send confirmation email with BCC to admins
            msg = Message(
                subject="Registration Successful – HPE Aruba Intelligence (HAI)",
                recipients=[email],
                bcc=current_app.config['ADMIN_EMAILS'],
                body=f"Thank you for registering with HPE Aruba Intelligence (HAI), {email}!\n\nYour account has been created as an employee. Please wait for admin review and approval before you can log in."
            )
            try:
                logger.debug(f"Sending registration email to {email}, BCC: {current_app.config['ADMIN_EMAILS']}")
                mail.send(msg)
                logger.debug(f"Registration email sent to {email}")
            except Exception as email_error:
                logger.error(f"Failed to send registration email to {email}: {str(email_error)}")
                flash('Registration successful, but failed to send confirmation email. Please contact support.')

            flash('Registration successful! Awaiting admin approval.')
            return redirect(url_for('auth_bp.login'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration failed for {email}: {str(e)}")
            flash(f'Registration failed: {str(e)}')
            return redirect(url_for('auth_bp.register'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        logger.debug(f"Login attempt for email: {email}")

        user = User.query.filter_by(email=email).first()
        if user:
            logger.debug(f"User found: {user.email}, role: {user.role}, enabled: {user.enabled}")
            if not user.enabled:
                logger.debug(f"User {user.email} is disabled")
                flash('Your account is pending admin approval.')
                return redirect(url_for('auth_bp.login'))
            if check_password_hash(user.password_hash, password):
                logger.debug(f"Password match for {user.email}")
                login_user(user)
                if user.role == 'admin':
                    return redirect(url_for('admin_bp.admin_dashboard'))
                else:
                    return redirect(url_for('employee_bp.dashboard'))
            else:
                logger.debug(f"Password mismatch for {user.email}")
                flash('Invalid password.')
        else:
            logger.debug(f"No user found with email: {email}")
            flash('Email not found.')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    # Consume flashed messages to clear them
    get_flashed_messages()
    logout_user()
    return redirect(url_for('auth_bp.login'))