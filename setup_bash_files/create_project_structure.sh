#!/usr/bin/env bash
#
# create_project_structure.sh
# Creates a basic Flask project folder structure with empty files.
# Adjust variables and file names as needed.

# Set your desired project directory:
APP_DIR="/opt/my_flask_app"

echo "Creating project structure under $APP_DIR..."

# 1. Create main directory
sudo mkdir -p "$APP_DIR"
# Optionally, change ownership to the current user (replace 'manish:manish' if needed):
sudo chown manish:manish "$APP_DIR"

# 2. Create subfolders
mkdir -p "$APP_DIR/app"
mkdir -p "$APP_DIR/app/routes"
mkdir -p "$APP_DIR/app/templates"
mkdir -p "$APP_DIR/app/static/css"
mkdir -p "$APP_DIR/app/static/images"
mkdir -p "$APP_DIR/app/config"
mkdir -p "$APP_DIR/scripts/CCR"
mkdir -p "$APP_DIR/scripts/CHR"
mkdir -p "$APP_DIR/scripts/KeyWord"
mkdir -p "$APP_DIR/scripts/Bucket"

# 3. Create empty Python files
touch "$APP_DIR/app/__init__.py"
touch "$APP_DIR/app/models.py"
touch "$APP_DIR/app/extensions.py"

touch "$APP_DIR/app/routes/auth_routes.py"
touch "$APP_DIR/app/routes/admin_routes.py"
touch "$APP_DIR/app/routes/employee_routes.py"

# 4. Create empty template files
touch "$APP_DIR/app/templates/base.html"
touch "$APP_DIR/app/templates/index.html"
touch "$APP_DIR/app/templates/login.html"
touch "$APP_DIR/app/templates/register.html"
touch "$APP_DIR/app/templates/employee_dashboard.html"
touch "$APP_DIR/app/templates/admin_dashboard.html"
touch "$APP_DIR/app/templates/forgot_password.html"
touch "$APP_DIR/app/templates/reset_password.html"

# 5. Create empty static files
touch "$APP_DIR/app/static/css/main.css"
# (Optionally) place a placeholder logo image here if you like:
# cp /path/to/logo.png "$APP_DIR/app/static/images/logo.png"

# 6. Create a config or JSON file if needed
touch "$APP_DIR/app/config/scripts_config.json"

# 7. Create the main run file
touch "$APP_DIR/run.py"

# 8. Create a requirements file
touch "$APP_DIR/requirements.txt"

# 9. Create placeholder script files (optional)
touch "$APP_DIR/scripts/CCR/Script-with-Default-Profile.py"
touch "$APP_DIR/scripts/CCR/Script-Skip-Default-Profile.py"
touch "$APP_DIR/scripts/CHR/script_chr.py"
touch "$APP_DIR/scripts/KeyWord/script_keyword.py"
touch "$APP_DIR/scripts/Bucket/script_bucket.py"

echo "Project structure created under $APP_DIR."
echo "You can now edit files in $APP_DIR to build your Flask app."
