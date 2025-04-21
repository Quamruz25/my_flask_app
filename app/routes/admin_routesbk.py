# Location: /opt/my_flask_app/app/routes/admin_routes.py
import logging
import traceback
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, login_required, current_user
from flask_mail import Message
from werkzeug.security import check_password_hash
from app.models import User, SessionMetadata
from app import db, mail
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin_bp', __name__, template_folder='templates')
logger = logging.getLogger('app.routes.admin_routes')

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        logger.debug(f"Admin login attempt for email: {email}")

        user = User.query.filter_by(email=email, role='admin').first()
        if user:
            logger.debug(f"User found: {user.email}, role: {user.role}, enabled: {user.enabled}")
            if not user.enabled:
                logger.debug(f"User {user.email} is disabled")
                flash('Your account is disabled.')
                return redirect(url_for('admin_bp.login'))
            if check_password_hash(user.password_hash, password):
                logger.debug(f"Password match for {user.email}")
                login_success = login_user(user)
                logger.debug(f"login_user result for {user.email}: {login_success}")
                logger.debug(f"Current user after login: {current_user.is_authenticated}")
                return redirect(url_for('admin_bp.admin_dashboard'))
            else:
                logger.debug(f"Password mismatch for {user.email}")
                flash('Invalid email or password.')
        else:
            logger.debug(f"No admin user found with email: {email}")
            flash('Invalid email or password.')
    return render_template('admin_login.html')

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    logger.debug(f"Accessing admin dashboard, current_user: {current_user.email}, role: {current_user.role}")
    if current_user.role != 'admin':
        flash('Access denied: Admins only.')
        return redirect(url_for('auth_bp.login'))
    
    try:
        # Get pending users
        pending_users = User.query.filter_by(enabled=False).all()
        logger.debug(f"Pending users: {len(pending_users)}")
        
        # Total registered users
        total_users = User.query.count()
        logger.debug(f"Total users: {total_users}")
        
        # Get all sessions
        all_sessions = SessionMetadata.query.all()
        logger.debug(f"All sessions: {len(all_sessions)}")
        
        # Session statistics
        # Sessions per day
        sessions_per_day = db.session.query(
            func.date(SessionMetadata.upload_timestamp),
            func.count(SessionMetadata.id)
        ).group_by(func.date(SessionMetadata.upload_timestamp)).all()
        logger.debug(f"Sessions per day: {sessions_per_day}")
        
        # Sessions per week
        sessions_per_week = db.session.query(
            func.yearweek(SessionMetadata.upload_timestamp),
            func.count(SessionMetadata.id)
        ).group_by(func.yearweek(SessionMetadata.upload_timestamp)).all()
        logger.debug(f"Sessions per week: {sessions_per_week}")
        
        # Sessions per month
        sessions_per_month = db.session.query(
            func.date_format(SessionMetadata.upload_timestamp, '%Y-%m'),
            func.count(SessionMetadata.id)
        ).group_by(func.date_format(SessionMetadata.upload_timestamp, '%Y-%m')).all()
        logger.debug(f"Sessions per month: {sessions_per_month}")
        
        # Sessions per year
        sessions_per_year = db.session.query(
            func.year(SessionMetadata.upload_timestamp),
            func.count(SessionMetadata.id)
        ).group_by(func.year(SessionMetadata.upload_timestamp)).all()
        logger.debug(f"Sessions per year: {sessions_per_year}")
        
        return render_template(
            'admin_dashboard.html',
            pending_users=pending_users,
            total_users=total_users,
            all_sessions=all_sessions,
            sessions_per_day=sessions_per_day,
            sessions_per_week=sessions_per_week,
            sessions_per_month=sessions_per_month,
            sessions_per_year=sessions_per_year
        )
    except Exception as e:
        logger.error(f"Error in admin_dashboard: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@admin_bp.route('/enable_user/<int:user_id>', methods=['POST'])
@login_required
def enable_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied: Admins only.')
        return redirect(url_for('auth_bp.login'))

    user = User.query.get_or_404(user_id)
    user.enabled = True
    try:
        db.session.commit()

        # Send approval email with BCC to admins
        msg = Message(
            subject="Account Approved",
            recipients=[user.email],
            bcc=current_app.config['ADMIN_EMAILS'],
            body=f"Dear {user.email},\n\nYour account has been approved by an admin. You can now log in to the HPE Aruba Intelligence platform."
        )
        mail.send(msg)

        flash(f'User {user.email} has been enabled.')
    except Exception as e:
        db.session.rollback()
        flash(f'Error enabling user: {str(e)}')

    return redirect(url_for('admin_bp.admin_dashboard'))

@admin_bp.route('/logout')
@login_required
def logout():
    from flask import get_flashed_messages
    get_flashed_messages()  # Clear flashed messages
    from flask_login import logout_user
    logout_user()
    return redirect(url_for('admin_bp.login'))