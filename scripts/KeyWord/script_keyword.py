#!/usr/bin/env python3
# Location: /opt/my_flask_app/scripts/KeyWord/script_keyword.py
import os
import sys
import json
import logging
import re
from typing import Tuple

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(sys.argv[3] if len(sys.argv) > 3 else "keyword_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def sanitize_input(keyword_input: dict) -> dict:
    """
    Sanitize the keyword input by removing lines that look like log messages or errors.
    
    Args:
        keyword_input: Dictionary containing file paths and their contents.
    
    Returns:
        Sanitized dictionary with filtered content.
    """
    sanitized_input = {}
    log_pattern = re.compile(r'httpd\[|nginx:|\[error\]|\[cgid:error\]|\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
    
    for file_path, data in keyword_input.items():
        content = data['content']
        content_lowercase = data['content_lowercase']
        # Filter out lines that match the log pattern
        filtered_content = []
        filtered_content_lowercase = []
        for line, line_lower in zip(content, content_lowercase):
            if not log_pattern.search(line):
                filtered_content.append(line)
                filtered_content_lowercase.append(line_lower)
        sanitized_input[file_path] = {
            'content': filtered_content,
            'content_lowercase': filtered_content_lowercase
        }
    
    logger.debug(f"Sanitized keyword input: {len(sanitized_input)} files")
    return sanitized_input

def create_html_search_page(input_json_path: str, output_dir: str, session_id: str) -> str:
    """
    Create an HTML search page with a table of search results.
    
    Args:
        input_json_path: Path to the input JSON file.
        output_dir: Directory for the output HTML file.
        session_id: Session identifier (not used in filename).
    
    Returns:
        Name of the generated HTML file ('keywordsearch.html').
    """
    html_filename = "keywordsearch.html"
    html_path = os.path.join(output_dir, html_filename)

    # Load and sanitize the JSON data
    with open(input_json_path, 'r', encoding='utf-8') as json_file:
        keyword_input = json.load(json_file)
    logger.debug(f"Loaded keyword input with {len(keyword_input)} files")

    # Sanitize the input to remove log messages
    keyword_input = sanitize_input(keyword_input)

    # HTML header with Bootstrap
    html_start = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HPE Aruba Tech-Support Search</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            padding: 20px;
            font-family: 'Roboto', Arial, sans-serif;
        }
        .header-container {
            margin-top: 5px;
            margin-bottom: 20px;
            text-align: center;
        }
        .header-box {
            border: 10px solid #3A7C22;
            padding: 15px 30px;
            background-color: #f4f4f9;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            display: inline-block;
        }
        h1 {
            font-family: 'Candara', Arial, sans-serif;
            font-size: 2.5rem;
            color: #333;
        }
        .search-container {
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            justify-content: center;
        }
        #searchBar {
            width: 100%;
            max-width: 600px;
            padding: 10px;
            font-size: 1.1rem;
            border: 2px solid #ccc;
            border-radius: 8px;
            outline: none;
        }
        #searchBar:focus {
            border-color: #3A7C22;
            box-shadow: 0 0 8px rgba(58, 124, 34, 0.3);
        }
        #searchButton {
            padding: 10px 20px;
            background-color: #3A7C22;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        #searchButton:hover {
            background-color: #2E621A;
        }
        #caseSensitiveContainer {
            margin-top: 10px;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        #caseSensitiveLabel {
            font-size: 0.9rem;
            color: #555;
        }
        .results-table {
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
        }
        .filepath {
            color: #003087;
            font-weight: bold;
        }
        .line-number {
            color: #800080;
        }
        #loading {
            display: none;
            text-align: center;
            margin: 20px 0;
            color: #555;
            font-style: italic;
        }
        #errorMessage {
            display: none;
            text-align: center;
            margin: 20px 0;
            color: #d32f2f;
            font-weight: bold;
            background-color: #ffebee;
            padding: 10px;
            border-radius: 5px;
        }
        .footer {
            background-color: #d3d3d3;
            padding: 10px;
            text-align: center;
            margin-top: 20px;
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap" rel="stylesheet">
</head>
<body>
    <div class="header-container">
        <div class="header-box">
            <h1>HPE Aruba Tech-Support Search</h1>
        </div>
    </div>

    <div class="container">
        <div class="search-container">
            <input type="text" id="searchBar" placeholder="Enter search keywords separated by OR">
            <button id="searchButton">Search</button>
        </div>
        <div id="caseSensitiveContainer" class="text-center">
            <input type="checkbox" id="caseSensitive" name="caseSensitive">
            <label id="caseSensitiveLabel" for="caseSensitive">Case Sensitive</label>
        </div>

        <div id="loading">Loading...</div>
        <div id="errorMessage"></div>

        <table class="table table-striped results-table" id="resultsTable">
            <thead>
                <tr>
                    <th>File Path</th>
                    <th>Line Number</th>
                    <th>Line Content</th>
                </tr>
            </thead>
            <tbody id="resultsBody">
            </tbody>
        </table>
    </div>

    <div class="footer">
        <strong>POWERED BY</strong> - HPE ARUBA PREMIUM SERVICES<br><br>
        <strong>Contact Person</strong> <a href="mailto:mksharma@hpe.com">Manish Sharma</a> & <a href="mailto:quamruz.subhani@hpe.com">Quamruz Subhani</a>
    </div>
"""

    # JavaScript for client-side searching with default search
    js_code = """
    <script>
        const searchBar = document.getElementById('searchBar');
        const searchButton = document.getElementById('searchButton');
        const caseSensitive = document.getElementById('caseSensitive');
        const resultsBody = document.getElementById('resultsBody');
        const loadingDiv = document.getElementById('loading');
        const errorMessageDiv = document.getElementById('errorMessage');

        // Store the original keyword input for client-side re-search
        const keywordInput = %s;

        function escapeHtml(unsafe) {
            return unsafe
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        function performSearch(keywordsInput = 'error') {
            let input = keywordsInput;
            if (keywordsInput === 'error' && searchBar.value.trim()) {
                input = searchBar.value.trim();
            }
            const keywords = input.split('OR').map(kw => kw.trim()).filter(kw => kw.length > 0);
            const isCaseSensitive = caseSensitive.checked;

            if (keywords.length === 0) {
                resultsBody.innerHTML = '<tr><td colspan="3">Please enter at least one search keyword.</td></tr>';
                return;
            }

            loadingDiv.style.display = 'block';

            // Perform the search
            const matches = {};
            for (const filePath in keywordInput) {
                const data = keywordInput[filePath];
                const content = data.content;
                const contentLowercase = data.content_lowercase;
                const linesToSearch = isCaseSensitive ? content : contentLowercase;
                const originalLines = content;

                const fileMatches = [];
                for (let i = 0; i < linesToSearch.length; i++) {
                    for (const keyword of keywords) {
                        const searchKey = isCaseSensitive ? keyword : keyword.toLowerCase();
                        if (!linesToSearch[i] || !searchKey) continue;
                        if (linesToSearch[i].includes(searchKey)) {
                            // Highlight all keywords in the line
                            let highlightedLine = escapeHtml(originalLines[i]);
                            for (const kw of keywords) {
                                const pattern = new RegExp(kw, isCaseSensitive ? 'g' : 'gi');
                                highlightedLine = highlightedLine.replace(
                                    pattern,
                                    match => `<span style="background-color: yellow;">${match}</span>`
                                );
                            }
                            fileMatches.push({
                                lineNumber: i + 1,
                                line: originalLines[i],
                                highlightedLine: highlightedLine
                            });
                            break; // OR logic: stop after the first matching keyword
                        }
                    }
                }
                if (fileMatches.length > 0) {
                    matches[filePath] = fileMatches;
                }
            }

            // Display the results
            resultsBody.innerHTML = '';
            let matchCount = 0;
            for (const filePath in matches) {
                const entries = matches[filePath];
                entries.sort((a, b) => a.lineNumber - b.lineNumber);
                entries.forEach(entry => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="filepath">${escapeHtml(filePath)}</td>
                        <td class="line-number">${entry.lineNumber}</td>
                        <td>${entry.highlightedLine}</td>
                    `;
                    resultsBody.appendChild(row);
                    matchCount++;
                });
            }

            loadingDiv.style.display = 'none';
            if (matchCount === 0) {
                resultsBody.innerHTML = '<tr><td colspan="3">No matches found.</td></tr>';
            }
        }

        searchButton.addEventListener('click', () => performSearch());

        searchBar.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                performSearch();
            }
        });

        caseSensitive.addEventListener('change', function() {
            performSearch();
        });

        // Perform a default search for "error" on page load
        window.onload = function() {
            performSearch('error');
        };
    </script>
"""

    html_end = """
</body>
</html>
"""

    try:
        with open(html_path, 'w', encoding='utf-8') as f:
            # Write HTML start
            f.write(html_start)

            # Embed the keyword_input data for client-side searching
            f.write(js_code % json.dumps(keyword_input))

            # Write HTML end
            f.write(html_end)

        logger.info("HTML search page created at %s", html_path)
        return html_filename

    except Exception as e:
        logger.error("Failed to create HTML search page: %s", e)
        raise

def run_full_process(input_dir: str, output_dir: str, session_id: str) -> Tuple[bool, str]:
    """
    Process the input JSON and generate the search page.
    
    Args:
        input_dir: Directory containing the input JSON file.
        output_dir: Directory for the output HTML file.
        session_id: Session identifier (not used in filename).
    
    Returns:
        A tuple containing a success status and a message.
    """
    input_json_path = os.path.join(input_dir, "keyword_input.json")
    
    if not os.path.exists(input_json_path):
        logger.error("input.json not found at %s", input_json_path)
        return False, f"Error: input.json not found at {input_json_path}"
    
    try:
        # Create the HTML search page
        html_filename = create_html_search_page(input_json_path, output_dir, session_id)
        
        logger.info("Search page generated successfully at: %s", html_filename)
        return True, f"Search page generated successfully at: {html_filename}"
    
    except Exception as e:
        logger.error("Unexpected error processing input.json: %s", e)
        return False, f"Error: Unexpected error processing input.json: {e}"

def main() -> None:
    """
    Main function to execute the script.
    """
    if len(sys.argv) < 4:
        logger.error("Usage: python script_keyword.py <input_dir> <output_dir> <log_file> <session_id>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    session_id = sys.argv[4]
    
    success, result = run_full_process(input_dir, output_dir, session_id)
    if not success:
        print(result)
        sys.exit(1)
    print(result)

if __name__ == "__main__":
    main()