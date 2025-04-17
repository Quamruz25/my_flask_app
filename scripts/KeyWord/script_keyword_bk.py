# Location: /opt/my_flask_app/scripts/KeyWord/script_keyword.py
import subprocess
import os
import html
import shutil
import json
import logging
from pathlib import Path
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(sys.argv[3] if len(sys.argv) > 3 else "keyword_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by replacing invalid characters with underscores."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def extract_with_7z(tar_path: str, extract_dir: str) -> list:
    """
    Extract a tar file using 7z and return a list of extracted file paths.
    
    Args:
        tar_path (str): Path to the tar file.
        extract_dir (str): Directory to extract files into.
    
    Returns:
        list: List of relative paths to extracted files.
    """
    SEVEN_ZIP_PATH = "/usr/bin/7z"  # Adjusted for Linux (p7zip package)
    
    if not os.path.exists(SEVEN_ZIP_PATH):
        logger.error("7z not found at %s", SEVEN_ZIP_PATH)
        raise FileNotFoundError("7z not found. Please ensure p7zip is installed (e.g., 'sudo apt install p7zip-full').")

    if not os.path.exists(tar_path):
        logger.error("Tar file not found at %s", tar_path)
        raise FileNotFoundError(f"Tar file not found: {tar_path}")

    command = [SEVEN_ZIP_PATH, "x", tar_path, f"-o{extract_dir}", "-y"]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info("7z extraction output:\n%s", result.stdout)
        if result.stderr:
            logger.warning("7z extraction warnings:\n%s", result.stderr)

        extracted_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file != "logs.tar":
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, extract_dir)
                    extracted_files.append(rel_path)
        
        logger.info("Extracted %d files", len(extracted_files))
        for file in extracted_files:
            logger.debug(" - %s", file)

        return extracted_files

    except subprocess.CalledProcessError as e:
        logger.error("Error during 7z extraction: %s\n7z output: %s", e, e.output)
        return []
    except PermissionError as e:
        logger.error("Permission error during extraction: %s", e)
        return []
    except Exception as e:
        logger.error("Unexpected error during extraction: %s", e)
        return []

def process_extracted_files(extract_dir: str, extracted_files: list) -> dict:
    """
    Process extracted files and create a repository of file contents.
    
    Args:
        extract_dir (str): Directory containing extracted files.
        extracted_files (list): List of relative paths to extracted files.
    
    Returns:
        dict: Repository mapping file paths to their contents and metadata.
    """
    file_repository = {}
    
    for rel_path in extracted_files:
        file_path = os.path.join(extract_dir, rel_path)
        try:
            if os.path.isfile(file_path):
                try:
                    # Process file line-by-line to reduce memory usage
                    lines = []
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        for line in f:
                            lines.append(line.strip())
                    
                    # Store both original and lowercase lines for efficient searching
                    file_repository[rel_path] = {
                        'content': lines,
                        'content_lowercase': [line.lower() for line in lines],
                        'full_path': file_path
                    }
                except (UnicodeDecodeError, IOError) as e:
                    logger.warning("Unable to read %s as text: %s", rel_path, e)
                    file_repository[rel_path] = {
                        'content': ['[Binary or non-text file]'],
                        'content_lowercase': ['[binary or non-text file]'],
                        'full_path': file_path
                    }
            else:
                logger.info("%s is a directory", rel_path)
                file_repository[rel_path] = {
                    'content': ['[Directory]'],
                    'content_lowercase': ['[directory]'],
                    'full_path': file_path
                }
        except PermissionError as e:
            logger.error("Permission error processing %s: %s", rel_path, e)
            continue
        except Exception as e:
            logger.error("Unexpected error processing %s: %s", rel_path, e)
            continue
    
    logger.info("Processed %d files for search repository", len(file_repository))
    return file_repository

def create_html_search_page(output_dir: str, session_id: str) -> str:
    """
    Create an HTML search page for the extracted files with support for multiple keywords using OR.
    
    Args:
        output_dir (str): Directory to save the HTML file.
        session_id (str): Session ID for constructing the correct fileData.json URL.
    
    Returns:
        str: Path to the generated HTML file.
    """
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HPE Aruba Tech-Support Search</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            background-color: #f4f4f9;
            font-family: 'Candara', Consolas, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
        }}
        .header-container {{
            margin-top: 5px;
            margin-bottom: 10px;
            width: 100%;
            max-width: 1200px;
            display: flex;
            justify-content: center;
            background-color: #d3d3d3;
            padding: 10px;
        }}
        .header-box {{
            padding: 15px 30px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
        }}
        h1 {{
            font-family: 'Candara', sans-serif;
            font-size: 2.5rem;
            color: #333;
            text-align: center;
        }}
        .content-container {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
            max-width: 1200px;
        }}
        .search-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 15px;
        }}
        #searchBar {{
            width: 95%;
            max-width: 1000px;
            padding: 12px 20px;
            font-family: 'Consolas';
            font-size: 1.1rem;
            border: 2px solid #ccc;
            border-radius: 8px;
            outline: none;
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        #searchBar:focus {{
            border-color: #3A7C22;
            box-shadow: 0 0 8px rgba(58, 124, 34, 0.3);
        }}
        #searchButton {{
            padding: 12px 30px;
            background-color: #3A7C22;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-family: 'Roboto', Arial, sans-serif;
            font-size: 1rem;
            font-weight: 500;
            transition: background-color 0.3s ease, transform 0.1s ease;
            flex-shrink: 0;
        }}
        #searchButton:hover {{
            background-color: #2E621A;
            transform: scale(1.05);
        }}
        #searchButton:active {{
            transform: scale(0.95);
        }}
        #caseSensitiveContainer {{
            margin-top: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
        }}
        #caseSensitive {{
            cursor: pointer;
        }}
        #caseSensitiveLabel {{
            font-size: 0.9rem;
            color: #555;
            user-select: none;
        }}
        .results-container {{
            width: 100%;
            padding: 0 20px;
        }}
        .result {{
            margin: 20px 0;
            padding: 15px;
            background-color: #FAE2D5;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            font-family: 'Consolas', monospace;
            font-size: 0.95rem;
            overflow-x: auto;
            white-space: nowrap;
        }}
        .result > div {{
            white-space: nowrap;
            min-width: 0;
        }}
        .filepath {{
            color: #003087;
            font-weight: bold;
            margin-bottom: 10px;
            white-space: nowrap;
        }}
        .line-number {{
            color: #800080;
            margin-right: 10px;
            display: inline-block;
        }}
        #loading {{
            display: none;
            text-align: center;
            margin: 20px 0;
            color: #555;
            font-style: italic;
        }}
        #errorMessage {{
            display: none;
            text-align: center;
            margin: 20px 0;
            color: #d32f2f;
            font-weight: bold;
            background-color: #ffebee;
            padding: 10px;
            border-radius: 5px;
        }}
        .footer {{
            background-color: #d3d3d3;
            padding: 10px;
            text-align: center;
            width: 100%;
        }}
        @media (max-width: 768px) {{
            #searchBar {{
                width: 100%;
                max-width: none;
            }}
            .search-container {{
                flex-direction: column;
                align-items: stretch;
            }}
            #searchButton {{
                width: 100%;
                max-width: 200px;
                margin: 10px auto 0;
            }}
            h1 {{
                font-size: 1.8rem;
            }}
            .result {{
                padding: 10px;
                font-size: 0.9rem;
            }}
            .results-container {{
                padding: 0 10px;
            }}
        }}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap" rel="stylesheet">
</head>
<body>
    <div class="header-container">
        <div class="header-box">
            <h1>HPE Aruba Tech-Support Search</h1>
        </div>
    </div>
    
    <div class="content-container">
        <div class="search-container">
            <input type="text" id="searchBar" placeholder="Enter search keywords separated by OR">
            <button id="searchButton">Search</button>
        </div>
        <div id="caseSensitiveContainer">
            <input type="checkbox" id="caseSensitive" name="caseSensitive">
            <label id="caseSensitiveLabel" for="caseSensitive">Case Sensitive</label>
        </div>
        
        <div id="errorMessage">Error loading file data. Please check the console.</div>
        <div id="loading">Loading...</div>
    </div>

    <div class="results-container">
        <div id="results"></div>
    </div>

    <div class="footer">
        <strong>POWERED BY</strong> - HPE ARUBA PREMIUM SERVICES<br><br>
        <strong>Contact Person</strong> <a href="mailto:mksharma@hpe.com">Manish Sharma</a> & <a href="mailto:quamruz.subhani@hpe.com">Quamruz Subhani</a>
    </div>

    <script>
        const searchBar = document.getElementById('searchBar');
        const searchButton = document.getElementById('searchButton');
        const caseSensitive = document.getElementById('caseSensitive');
        const resultsDiv = document.getElementById('results');
        const loadingDiv = document.getElementById('loading');
        const errorMessageDiv = document.getElementById('errorMessage');
        
        let fileData = null;

        // Function to perform the search with multiple keywords using OR
        function performSearch() {{
            const input = searchBar.value.trim();
            const keywords = input.split('OR').map(kw => kw.trim()).filter(kw => kw.length > 0);
            const isCaseSensitive = caseSensitive.checked;
            resultsDiv.innerHTML = '';
            
            console.log('Searching for keywords:', keywords, 'Case sensitive:', isCaseSensitive);
            
            if (keywords.length === 0) {{
                resultsDiv.innerHTML = '<p>Please enter at least one search keyword</p>';
                return;
            }}

            if (!fileData) {{
                resultsDiv.innerHTML = '<p>File data not loaded yet. Please wait...</p>';
                return;
            }}

            loadingDiv.style.display = 'block';
            let matchCount = 0;
            let resultHtml = '';

            const files = Object.entries(fileData);
            let currentIndex = 0;
            const chunkSize = 100;

            function processChunk() {{
                const endIndex = Math.min(currentIndex + chunkSize, files.length);
                
                for (let i = currentIndex; i < endIndex; i++) {{
                    const [filePath, fileInfo] = files[i];
                    let matchesFound = false;
                    let matchContent = '';

                    const linesToSearch = isCaseSensitive ? fileInfo.content : fileInfo.content_lowercase;
                    const searchKeywords = isCaseSensitive ? keywords : keywords.map(kw => kw.toLowerCase());
                    
                    fileInfo.content.forEach((line, index) => {{
                        const lineToSearch = linesToSearch[index];
                        if (searchKeywords.some(kw => lineToSearch.includes(kw))) {{
                            if (!matchesFound) {{
                                matchContent += `<div class="filepath">${{filePath}}</div>`;
                                matchesFound = true;
                            }}
                            matchContent += `<div><span class="line-number">Line ${{index + 1}}:</span>${{escapeHtml(line)}}</div>`;
                            matchCount++;
                        }}
                    }});

                    if (matchesFound) {{
                        resultHtml += `<div class="result">${{matchContent}}</div>`;
                    }}
                }}

                currentIndex = endIndex;

                if (currentIndex < files.length) {{
                    setTimeout(processChunk, 0);
                }} else {{
                    loadingDiv.style.display = 'none';
                    if (matchCount === 0) {{
                        resultsDiv.innerHTML = '<p>No matches found</p>';
                    }} else {{
                        resultsDiv.innerHTML = resultHtml;
                        console.log('Found', matchCount, 'matches');
                    }}
                }}
            }}

            processChunk();
        }}

        // Load file data
        fetch('/static/keyword/{session_id}/fileData.json')
            .then(response => response.json())
            .then(data => {{
                fileData = data;
                console.log('File data loaded:', Object.keys(fileData).length, 'files');
            }})
            .catch(error => {{
                console.error('Error loading file data:', error);
                errorMessageDiv.style.display = 'block';
            }});

        searchButton.addEventListener('click', function() {{
            performSearch();
        }});

        searchBar.addEventListener('keypress', function(event) {{
            if (event.key === 'Enter') {{
                event.preventDefault();
                performSearch();
            }}
        }});

        caseSensitive.addEventListener('change', function() {{
            if (searchBar.value.trim().length > 0) {{
                performSearch();
            }}
        }});
        
        function escapeHtml(unsafe) {{
            return unsafe
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#39;");
        }}
    </script>
</body>
</html>
"""
    
    html_path = os.path.join(output_dir, "keywordsearch.html")
    try:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info("HTML search page created at %s", html_path)
    except (IOError, OSError) as e:
        logger.error("Failed to write HTML file at %s: %s", html_path, e)
        raise
    
    return html_path

def run_full_process(input_dir: str, output_dir: str, tar_path: str, session_id: str) -> bool:
    """
    Run the full process: extract files, process them, and generate the search page.
    
    Args:
        input_dir (str): Directory for extracted files.
        output_dir (str): Directory for output files (HTML, JSON).
        tar_path (str): Path to the tar file.
        session_id (str): Session ID for constructing URLs.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        logger.info("Created directories: %s, %s", input_dir, output_dir)
    except (OSError, PermissionError) as e:
        logger.error("Failed to create directories %s, %s: %s", input_dir, output_dir, e)
        return False
    
    # Step 1: Extract logs.tar
    extracted_files = extract_with_7z(tar_path, input_dir)
    if not extracted_files:
        logger.warning("No files were extracted from %s", tar_path)
        print("No files were extracted from logs.tar. Please check the tar file and 7z installation.")
        return False

    # Step 2: Find and process configs.tar.gz
    configs_tar_gz_path = os.path.join(input_dir, "configs.tar.gz")
    config_dir = os.path.join(input_dir, "config")
    if os.path.exists(configs_tar_gz_path):
        # Create config directory and move configs.tar.gz into it
        os.makedirs(config_dir, exist_ok=True)
        shutil.move(configs_tar_gz_path, os.path.join(config_dir, "configs.tar.gz"))
        logger.info("Moved configs.tar.gz to %s", config_dir)
        
        # Extract configs.tar.gz in config folder
        configs_tar_gz_new_path = os.path.join(config_dir, "configs.tar.gz")
        extract_with_7z(configs_tar_gz_new_path, config_dir)
        logger.info("Extracted configs.tar.gz in %s", config_dir)
        
        # Check for configs.tar inside config folder and extract it
        configs_tar_path = os.path.join(config_dir, "configs.tar")
        if os.path.exists(configs_tar_path):
            extract_with_7z(configs_tar_path, config_dir)
            logger.info("Extracted configs.tar in %s", config_dir)
    else:
        logger.warning("configs.tar.gz not found in %s", input_dir)

    # Step 3: Find and process mm_logs.tar.gz in \var\log\oslog\memlogs
    memlogs_dir = os.path.join(input_dir, "var", "log", "oslog", "memlogs")
    mm_logs_tar_gz_path = os.path.join(memlogs_dir, "mm_logs.tar.gz")
    if os.path.exists(mm_logs_tar_gz_path):
        # Extract mm_logs.tar.gz in memlogs directory
        extract_with_7z(mm_logs_tar_gz_path, memlogs_dir)
        logger.info("Extracted mm_logs.tar.gz in %s", memlogs_dir)
        
        # Check for mm_logs.tar and extract it
        mm_logs_tar_path = os.path.join(memlogs_dir, "mm_logs.tar")
        if os.path.exists(mm_logs_tar_path):
            extract_with_7z(mm_logs_tar_path, memlogs_dir)
            logger.info("Extracted mm_logs.tar in %s", memlogs_dir)
    else:
        logger.warning("mm_logs.tar.gz not found in %s", memlogs_dir)

    # Step 4: Process all extracted files
    extracted_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file != "logs.tar":
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, input_dir)
                extracted_files.append(rel_path)
    
    if not extracted_files:
        logger.warning("No files were found after all extractions")
        print("No files were found after all extractions.")
        return False

    # Process extracted files
    file_repository = process_extracted_files(input_dir, extracted_files)
    
    if not file_repository:
        logger.warning("No files were processed for the search repository")
        print("No files were processed for the search repository.")
        return False

    # Save file data to a separate JSON file
    json_path = os.path.join(output_dir, "fileData.json")
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(file_repository, f, ensure_ascii=False)
        logger.info("File data saved at %s", json_path)
    except (IOError, OSError) as e:
        logger.error("Failed to write JSON file at %s: %s", json_path, e)
        print(f"Error: Failed to write JSON file at {json_path}: {e}")
        return False
    
    # Create HTML search page
    try:
        html_path = create_html_search_page(output_dir, session_id)
        print(f"Search page generated successfully at: {html_path}")
        print(f"File data saved at: {json_path}")
        print(f"All files extracted to: {input_dir}")
        return True
    except Exception as e:
        logger.error("Failed to create HTML search page: %s", e)
        print(f"Error: Failed to create HTML search page: {e}")
        return False

def main():
    """Main function to run the script."""
    if len(sys.argv) < 4:
        logger.error("Usage: python script_keyword.py <input_dir> <output_dir> <log_file> <session_id>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    session_id = sys.argv[4]
    tar_path = os.path.join(input_dir, "logs.tar")
    
    success = run_full_process(input_dir, output_dir, tar_path, session_id)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()