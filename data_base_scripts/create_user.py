#!/usr/bin/env python3.6
# /opt/my_flask_app/create_employee_user.py
# This script creates a non-admin (employee) user with embedded details.

from app import create_app
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash

# Embedded user details:
EMPLOYEE_EMAIL = "manish@hpe.com"
EMPLOYEE_PASSWORD = "Aruba@123"  # Change this to a secure password

app = create_app()
with app.app_context():
    existing_user = User.query.filter_by(email=EMPLOYEE_EMAIL).first()
    if existing_user:
        print(f"User with email {EMPLOYEE_EMAIL} already exists.")
    else:
        new_user = User(
            email=EMPLOYEE_EMAIL,
            password_hash=generate_password_hash(EMPLOYEE_PASSWORD),
            role="employee",   # Non-admin role
            enabled=True       # Enabled so the user can log in immediately
        )
        db.session.add(new_user)
        db.session.commit()
        print(f"Employee user {EMPLOYEE_EMAIL} created successfully!")
