# Location: /opt/my_flask_app/app/__init__.py
import os
from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
import logging
from logging.handlers import RotatingFileHandler

# Import configuration from config.py
from config import *

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()

def file_exists(filepath):
    """Custom Jinja filter to check if a file exists."""
    return os.path.exists(filepath)

def create_app():
    app = Flask(__name__)
    
    # Load configurations from config.py
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAIL_SERVER'] = MAIL_SERVER
    app.config['MAIL_PORT'] = MAIL_PORT
    app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
    app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
    app.config['MAIL_USERNAME'] = MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
    app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER
    app.config['ADMIN_EMAILS'] = ADMIN_EMAILS
    app.config['SEVEN_ZIP_CMD'] = SEVEN_ZIP_CMD
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth_bp.login'
    login_manager.session_protection = 'strong'
    mail.init_app(app)
    
    # Configure logging
    file_handler = RotatingFileHandler('/opt/my_flask_app/logs/app.log', maxBytes=10000000, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers = [file_handler, console_handler]  # Replace default handlers
    root_logger.propagate = False

    # Configure app logger
    app_logger = logging.getLogger('app')
    app_logger.setLevel(logging.DEBUG)
    app_logger.handlers = [file_handler, console_handler]
    app_logger.propagate = False

    # Configure Werkzeug logger
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.handlers = [file_handler, console_handler]
    werkzeug_logger.propagate = False

    # Configure auth_routes logger
    auth_logger = logging.getLogger('app.routes.auth_routes')
    auth_logger.setLevel(logging.DEBUG)
    auth_logger.handlers = [file_handler, console_handler]
    auth_logger.propagate = False

    # Configure employee_routes logger
    employee_logger = logging.getLogger('app.routes.employee_routes')
    employee_logger.setLevel(logging.DEBUG)
    employee_logger.handlers = [file_handler, console_handler]
    employee_logger.propagate = False

    # Configure Flask's built-in logger
    app.logger.handlers = [file_handler, console_handler]
    app.logger.setLevel(logging.DEBUG)
    app.logger.propagate = False

    app_logger.debug("Debug logging is enabled.")
    auth_logger.debug("Auth routes logger configured.")
    employee_logger.debug("Employee routes logger configured.")
    
    # Register blueprints
    from app.routes import auth_routes, employee_routes, admin_routes
    app.register_blueprint(auth_routes.auth_bp)
    app.register_blueprint(employee_routes.employee_bp)
    app.register_blueprint(admin_routes.admin_bp, url_prefix='/admin')
    
    # Add custom Jinja filter
    app.jinja_env.filters['exists'] = file_exists
    
    # Add a root route to render index.html
    @app.route('/')
    def root():
        app_logger.debug("Root route accessed, rendering index.html")
        return render_template('index.html')
    
    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    user = User.query.get(int(user_id))
    app_logger = logging.getLogger('app')
    app_logger.debug(f"Loading user with ID {user_id}: {user}")
    return user