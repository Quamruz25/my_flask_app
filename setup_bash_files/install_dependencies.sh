#!/usr/bin/env bash
#
# install_dependencies.sh
# Updates Ubuntu, installs Python & pip, creates a default requirements.txt if missing, and installs dependencies.
# Last updated: 2025-03-28

APP_DIR="/opt/my_flask_app"
REQUIREMENTS_FILE="$APP_DIR/requirements.txt"

echo "------------------------------"
echo "1. Updating system packages..."
echo "------------------------------"
apt-get update -y

echo "------------------------------"
echo "2. Installing Python3 & pip3..."
echo "------------------------------"
apt-get install -y python3 python3-pip

echo "------------------------------"
echo "3. Ensuring $APP_DIR exists..."
echo "------------------------------"
if [ ! -d "$APP_DIR" ]; then
  echo "Error: $APP_DIR does not exist. Please create your folder structure first."
  exit 1
fi

echo "------------------------------"
echo "4. Checking for $REQUIREMENTS_FILE..."
echo "------------------------------"
if [ ! -f "$REQUIREMENTS_FILE" ]; then
  echo "No requirements.txt found. Creating a default one..."
  cat <<EOF > "$REQUIREMENTS_FILE"
# Default Python dependencies for a basic Flask project:
Flask==2.2.3
Flask-Login==0.6.2
SQLAlchemy==1.4.46
PyMySQL==1.1.0
Flask-Mail==0.9.1
Flask-Migrate==4.0.4
EOF
  echo "Default requirements.txt created at $REQUIREMENTS_FILE"
else
  echo "Found existing $REQUIREMENTS_FILE. Installing from it."
fi

echo "------------------------------"
echo "5. Installing Python packages..."
echo "------------------------------"
pip3 install --upgrade pip
pip3 install -r "$REQUIREMENTS_FILE"

echo "------------------------------"
echo "Installation Complete!"
echo "------------------------------"
echo "Configure your Flask config (in config.py) to use your external SMTP relay."
echo "Then run your app with: python3 $APP_DIR/run.py --host=0.0.0.0 --port=5000"
