#!/usr/bin/env python3.6
# /opt/my_flask_app/create_admin.py
from app import create_app
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    # Adjust email and password as desired:
    admin_email = "superbot@hpe.com"
    admin_password = "Aruba@123"
    
    if User.query.filter_by(email=admin_email).first():
        print("Admin user already exists.")
    else:
        admin = User(
            email=admin_email,
            password_hash=generate_password_hash(admin_password),
            role="admin",
            enabled=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created!")
