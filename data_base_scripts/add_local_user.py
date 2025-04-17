# Location: /opt/my_flask_app/add_user.py
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User

# Create the Flask app
app = create_app()

def add_user():
    with app.app_context():
        try:
            # Prompt for user input
            email = input("Enter email: ").strip()
            password = input("Enter password: ").strip()
            role = input("Enter role (admin/employee): ").strip().lower()

            # Validate role
            if role not in ['admin', 'employee']:
                print("Error: Role must be 'admin' or 'employee'.")
                sys.exit(1)

            # Validate email (basic check)
            if not email or '@' not in email:
                print("Error: Invalid email address.")
                sys.exit(1)

            # Validate password
            if not password:
                print("Error: Password cannot be empty.")
                sys.exit(1)

            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                print(f"Error: User with email {email} already exists.")
                sys.exit(1)

            # Hash the password
            password_hash = generate_password_hash(password)

            # Create new user
            new_user = User(
                email=email,
                password_hash=password_hash,
                role=role,
                enabled=(role == 'admin'),  # Enable admin users by default, employees need approval
                created_at=datetime.utcnow()
            )

            # Add to database
            db.session.add(new_user)
            db.session.commit()

            print(f"User {email} added successfully with role {role}.")

        except Exception as e:
            print(f"Error adding user: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    add_user()