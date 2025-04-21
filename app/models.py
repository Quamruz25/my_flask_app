# Location: /opt/my_flask_app/app/models.py
from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'employee'
    enabled = db.Column(db.Integer, default=0, nullable=False)  # 0: Pending, 1: Approved, 3: Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<User {self.email}>'

    # Flask-Login required methods
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.enabled == 1

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

class SessionMetadata(db.Model):
    __tablename__ = 'session_metadata'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), nullable=False, unique=True)
    username = db.Column(db.String(120), nullable=False)
    case_number = db.Column(db.String(50), nullable=False)
    transaction_folder = db.Column(db.String(255), nullable=False)
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<SessionMetadata {self.session_id}>'