# Location: /opt/my_flask_app/scripts/KeyWord/script_keyword.py
import os
import json
import http.server
import socketserver
import webbrowser
import threading
import time
import socket
import sys
import logging

# Optional: Use ujson for faster JSON serialization if available
try:
    import ujson as json_lib
except ImportError:
    import json as json_lib
    print("ujson not installed. Using standard json library.")

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

def find_free_port(start_port: int = 8000, max_attempts: int = 50) -> int:
    """
    Find an available port starting from start_port.
    
    Args:
        start_port (int): Starting port number to check.
        max_attempts (int): Maximum number of ports to try.
    
    Returns:
        int: Available port number.
    
    Raises:
        RuntimeError: If no free port is found.
    """
    port = start_port
    for attempt in range(max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("localhost", port))
                logger.debug("Found free port: %d", port)
                return port
        except OSError as e:
            if e.errno == 98:  # Linux: Address already in use
                logger.warning("Port %d is already in use", port)
            else:
                logger.warning("Failed to bind to port %d: %s", port, e)
            port += 1
    logger.error("Could not find a free port between %d and %d", start_port, port - 1)
    raise RuntimeError(f"Could not find a free port between {start_port} and {port - 1}.")

def start_local_server(directory: str, port: int) -> None:
    """
    Start a local HTTP server to serve the search page.
    
    Args:
        directory (str): Directory to serve files from.
        port (int): Port to run the server on.
    """
    try:
        os.chdir(directory)
        logger.info("Changed working directory to %s", directory)
    except (OSError, PermissionError) as e:
        logger.error("Failed to change directory to %s: %s", directory, e)
        print(f"Error: Could not change to directory {directory}: {e}")
        sys.exit(1)

    try:
        Handler = http.server.SimpleHTTPRequestHandler
        httpd = socketserver.TCPServer(("", port), Handler, bind_and_activate=False)
        httpd.allow_reuse_address = True
        httpd.server_bind()
        httpd.server_activate()
        logger.info("Serving at http://localhost:%d/keywordsearch.html", port)
        print(f"Serving at http://localhost:{port}/keywordsearch.html")
        print("Press Ctrl+C to stop the server")
        httpd.serve_forever()
    except OSError as e:
        if e.errno == 98:  # Linux: Address already in use
            logger.error("Port %d is already in use", port)
            print(f"Error: Port {port} is already in use. Please free the port or try a different one.")
            print("To find the process using the port, run the following command:")
            print(f"  lsof -i :{port}")
            print("Then, terminate the process using:")
            print("  kill -9 <pid>")
            print("Alternatively, rerun the script to automatically select a different port.")
        else:
            logger.error("Error starting server on port %d: %s", port, e)
            print(f"Error starting server on port {port}: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error starting server on port %d: %s", port, e)
        print(f"Unexpected error starting server on port {port}: {e}")
        sys.exit(1)

def create_html_search_page(output_dir: str, file_repository: dict) -> str:
    """
    Create an HTML search page by embedding the file repository JSON data.
    
    Args:
        output_dir (str): Directory to save the HTML file.
        file_repository (dict): JSON data to embed.
    
    Returns:
        str: Path to the generated HTML file.
    """
    # Embed file data directly into the HTML
    file_data_json = json_lib.dumps(file_repository, ensure_ascii=False)
    
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
            font-family: 'Roboto', Consolas, sans-serif;
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
        }}
        .header-box {{
            border: 10px solid #3A7C22;
            padding: 15px 30px;
            background-color: #f4f4f9;
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
        
        <div id="errorMessage">This page must be accessed via a local web server. Please run the script with --server-only to start the server and access the page at <a href="http://localhost:8000/keywordsearch.html">http://localhost:8000/keywordsearch.html</a>.</div>
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

        // Embed file data directly
        const fileData = {file_data_json};

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

        // Check if the page is being accessed via file://
        if (window.location.protocol === 'file:') {{
            errorMessageDiv.style.display = 'block';
            searchBar.disabled = true;
            searchButton.disabled = true;
        }} else {{
            console.log('File data loaded:', Object.keys(fileData).length, 'files');

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
        }}

        function escapeHtml(unsafe) {{
            return unsafe
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
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

def run_full_process(input_dir: str, output_dir: str, session_id: str) -> bool:
    """
    Run the process to read input.json and generate the search page.
    
    Args:
        input_dir (str): Directory containing the input.json file.
        output_dir (str): Directory for the output HTML file.
        session_id (str): Session identifier (not used in this context).
    
    Returns:
        bool: True if successful, False otherwise.
    """
    # Define the path to input.json
    input_json_path = os.path.join(input_dir, "keyword_input.json")
    
    if not os.path.exists(input_json_path):
        logger.error("input.json not found at %s", input_json_path)
        print(f"Error: input.json not found at {input_json_path}")
        return False
    
    try:
        # Read the input.json file
        with open(input_json_path, 'r', encoding='utf-8') as f:
            file_repository = json_lib.load(f)
        
        logger.info("Successfully loaded input.json with %d entries", len(file_repository))
        
        # Create the HTML search page with embedded data
        html_path = create_html_search_page(output_dir, file_repository)
        print(f"Search page generated successfully at: {html_path}")
        
        # Find a free port and start the server
        try:
            port = find_free_port(8000)
        except RuntimeError as e:
            logger.error("Failed to find a free port: %s", e)
            print(f"Error: {e}")
            return False
        
        url = f"http://localhost:{port}/keywordsearch.html"
        server_thread = threading.Thread(target=start_local_server, args=(output_dir, port))
        server_thread.daemon = True
        server_thread.start()
        
        time.sleep(1)
        webbrowser.open(url)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
            print("\nServer stopped.")
        
        return True
    except json.JSONDecodeError as e:
        logger.error("Failed to parse input.json: %s", e)
        print(f"Error: Failed to parse input.json: {e}")
        return False
    except Exception as e:
        logger.error("Unexpected error processing input.json: %s", e)
        print(f"Error: Unexpected error processing input.json: {e}")
        return False

def main():
    """Main function to execute the script."""
    if len(sys.argv) < 4:
        logger.error("Usage: python script_keyword.py <input_dir> <output_dir> <log_file> <session_id>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    session_id = sys.argv[4]
    
    success = run_full_process(input_dir, output_dir, session_id)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()