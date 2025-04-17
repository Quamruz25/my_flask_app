#!/usr/bin/env bash
#
# auto_setup.sh
# Automates environment setup for a Flask app on Ubuntu.
#
# Usage:
#   1) chmod +x auto_setup.sh
#   2) sudo ./auto_setup.sh

# -----------------------------
# 0. Configuration Variables
# -----------------------------
MYSQL_ROOT_PASSWORD="whopee"
MYSQL_APP_DB="my_flask_db"
MYSQL_APP_USER="flask_user"
MYSQL_APP_PASS="whopee"    # or a different password for the app user
APP_DIR="/opt/my_flask_app"
PYTHON_VERSION="python3"   # or python3.8, etc.
# If you have a requirements.txt, you can specify its location:
REQUIREMENTS_FILE="$APP_DIR/requirements.txt"

# -----------------------------
# 1. Update and Install System Packages
# -----------------------------
echo "Updating system packages..."
apt-get update -y
apt-get upgrade -y

echo "Installing required packages..."
apt-get install -y $PYTHON_VERSION ${PYTHON_VERSION}-pip p7zip-full debconf-utils

# -----------------------------
# 2. Configure and Install MySQL (Non-Interactive)
# -----------------------------
echo "Setting MySQL root password non-interactively..."
debconf-set-selections <<< "mysql-server mysql-server/root_password password $MYSQL_ROOT_PASSWORD"
debconf-set-selections <<< "mysql-server mysql-server/root_password_again password $MYSQL_ROOT_PASSWORD"

echo "Installing MySQL server..."
apt-get install -y mysql-server

# Make sure MySQL is running
systemctl enable mysql
systemctl start mysql

# -----------------------------
# 3. Secure MySQL and Create DB/User
# -----------------------------
echo "Securing and configuring MySQL..."

# (Optionally) run mysql_secure_installation equivalent:
# You can also run mysql_secure_installation commands in expect, 
# but for brevity, we'll skip those interactive prompts.

# Create a script to set up DB and user
SQL_SCRIPT="/tmp/mysql_setup.sql"
cat <<EOF > $SQL_SCRIPT
-- Set root password again in case it's needed
ALTER USER 'root'@'localhost' IDENTIFIED BY '$MYSQL_ROOT_PASSWORD';

-- Create the application database
CREATE DATABASE IF NOT EXISTS $MYSQL_APP_DB;

-- Create a dedicated user and grant privileges
CREATE USER IF NOT EXISTS '$MYSQL_APP_USER'@'localhost' IDENTIFIED BY '$MYSQL_APP_PASS';
GRANT ALL PRIVILEGES ON $MYSQL_APP_DB.* TO '$MYSQL_APP_USER'@'localhost';
FLUSH PRIVILEGES;
EOF

echo "Running MySQL setup script..."
mysql -u root -p"$MYSQL_ROOT_PASSWORD" < $SQL_SCRIPT
rm -f $SQL_SCRIPT

# -----------------------------
# 4. Create Project Directory
# -----------------------------
echo "Creating Flask project directory at $APP_DIR..."
mkdir -p $APP_DIR
chown $SUDO_USER:$SUDO_USER $APP_DIR 2>/dev/null || true

# (Optional) Create basic structure:
mkdir -p $APP_DIR/app/routes
mkdir -p $APP_DIR/app/templates
mkdir -p $APP_DIR/app/static/css
mkdir -p $APP_DIR/app/static/images
mkdir -p $APP_DIR/scripts

touch $APP_DIR/app/__init__.py
touch $APP_DIR/app/routes/auth_routes.py
touch $APP_DIR/app/routes/admin_routes.py
touch $APP_DIR/app/routes/employee_routes.py
touch $APP_DIR/app/models.py
touch $APP_DIR/app/extensions.py
touch $APP_DIR/run.py
touch $APP_DIR/requirements.txt

# -----------------------------
# 5. Install Python Dependencies
# -----------------------------
if [ -f "$REQUIREMENTS_FILE" ] && [ -s "$REQUIREMENTS_FILE" ]; then
  echo "Installing Python dependencies from $REQUIREMENTS_FILE..."
  pip3 install -r "$REQUIREMENTS_FILE"
else
  echo "No requirements.txt found or it's empty. Skipping pip install."
fi

# -----------------------------
# Done!
# -----------------------------
echo "All done! Summary:"
echo " - MySQL root password: $MYSQL_ROOT_PASSWORD"
echo " - New database: $MYSQL_APP_DB"
echo " - New MySQL user: $MYSQL_APP_USER"
echo " - MySQL user password: $MYSQL_APP_PASS"
echo " - Project directory created at: $APP_DIR"
echo ""
echo "Next steps:"
echo " 1) Place or clone your Flask app code into $APP_DIR"
echo " 2) Adjust DB credentials in your Flask config to:"
echo "      mysql+pymysql://$MYSQL_APP_USER:$MYSQL_APP_PASS@localhost/$MYSQL_APP_DB"
echo " 3) python3 $APP_DIR/run.py --host=0.0.0.0 --port=5000"
