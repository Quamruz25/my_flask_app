import subprocess
import os
 
transaction_folder = "/home/manish/flask_uploads/quamruz/aruba1234/2b33af00-89ee-4453-8814-8097d47b148a"
script_path = "/opt/my_flask_app/scripts/CCR/Script-with-Default-Profile.py"  # Replace with actual script location
input_file = os.path.join(transaction_folder, "input", "CCR_input.txt")
 
subprocess.run(['python3.6', script_path, input_file], cwd=transaction_folder)