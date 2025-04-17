#!/usr/bin/env python3
"""
Script-Skip-Default-Profile.py
Usage: python3 Script-Skip-Default-Profile.py <input_file> <output_file> <log_file>

This script processes the input file to generate an HTML report,
skipping any keyword match where the next word is "default".
"""

import os
import re
import sys
import logging

def main(input_file_path, output_file_path, log_file_path):
    # Setup logging
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(console_handler)
    
    logging.info("Script-Skip-Default-Profile started...")
    
    # Ensure the input file exists
    if not os.path.exists(input_file_path):
        logging.error(f"Input file not found: {input_file_path}")
        print(f"Error: Input file not found: {input_file_path}")
        sys.exit(1)
    
    # Read input file
    with open(input_file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    
    # Define keyword list (add your full list as needed)
    keywords = set([
        "ip access-list geolocation", "ip access-list eth", "netdestination", "aaa bandwidth-contract",
        # ... add more keywords here ...
    ])
    
    results = []
    # Scan each line for keywords and extract the word following the keyword
    logging.info("Scanning input file for keywords and extracting next words (skipping 'default')...")
    for line in lines:
        for keyword in keywords:
            match = re.search(rf"\b{re.escape(keyword)}\b\s+(?:\"([^\"]+)\"|(\S+))", line)
            if match:
                next_word = match.group(1) if match.group(1) else match.group(2)
                if next_word.lower() == "default":
                    logging.info(f"Skipping keyword '{keyword}' with result 'default'.")
                    continue
                match_count = sum(1 for ln in lines if re.search(rf"\b{re.escape(next_word)}\b", ln))
                found_status = "YES" if match_count >= 2 else "NO"
                results.append((keyword, next_word, found_status))
    
    # VRRP matching optimization (example)
    vrrp_numbers = {re.match(r"^vrrp (\d+)", line).group(1) for line in lines if line.startswith("vrrp")}
    virtual_router_numbers = {re.match(r"^Virtual Router (\d+)", line).group(1) for line in lines if line.startswith("Virtual Router")}
    vrrp_results = []
    logging.info("Scanning VRRP numbers and matching with Virtual Router...")
    for vrrp_num in vrrp_numbers:
        match_found = "YES" if vrrp_num in virtual_router_numbers else "NO"
        vrrp_results.append((f"vrrp {vrrp_num}", match_found))
    
    # Generate HTML report
    logging.info("Generating HTML output...")
    html_content = ["""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HPE Aruba Config Cleanup Review - Skip Default</title>
    <style>
        body { font-family: Calibri, sans-serif; background-color: #f2f2f2; font-size: 18px; }
        .box { border: 10px solid green; color: black; padding: 15px; text-align: center; margin-top: 10px; }
        .found { color: green; font-weight: bold; }
        .not-found { color: red; }
        table { border-collapse: collapse; margin: 20px; }
        th, td { border: 1px solid black; padding: 5px; text-align: center; }
        th { background-color: #FBE2D5; }
    </style>
</head>
<body>
    <div class="box">HPE Aruba Config Cleanup Review - Skip Default</div>
    <div class="info">This report shows the analysis with default profiles skipped.</div>
    <table>
        <tr><th>Config Profile</th><th>Profile Name</th><th>Match</th></tr>
"""]
    for keyword, next_word, found_status in results:
        color_class = "found" if found_status == "YES" else "not-found"
        html_content.append(f"<tr><td>{keyword}</td><td>{next_word}</td><td class='{color_class}'>{found_status}</td></tr>")
    for vrrp, match_status in vrrp_results:
        color_class = "found" if match_status == "YES" else "not-found"
        html_content.append(f"<tr><td>{vrrp}</td><td>Virtual Router</td><td class='{color_class}'>{match_status}</td></tr>")
    html_content.append("</table></body></html>")
    
    with open(output_file_path, "w", encoding="utf-8") as output_file:
        output_file.write("".join(html_content))
    
    logging.info(f"HTML report generated at: {output_file_path}")
    print(f"HTML report generated successfully at: {output_file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 Script-Skip-Default-Profile.py <input_file> <output_file> <log_file>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
