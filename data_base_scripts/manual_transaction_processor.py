#!/usr/bin/env python3
"""
manual_transaction_processor.py
Location: /opt/my_flask_app/scripts/manual_transaction_processor.py

Usage:
    python3 manual_transaction_processor.py --transaction-folder <path-to-transaction-folder>

This script processes a transaction folder by:
1. Extracting logs.tar using 7-Zip into the transaction folder.
2. Moving and recursively extracting configs.tar.gz (if present) into a "config" folder.
3. Creating "input" and "output" folders.
4. Generating input files:
     - CCR_input.txt: contains blocks for "show running-config" (until a line exactly "end"),
                      "show vrrp stats all" (until the next line that starts with "show"),
                      and "show ap active" (until the next line that starts with "show").
     - CHR_input.txt: contains the "show running-config" block (until "end").
     - bucket_input.txt: contains the full content of tech-support.log.
     - keyword_input.json: a JSON dataset built from all files in flash, mswitch, var, and config.
5. Saving session metadata to a JSON file.
6. Logging all operations to a log file "processing.log" in the transaction folder.
"""

import os
import sys
import subprocess
import shutil
import logging
import argparse
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# -------------------------------
# Helper: Setup logger to file
# -------------------------------
def setup_logger(log_path):
    logger = logging.getLogger("manual_processor")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

# -------------------------------
# Helper: Run 7z extraction
# -------------------------------
def extract_with_7z(archive_path, output_dir, logger):
    cmd = ["7z", "x", archive_path, f"-o{output_dir}", "-y"]
    logger.debug("Running command: " + " ".join(cmd))
    try:
        result = subprocess.run(cmd, universal_newlines=True)
        logger.debug("7z command finished with return code: " + str(result.returncode))
        if result.returncode != 0:
            logger.error("Extraction failed for " + archive_path)
            return False
        return True
    except Exception as e:
        logger.error("Exception during extraction of {}: {}".format(archive_path, e))
        return False

# -------------------------------
# Helper: Find tech-support.log recursively
# -------------------------------
def find_techsupport_log(transaction_folder, logger):
    for root, dirs, files in os.walk(transaction_folder):
        for file in files:
            if file == "tech-support.log":
                path = os.path.join(root, file)
                logger.debug("Found tech-support.log at: " + path)
                return path
    logger.warning("tech-support.log not found in transaction folder: " + transaction_folder)
    return None

# -------------------------------
# Helper: Extract a block of text
# -------------------------------
def extract_block_from_lines(lines, start_phrase, stop_condition):
    block = []
    capturing = False
    for line in lines:
        if not capturing and line.strip() == start_phrase:
            capturing = True
        if capturing:
            block.append(line)
            if stop_condition(line):
                break
    return "".join(block)

# -------------------------------
# Generate Input Functions
# -------------------------------
def generate_ccr_input(transaction_folder, logger):
    log_path = find_techsupport_log(transaction_folder, logger)
    if not log_path:
        return ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error("Error reading tech-support.log for CCR: " + str(e))
        return ""
    # Extract "show running-config" block until a line exactly "end"
    running_config = extract_block_from_lines(
        lines,
        "show running-config",
        lambda line: line.strip().lower() == "end"
    )
    # Extract "show vrrp stats all" block until the next "show" command (excluding it)
    vrrp_block = extract_block_from_lines(
        lines,
        "show vrrp stats all",
        lambda line: line.strip().startswith("show") and line.strip() != "show vrrp stats all"
    )
    # Extract "show ap active" block similarly
    ap_active = extract_block_from_lines(
        lines,
        "show ap active",
        lambda line: line.strip().startswith("show") and line.strip() != "show ap active"
    )
    combined = running_config + "\n" + vrrp_block + "\n" + ap_active
    logger.debug("Generated CCR input length: {} characters".format(len(combined)))
    return combined

def generate_chr_input(transaction_folder, logger):
    log_path = find_techsupport_log(transaction_folder, logger)
    if not log_path:
        return ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error("Error reading tech-support.log for CHR: " + str(e))
        return ""
    running_config = extract_block_from_lines(
        lines,
        "show running-config",
        lambda line: line.strip().lower() == "end"
    )
    logger.debug("Generated CHR input length: {} characters".format(len(running_config)))
    return running_config

def generate_bucket_input(transaction_folder, logger):
    log_path = find_techsupport_log(transaction_folder, logger)
    if not log_path:
        return ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        logger.debug("Generated Bucket input length: {} characters".format(len(content)))
        return content
    except Exception as e:
        logger.error("Error reading tech-support.log for Bucket: " + str(e))
        return ""

def generate_keyword_input(transaction_folder, logger):
    base_dirs = ["flash", "mswitch", "var"]
    config_dir = os.path.join(transaction_folder, "config")
    if os.path.exists(config_dir):
        base_dirs.append("config")
    file_data = {}
    for d in base_dirs:
        dir_path = os.path.join(transaction_folder, d)
        if not os.path.exists(dir_path):
            logger.warning("Directory not found for keyword input: " + dir_path)
            continue
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, transaction_folder)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    file_data[rel_path] = content
                except Exception as e:
                    logger.error("Error reading file {}: {}".format(full_path, e))
    dataset = json.dumps(file_data, indent=2)
    logger.debug("Generated Keyword input dataset with {} files".format(len(file_data)))
    return dataset

# -------------------------------
# Main processing function
# -------------------------------
def process_transaction(transaction_folder):
    transaction_folder = os.path.abspath(transaction_folder)
    log_file_path = os.path.join(transaction_folder, "processing.log")
    logger = setup_logger(log_file_path)
    logger.info("Starting transaction processing for folder: " + transaction_folder)

    # Verify existence of logs.tar
    logs_tar = os.path.join(transaction_folder, "logs.tar")
    if not os.path.exists(logs_tar):
        logger.error("logs.tar not found in transaction folder: " + transaction_folder)
        return False

    # Extract logs.tar into the transaction folder
    if not extract_with_7z(logs_tar, transaction_folder, logger):
        logger.error("Failed to extract logs.tar")
        return False
    logger.info("Extracted logs.tar successfully.")

    # Process the configs.tar.gz file (if exists) from the transaction folder
    configs_tar_gz = os.path.join(transaction_folder, "configs.tar.gz")
    if os.path.exists(configs_tar_gz):
        config_folder = os.path.join(transaction_folder, "config")
        os.makedirs(config_folder, exist_ok=True)
        new_configs_path = os.path.join(config_folder, "configs.tar.gz")
        shutil.move(configs_tar_gz, new_configs_path)
        logger.info("Moved configs.tar.gz to config folder: " + config_folder)
        if extract_with_7z(new_configs_path, config_folder, logger):
            logger.info("Extracted configs.tar.gz in config folder successfully.")
        else:
            logger.error("Failed to extract configs.tar.gz in config folder.")
        # If a configs.tar file appears, extract it recursively
        configs_tar = os.path.join(config_folder, "configs.tar")
        if os.path.exists(configs_tar):
            if extract_with_7z(configs_tar, config_folder, logger):
                logger.info("Extracted configs.tar in config folder successfully.")
            else:
                logger.error("Failed to extract configs.tar in config folder.")
    else:
        logger.warning("configs.tar.gz not found in transaction folder.")

    # Create input and output folders
    input_folder = os.path.join(transaction_folder, "input")
    output_folder = os.path.join(transaction_folder, "output")
    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)
    logger.info("Created input folder: " + input_folder)
    logger.info("Created output folder: " + output_folder)

    # Generate input files from tech-support.log found under var (recursively)
    ccr_input = generate_ccr_input(transaction_folder, logger)
    with open(os.path.join(input_folder, "CCR_input.txt"), "w", encoding="utf-8") as f:
        f.write(ccr_input)
    logger.info("CCR input file created.")

    chr_input = generate_chr_input(transaction_folder, logger)
    with open(os.path.join(input_folder, "CHR_input.txt"), "w", encoding="utf-8") as f:
        f.write(chr_input)
    logger.info("CHR input file created.")

    bucket_input = generate_bucket_input(transaction_folder, logger)
    with open(os.path.join(input_folder, "bucket_input.txt"), "w", encoding="utf-8") as f:
        f.write(bucket_input)
    logger.info("Bucket input file created.")

    keyword_input = generate_keyword_input(transaction_folder, logger)
    with open(os.path.join(input_folder, "keyword_input.json"), "w", encoding="utf-8") as f:
        f.write(keyword_input)
    logger.info("Keyword input file created.")

    # Save session metadata (for debugging we save as a JSON file)
    session_metadata = {
        "session_id": os.path.basename(transaction_folder),
        "username": "manual_test",
        "case_number": "manual_case",
        "transaction_folder": transaction_folder,
        "upload_timestamp": datetime.now().isoformat()
    }
    metadata_file = os.path.join(transaction_folder, "session_metadata.json")
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(session_metadata, f, indent=2)
    logger.info("Session metadata saved.")

    return True

def main():
    parser = argparse.ArgumentParser(description="Manually process a transaction folder to generate input, output, and log files.")
    parser.add_argument("--transaction-folder", required=True, help="Path to the transaction folder")
    args = parser.parse_args()
    if process_transaction(args.transaction_folder):
        print("Transaction processing completed successfully.")
    else:
        print("Transaction processing failed. Check the processing.log for details.")

if __name__ == "__main__":
    main()
