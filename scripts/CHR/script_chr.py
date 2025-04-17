#!/usr/bin/env python3
# Location: /opt/my_flask_app/scripts/CHR/script_chr.py
"""
script_chr.py
Usage: python3 script_chr.py <input_file> <final_output_html> <overall_log_file>
Driver script for CHR processing. Calls run1.py to generate a modified input and then run2.py to produce the final CHR HTML report.
"""
import sys
import os
import subprocess

def main(input_file, final_output_html, overall_log_file):
    # Define intermediate file in the same directory as final_output_html
    intermediate_file = os.path.join(os.path.dirname(final_output_html), "chr_intermediate.txt")
    run1_log = os.path.join(os.path.dirname(overall_log_file), "chr_run1.log")
    
    # Ensure directories exist
    os.makedirs(os.path.dirname(intermediate_file), exist_ok=True)
    os.makedirs(os.path.dirname(run1_log), exist_ok=True)

    print("Running CHR Step 1 (run1.py)...")
    run1_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run1.py")
    ret1 = subprocess.run(["python3", run1_path, input_file, intermediate_file, run1_log],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if ret1.returncode != 0:
        print("Error: run1.py failed. Check log:", run1_log)
        print("STDERR:", ret1.stderr)
        sys.exit(1)
    
    run2_log = os.path.join(os.path.dirname(overall_log_file), "chr_run2.log")
    run2_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run2.py")
    print("Running CHR Step 2 (run2.py)...")
    ret2 = subprocess.run(["python3", run2_path, intermediate_file, final_output_html, run2_log],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if ret2.returncode != 0:
        print("Error: run2.py failed. Check log:", run2_log)
        print("STDERR:", ret2.stderr)
        sys.exit(1)
    
    print("CHR processing complete.")
    print("Final CHR report available at:", final_output_html)
    print("Overall log available at:", overall_log_file)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 script_chr.py <input_file> <final_output_html> <overall_log_file>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])