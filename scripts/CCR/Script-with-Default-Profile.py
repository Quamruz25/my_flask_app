#!/usr/bin/env python3
# Location: /opt/my_flask_app/scripts/CCR/Script-with-Default-Profile.py
import os
import re
import logging
import sys
from collections import defaultdict

if len(sys.argv) < 4:
    print("Usage: python3 Script-with-Default-Profile.py <input_file> <output_file> <log_file>")
    sys.exit(1)

input_file_path = sys.argv[1]
output_file_path = sys.argv[2]
log_file_path = sys.argv[3]

logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(console_handler)
logger = logging.getLogger(__name__)

logger.info("CCR Script with Default Profile started...")

if not os.path.exists(input_file_path):
    logger.error(f"Input file not found: {input_file_path}")
    print(f"Error: Input file not found: {input_file_path}")
    sys.exit(1)

# Precompile regex patterns for keywords
keywords = [
   "ip access-list geolocation", "ip access-list eth", "netdestination", "aaa bandwidth-contract",
    "ip access-list session", "user-role", "vlan-name", "ip nexthop-list", "crypto isakmp policy",
    "mgmt-server primary-server", "ntp server", "cp-bandwidth-contract", "aaa rfc-3576-server",
    "aaa authentication mac", "aaa authentication dot1x", "aaa authentication-server ldap",
    "aaa authentication-server tacacs", "aaa authentication-server radius", "scheduler-profile",
    "aaa server-group", "aaa profile", "aaa authentication captive-portal", "aaa authentication wispr",
    "aaa authentication vpn", "aaa authentication stateful-ntlm", "aaa authentication stateful-kerberos",
    "aaa authentication via auth-profile", "aaa authentication via connection-profile",
    "aaa authentication via web-auth", "ids ap-classification-rule", "ids management-profile",
    "ids wms-general-profile", "ids wms-local-system-profile", "ucc", "lc-cluster group-profile",
    "ap regulatory-domain-profile", "dump-auto-uploading-profile", "ap wired-ap-profile",
    "ap enet-link-profile", "ap mesh-ht-ssid-profile", "ap lldp med-network-policy-profile",
    "ap mesh-cluster-profile", "ap mesh-accesslist-profile", "ap wifi-uplink-profile",
    "ap multizone-profile", "ap usb-acl-prof", "iot radio-profile", "dump-collection-profile",
    "ap lldp profile", "ap mesh-radio-profile", "ap usb-profile", "ap system-profile",
    "ap wired-port-profile", "gps service-profile", "ids general-profile", "ids rate-thresholds-profile",
    "ids signature-profile", "ids impersonation-profile", "ids unauthorized-device-profile",
    "ids signature-matching-profile", "ids dos-profile", "ids profile", "rf dot11-60GHz-radio-profile",
    "wlan 6ghz-rrm-ie-profile", "rf arm-profile", "rf ht-radio-profile", "rf spectrum-profile",
    "rf optimization-profile", "rf event-thresholds-profile", "rf am-scan-profile",
    "rf dot11a-radio-profile", "rf dot11g-radio-profile", "rf dot11-6GHz-radio-profile",
    "wlan rrm-ie-profile", "wlan bcn-rpt-req-profile", "wlan dot11r-profile", "wlan tsm-req-profile",
    "wlan ht-ssid-profile", "wlan he-ssid-profile", "wlan hotspot anqp-venue-name-profile",
    "wlan hotspot anqp-nwk-auth-profile", "wlan hotspot anqp-roam-cons-profile",
    "wlan hotspot anqp-nai-realm-profile", "wlan hotspot anqp-3gpp-nwk-profile",
    "wlan hotspot h2qp-operator-friendly-name-profile", "wlan hotspot h2qp-wan-metrics-profile",
    "wlan hotspot h2qp-conn-capability-profile", "wlan hotspot h2qp-op-cl-profile",
    "wlan hotspot h2qp-osu-prov-list-profile", "wlan hotspot anqp-ip-addr-avail-profile",
    "wlan hotspot anqp-domain-name-profile", "wlan edca-parameters-profile station",
    "wlan edca-parameters-profile ap", "wlan mu-edca-parameters-profile", "wlan dot11k-profile",
    "wlan ssid-profile", "wlan virtual-ap", "wlan traffic-management-profile", "mgmt-server profile",
    "ap authorization-profile", "ap provisioning-profile", "rf arm-rf-domain-profile",
    "ap am-filter-profile", "ap spectrum local-override", "airmatch profile", "ap-lacp-striping-ip",
    "ap general-profile", "ap deploy-profile", "airslice-profile", "ap-group", "ap-name",
    "airgroupprofile service", "iot transportProfile", "iot useTransportProfile",
    "snmp-server host", "ip probe" 
]
keyword_patterns = [(keyword, re.compile(rf"\b{re.escape(keyword)}\b\s+(?:\"([^\"]+)\"|(\S+))")) for keyword in keywords]
word_count_pattern = re.compile(r'\b\w+\b')  # Pattern to extract words for counting

# Step 1: Read file and build word counts in one pass
word_counts = defaultdict(int)
lines = []
with open(input_file_path, "r", encoding="utf-8") as file:
    for line in file:
        lines.append(line)
        # Count occurrences of each word in the line
        words = word_count_pattern.findall(line)
        for word in words:
            word_counts[word] += 1

# Step 2: Process lines for keyword matches
results = []
for line in lines:
    for keyword, pattern in keyword_patterns:
        match = pattern.search(line)
        if match:
            next_word = match.group(1) if match.group(1) else match.group(2)
            match_count = word_counts.get(next_word, 0)
            found_status = "YES" if match_count >= 2 else "NO"
            results.append((keyword, next_word, found_status))

# Step 3: VRRP matching
vrrp_numbers = set()
virtual_router_numbers = set()
for line in lines:
    if line.startswith("vrrp"):
        match = re.match(r"^vrrp (\d+)", line)
        if match:
            vrrp_numbers.add(match.group(1))
    if line.startswith("Virtual Router"):
        match = re.match(r"^Virtual Router (\d+)", line)
        if match:
            virtual_router_numbers.add(match.group(1))

vrrp_results = []
for vrrp_num in vrrp_numbers:
    match_found = "YES" if vrrp_num in virtual_router_numbers else "NO"
    vrrp_results.append((f"vrrp {vrrp_num}", match_found))

# Step 4: Generate HTML output
logger.info("Generating HTML output...")
html_content = ["""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HPE Aruba Config Cleanup Review</title>
    <style>
        body { font-family: Calibri, sans-serif; margin: 0; padding: 0px; display: flex; justify-content: center; align-items: center; flex-direction: column; min-height: 100vh; background-color: #f2f2f2; font-size: 18px; width: 100%; }
        .box { border: 10px solid green; color: black; padding: 15px 25px; border-radius: 2px; font-size: 30px; font-weight: bold; text-align: center; margin-top: 10px; width: 90%; max-width: 600px; }
        .found { color: green; font-weight: bold; }
        .not-found { color: red; }
        table { border-collapse: collapse; width: auto; margin: 20px; table-layout: auto; }
        th, td { border: 1px solid black; padding: 5px; text-align: center; word-wrap: break-word; }
        th { background-color: #FBE2D5; }
    </style>
</head>
<body>
    <div class="box">HPE Aruba Config Cleanup Review</div>
    <div style="height: 15px;"></div>
    <div class="info">This report is for the customer's review and action. HPE/Aruba Support is providing information on the usage status of configuration profiles.</div>
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

logger.info("HTML report generated at: {}".format(output_file_path))
print("HTML report generated successfully at: {}".format(output_file_path))