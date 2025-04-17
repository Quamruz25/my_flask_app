import subprocess
import os

# Define the transaction folder
transaction_folder = "/home/manish/flask_uploads/quamruz/aruba1234/2b33af00-89ee-4453-8814-8097d47b148a"

# Define paths for input, output, and log files
input_file = os.path.join(transaction_folder, "input", "CCR_input.txt")
output_folder = os.path.join(transaction_folder, "output")
log_folder = os.path.join(transaction_folder, "log")
output_file = os.path.join(output_folder, "CCR_output.html")
log_file = os.path.join(log_folder, "CCR_script.log")

# Create output and log folders if they don’t exist
os.makedirs(output_folder, exist_ok=True)
os.makedirs(log_folder, exist_ok=True)

# Define the script path
script_path = "/opt/my_flask_app/scripts/CCR/Script-with-Default-Profile.py"

# Run the script with all required arguments
try:
    result = subprocess.run(
        ['/opt/my_flask_app/.venv/bin/python', script_path, input_file, output_file, log_file],
        cwd=transaction_folder,
        stdout=subprocess.PIPE,  # Capture standard output
        stderr=subprocess.PIPE,  # Capture standard error
        universal_newlines=True,  # Return output as strings (compatible with Python 3.4+)
        check=True  # Raise an exception if the script returns a non-zero exit code
    )
    print("Script executed successfully.")
    print("Standard Output:\n", result.stdout)
    print("Standard Error:\n", result.stderr)
except subprocess.CalledProcessError as e:
    print("Script failed with error:")
    print("Return Code:", e.returncode)
    print("Standard Output:\n", e.stdout)
    print("Standard Error:\n", e.stderr)
except Exception as e:
    print("An unexpected error occurred:", str(e))

# Verify the output and log files
if os.path.exists(output_file):
    print(f"Output file created successfully at: {output_file}")
else:
    print(f"Output file was not created at: {output_file}")

if os.path.exists(log_file):
    print(f"Log file created successfully at: {log_file}")
else:
    print(f"Log file was not created at: {log_file}")