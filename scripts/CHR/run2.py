#!/usr/bin/env python3
# Location: /opt/my_flask_app/scripts/CHR/run2.py
"""
run2.py - CHR Step 2
Usage: python3 run2.py <modified_input_file> <output_html_file> <log_file>
Generates an HTML output with a hierarchical view of the modified CHR configuration.
"""
import sys
import os
import re
import json
from pathlib import Path

if len(sys.argv) < 4:
    print("Usage: python3 run2.py <modified_input_file> <output_html_file> <log_file>")
    sys.exit(1)

input_file = sys.argv[1]
output_html = sys.argv[2]
log_file = sys.argv[3]

# Ensure output directory exists
os.makedirs(os.path.dirname(output_html), exist_ok=True)

# -------------------------------------------------------
# Helper Functions
# -------------------------------------------------------
def read_config_file(file_path):
    """Read the entire configuration file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().splitlines()
    except Exception as e:
        print(f"Error reading configuration file {file_path}: {e}")
        raise

def split_into_blocks(lines):
    """Split the config into blocks separated by '!'."""
    try:
        blocks = []
        current_block = []
        for line in lines:
            if line.strip() == "!":
                if current_block:
                    blocks.append(current_block)
                    current_block = []
            else:
                current_block.append(line)
        if current_block:
            blocks.append(current_block)
        return blocks
    except Exception as e:
        print(f"Error splitting lines into blocks: {e}")
        raise

def extract_quoted(text):
    """Extract quoted strings from a line."""
    try:
        return re.findall(r'"([^"]+)"', text)
    except Exception as e:
        print(f"Error extracting quoted strings from text: {e}")
        raise

def extract_next_word(line, keyword):
    """Extract the next word after a keyword in a line."""
    try:
        parts = line.split()
        index = parts.index(keyword)
        if index + 1 < len(parts):
            return parts[index + 1]
    except (ValueError, IndexError) as e:
        print(f"Error extracting word after keyword '{keyword}': {e}")
        return None

def build_block_index(blocks):
    """Index blocks by their quoted identifier and type."""
    try:
        block_index = {}
        for block in blocks:
            header = block[0].strip()
            quoted = extract_quoted(header)
            if quoted:
                key = quoted[0]
                block_type = header.split()[0]  # e.g., 'aaa', 'user-role', 'ip'
                block_index.setdefault(key, []).append((block_type, block))
        return block_index
    except Exception as e:
        print(f"Error building block index: {e}")
        raise

def build_hierarchy(block, block_index, visited=None):
    """Recursively build the hierarchy for a block with specific mappings."""
    if visited is None:
        visited = set()
    
    try:
        block_id = id(block)
        if block_id in visited:
            return {"config": "\n".join(block) + "\n!", "children": {}}
        
        visited.add(block_id)
        block_text = "\n".join(block) + "\n!"
        hierarchy = {"config": block_text, "children": {}}

        header = block[0].strip()
        block_type = header.split()[0]  # e.g., 'aaa', 'user-role'

        for line in block[1:]:  # Skip the header
            line = line.strip()

            # Lookup for additional profiles
            if block_type == "aaa":
                if "authentication-mac" in header:
                    if line.startswith("mac-server-group"):
                        mac_name = extract_next_word(line, "mac-server-group")
                        if mac_name and mac_name in block_index:
                            for b_type, child_block in block_index[mac_name]:
                                if b_type == "mac-server-group":
                                    hierarchy["children"][f"mac-server-group_{mac_name}"] = build_hierarchy(child_block, block_index, visited.copy())
                elif "profile" in header:
                    if line.startswith("authentication-dot1x"):
                        profile_name = extract_next_word(line, "authentication-dot1x")
                        if profile_name and profile_name in block_index:
                            for b_type, child_block in block_index[profile_name]:
                                if b_type == "profile":
                                    hierarchy["children"][f"authentication-dot1x_{profile_name}"] = build_hierarchy(child_block, block_index, visited.copy())

            # Profile Handling for Captive Portal
            if "captive-portal" in header:
                if line.startswith("captive-portal"):
                    profile_name = extract_next_word(line, "captive-portal")
                    if profile_name and profile_name in block_index:
                        for b_type, child_block in block_index[profile_name]:
                            if b_type == "profile":
                                hierarchy["children"][f"captive-portal_{profile_name}"] = build_hierarchy(child_block, block_index, visited.copy())

            # Profile Lookup for Radius Accounting
            if block_type == "radius-accounting":
                if line.startswith("rfc-3576-server"):
                    server_name = extract_next_word(line, "rfc-3576-server")
                    if server_name and server_name in block_index:
                        for b_type, child_block in block_index[server_name]:
                            if b_type == "rfc-3576-server":
                                hierarchy["children"][f"rfc-3576-server_{server_name}"] = build_hierarchy(child_block, block_index, visited.copy())
                
            # Other profiles for access list session, vlan, etc.
            elif "access-list session" in line:
                acl_name = extract_next_word(line, "session")
                if acl_name and acl_name in block_index:
                    for b_type, child_block in block_index[acl_name]:
                        if b_type == "ip" and "access-list" in child_block[0]:
                            hierarchy["children"][f"access-list_session_{acl_name}"] = build_hierarchy(child_block, block_index, visited.copy())
                            
            elif "vlan" in line:
                vlan_name = extract_next_word(line, "vlan")
                if vlan_name and vlan_name in block_index:
                    for b_type, child_block in block_index[vlan_name]:
                        if b_type == "vlan":
                            hierarchy["children"][f"vlan-{vlan_name}"] = build_hierarchy(child_block, block_index, visited.copy())

            # General Profile Matching
            names = extract_quoted(line)
            for name in names:
                if name in block_index:
                    for b_type, child_block in block_index[name]:
                        hierarchy["children"][name] = build_hierarchy(child_block, block_index, visited.copy())

        return hierarchy
    except Exception as e:
        print(f"Error building hierarchy: {e}")
        raise

# -------------------------------------------------------
# Main Processing
# -------------------------------------------------------
try:
    # Read and process the configuration
    config_lines = read_config_file(input_file)
    blocks = split_into_blocks(config_lines)
    block_index = build_block_index(blocks)

    # Find all ap-group blocks as the top-level structure
    ap_group_blocks = [block for block in blocks if block and block[0].strip().lower().startswith("ap-group")]
    ap_groups_hierarchy = {}
    for block in ap_group_blocks:
        header_quoted = extract_quoted(block[0])
        if header_quoted:
            ap_group_name = header_quoted[0]
            ap_groups_hierarchy[ap_group_name] = build_hierarchy(block, block_index)
except Exception as e:
    print(f"Error in main processing: {e}")

# -------------------------------------------------------
# HTML Generation with Expandable Sections and Collapse All Button
# -------------------------------------------------------
def generate_html(ap_groups):
    """Generate an HTML page with an expandable hierarchy and a collapse all button."""
    try:
        hierarchy_json = json.dumps(ap_groups)
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>HPE Aruba Config Hierarchy</title>
    <style>
    body {{
      font-family: monospace;
      margin: 0;
      padding: 20px;
      display: flex;
      justify-content: center;
      align-items: center;
      flex-direction: column;
      min-height: 100vh;
      background-color: #f2f2f2;
      font-size: 18px;
      width: 100%;
    }}
    .header {{
      background-color: #4CAF50;
      color: Black;
      padding: 10px;
      text-align: center;
      font-size: 30px;
      margin-bottom: 20px;
    }}
    .dropdown {{
      margin-bottom: 20px;
    }}
    select {{
      width: 100%;
      padding: 8px;
      font-size: 15px;
      font-family: Consolas;
    }}
    .content {{
      border: 1px solid #ccc;
      padding: 10px;
      overflow-y: auto;
    }}
    details {{
      margin: 5px 0;
    }}
    summary::before {{
      cursor: pointer;
      outline: none;
      user-select: none;
    }}
    summary::before {{
      content: "+ ";
      font-size: 25px;
      font-family: Consolas;
      color: green;
    }}
    details[open] > summary::before {{
      content: "- ";
      font-size: 25px;
      font-family: Consolas;
      color: red;
    }}
    .config {{
      white-space: pre-wrap;
      margin: 10px 0 0 20px;
      padding: 10px;
      font-size: 20px;
      font-family: Consolas;
      background: #f9f9f9;
      border-left: 2px solid #ddd;
    }}
    .collapse-all, .expand-all {{
      margin-bottom: 15px;
      padding: 8px;
      font-size: 20px;
      font-family: Consolas;
      background-color: green;
      color: white;
      border: none;
      cursor: pointer;
    }}

  </style>
</head>
<body>
  <div class="header">HPE Aruba Config Hierarchy</div>
  <div class="dropdown">
    <select id="apGroupSelect" onchange="updateContent()">
      <option value="">Select AP-Group</option>
"""

        # Add options for AP-Groups
        for ap_group in ap_groups:
            html += f'<option value="{ap_group}">{ap_group}</option>'

        html += """
    </select>
  </div>

  <div class="content">
    <div class="collapse-all">
      <button onclick="collapseAll()">Collapse All</button>
      <button onclick="expandAll()">Expand All</button>
    </div>

    <div id="apGroupContent"></div>
  </div>

  <script>
    const apGroups = """ + hierarchy_json + """;

    function updateContent() {
      const select = document.getElementById('apGroupSelect');
      const apGroupName = select.value;
      const contentDiv = document.getElementById('apGroupContent');
      contentDiv.innerHTML = '';
      
      if (apGroupName && apGroups[apGroupName]) {
        const hierarchy = apGroups[apGroupName];
        contentDiv.innerHTML = generateHierarchy(hierarchy);
      }
    }

    function generateHierarchy(hierarchy) {
      let html = '';
      if (hierarchy.config) {
        html += `<div class="config">${hierarchy.config}</div>`;
      }
      if (hierarchy.children) {
        for (let child in hierarchy.children) {
          html += `<details><summary>${child}</summary>${generateHierarchy(hierarchy.children[child])}</details>`;
        }
      }
      return html;
    }

    function collapseAll() {
      const details = document.querySelectorAll("details");
      details.forEach((detail) => detail.removeAttribute("open"));
    }

    function expandAll() {
      const details = document.querySelectorAll("details");
      details.forEach((detail) => detail.setAttribute("open", true));
    }
  </script>
</body>
</html>
"""
        with open(output_html, 'w', encoding='utf-8') as file:
            file.write(html)
        print(f"HTML output written to {output_html}")
    except Exception as e:
        print(f"Error generating HTML: {e}")

generate_html(ap_groups_hierarchy)