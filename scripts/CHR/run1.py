#!/usr/bin/env python3
# Location: /opt/my_flask_app/scripts/CHR/run1.py
"""
run1.py - CHR Step 1
Usage: python3 run1.py <input_file> <modified_input_file> <log_file>
Reads the input file and applies regex-based modifications to add quotes around specific keywords.
"""
import sys
import re
from pathlib import Path
import os

if len(sys.argv) < 4:
    print("Usage: python3 run1.py <input_file> <modified_input_file> <log_file>")
    sys.exit(1)

input_file = sys.argv[1]
modified_input_file = sys.argv[2]
log_file = sys.argv[3]

# Ensure the output directory exists
os.makedirs(os.path.dirname(modified_input_file), exist_ok=True)

# Function to apply changes
def apply_changes(file_path, output_path):
    # Read the input file
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    # Prepare a list to store modified lines
    modified_lines = []
    
    # Define patterns and replacements
    patterns = [
        (r'(version\s+)(\S+)', r'\1"\2"'),
        (r'(controller\s+config\s+)(\S+)', r'\1"\2"'),
        (r'(ip\s+nat\s+pool\s+)(\S+)', r'\1"\2"'),
        (r'(ip\s+access-list\s+mac\s+)(\S+)', r'\1"\2"'),
        (r'(ip\s+access-list\s+eth\s+)(\S+)', r'\1"\2"'),
        (r'(ip\s+access-list\s+geolocation\s+)(\S+)', r'\1"\2"'),
        (r'(ip\s+access-list\s+route\s+)(\S+)', r'\1"\2"'),
        (r'(netdestination\s+)(\S+)', r'\1"\2"'),
        (r'(netexthdr\s+)(\S+)', r'\1"\2"'),
        (r'(time-range\s+periodic\s+)(\S+)', r'\1"\2"'),
        (r'(time-range\s+absolute\s+)(\S+)', r'\1"\2"'),
        (r'(aaa\s+bandwidth-contract\s+)(\S+)(?!")', r'\1"\2"'),
        (r'(access-list\s+session\s+)(\S+)', r'\1"\2"'),
        (r'(netservice\s+)(\S+)(?!")', r'\1"\2"'),
        (r'(\s)(svc-\S+)', r'\1"\2"'),
        (r'(user-role\s+)(\S+)', r'\1"\2"'),
        (r'^[ ]{0,5}(vlan\s+)(\d+)', r'\1"\2"'),  # Updated for vlan, preserving leading zero
        (r'^[ ]{0,5}(vlan-name\s+)(\S+)', r'\1"\2"'),
        (r'(ip\s+nexthop-list\s+)(\S+)', r'\1"\2"'),
        (r'(cp-bandwidth-contract\s+)(\S+)', r'\1"\2"'),
        (r'(auth-server\s+)(\S+)', r'\1"\2"')
    ]
    
    # Loop through each line and apply the patterns
    for line in lines:
        modified_line = line
        
        # Apply the existing patterns
        for pattern, replacement in patterns:
            modified_line = re.sub(pattern, replacement, modified_line)
        
        # If the line starts with "aaa bandwidth-contract", ensure only one pair of quotes is added
        if modified_line.lstrip().startswith("aaa bandwidth-contract"):
            modified_lines.append(modified_line)
            modified_lines.append("!\n")  # Add the "!" on a new line
        # If the line starts with "netservice", ensure only one pair of quotes is added
        elif modified_line.lstrip().startswith("netservice"):
            modified_lines.append(modified_line)
            modified_lines.append("!\n")  # Add the "!" on a new line
        else:
            modified_lines.append(modified_line)
    
    # Save the output to a new file
    with open(output_path, 'w') as output_file:
        output_file.writelines(modified_lines)
    
    print(f"Processed file saved as: {output_path}")

# Process the single input file
apply_changes(input_file, modified_input_file)