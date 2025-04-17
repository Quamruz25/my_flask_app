#!/usr/bin/env python3
# Location: /opt/my_flask_app/scripts/Bucket/script_bucket.py
"""
script_bucket.py
Usage: python3 script_bucket.py <input_file> <output_html> <log_file>
Processes the complete tech-support.log file and categorizes command blocks into predefined buckets.
Generates an HTML report preserving the original formatting.
"""

import re
import html
import os
import sys
import logging
from collections import defaultdict

# Define the bucket order and their corresponding "show" commands
bucket_order = [
    "show log", "show datapath", "show airgroup", "show ipc", "show gsm", "show ap", 
    "show license", "show crypto", "show threshold", "show ha", "show dpi", "show aaa", 
    "show iap", "show openflow", "show acl", "show memory", "show cpu", "show audit", 
    "show web-cc", "show dds", "show mgmt", "show sapm", "show websocket", "show est", 
    "show amon", "show switches", "show configuration", "show process", "show boot", 
    "show firewall", "show ip", "show igmp", "show ucc", "show wms", "show ipv6", 
    "show dns", "show allowlist", "show tpm", "show cpsec", "show dot1x", "show vpdn", 
    "show user", "show vrrp", "show ntp", "show tunneled-node", "show Layer2/3", 
    "show info", "show stm", "show wmm", "show snmp", "show wificalling", "show papi", 
    "show uplink", "show pan-gp", "show running"
]

buckets = {
    "show log": [
        "show log all | include mdns,ofa", "show log user-debug all", "show log user all",
        "show log system all", "show log security all", "show log errorlog all",
        "show uplink connection logs all"
    ],
    "show datapath": [
        "show datapath acl id 2700", "show datapath acl id 2701", "show datapath acl id 2702",
        "show datapath application counters", "show datapath bridge counters",
        "show datapath bridge table", "show datapath bwm table", "show datapath cp-bwm table",
        "show datapath crypto counters", "show datapath debug dma counters",
        "show datapath debug trace-buffer", "show datapath debug opcode",
        "show datapath dhcp router", "show datapath exception counters", "show datapath frame",
        "show datapath frame debug", "show datapath frame counters", "show datapath frame all",
        "show datapath frame spoofed-macs", "show datapath frame cpsp",
        "show datapath hardware counters", "show datapath hardware statistics",
        "show datapath ip-reassembly counters", "show datapath ipsec-map",
        "show datapath l3-interface", "show datapath lag table",
        "show datapath maintenance counters", "show datapath message-queue counters",
        "show datapath nat table", "show datapath papi counters", "show datapath port",
        "show datapath route counters", "show datapath route verbose",
        "show datapath route-cache counters", "show datapath route-cache verbose",
        "show datapath session counters", "show datapath session internal",
        "show datapath session high-value", "show datapath session perf",
        "show datapath session dhcp-perf", "show datapath session ipv6 verbose",
        "show datapath session ipv6 internal", "show datapath session ipv6 high-value",
        "show datapath session ipv6 perf", "show datapath session ipv6 dhcp-perf",
        "show datapath station table", "show datapath station crypto-counters",
        "show datapath tunnel counters", "show datapath tunnel verbose",
        "show datapath tunnel ipv6 verbose", "show datapath tunnel heartbeat",
        "show datapath tunnel-group", "show datapath user counters", "show datapath user table",
        "show datapath user ipv6", "show datapath remote-user counters",
        "show datapath remote-user table ipv4", "show datapath remote-user table ipv6",
        "show datapath utilization", "show datapath vlan table", "show datapath vlan-mcast table",
        "show datapath route ipv6", "show datapath tunnel ipv6", "show datapath exthdr",
        "show datapath route-cache ipv6", "show datapath scheduler table",
        "show datapath mobility home-agent-table", "show datapath mobility stats",
        "show datapath mobility mcast-table", "show datapath ip-mcast group",
        "show datapath ip-mcast station", "show datapath ip-mcast destination",
        "show datapath ipv6-mcast group", "show datapath ipv6-mcast destination",
        "show datapath ipv6-mcast station", "show datapath debug eap counters",
        "show datapath papi counters all", "show datapath papi remote-device-table counters",
        "show datapath papi remote-device-table", "show datapath papi remote-device-table ipv6",
        "show datapath ip-fragment-table", "show datapath network ingress",
        "show datapath internal dir nae file rx_free_fifo",
        "show datapath internal dir nae file rx_misc",
        "show datapath internal dir nae file tx_credit",
        "show datapath internal dir nae file tx_misc",
        "show datapath internal dir poe file enq_msg_ctrs",
        "show datapath internal dir poe file stats_n_dbg",
        "show datapath internal dir poe file class_drop_ctrs",
        "show datapath internal dir poe file ecc_1bit_errs",
        "show datapath internal dir poe file vec_drop_ctrs",
        "show datapath internal dir poe file err_regs",
        "show datapath internal dir int file pic_regs",
        "show datapath internal dir sae file error_status",
        "show datapath internal dir sae file msg_cnt",
        "show datapath internal dir sae file op_cnt",
        "show datapath internal dir sae file int_status",
        "show datapath openflow statistics", "show datapath openflow acl",
        "show datapath openflow acl-action-table", "show datapath acl id 4",
        "show datapath session | include O,IP", "show datapath session dpi | include O,IP",
        "show datapath session ipv6 | include O,IP", "show datapath session ipv6 dpi | include O,IP",
        "show datapath openflow auxiliary", "show datapath web-cc counters",
        "show datapath web-cc", "show datapath session web-cc",
        "show datapath session web-cc counters", "show datapath session ipv6 web-cc",
        "show datapath session ipv6 web-cc counters", "show datapath ip-reputation counters",
        "show datapath ip-geolocation counters", "show datapath session ip-classification",
        "show datapath compression", "show datapath internal dir sae file dbg_cnt",
        "show datapath tcp tunnel table", "show datapath tcp counters",
        "show datapath tcp app ssl counter"
    ],
    "show airgroup": [
        "show airgroupprofile", "show airgroupprofile activate", "show airgroupprofile cppm",
        "show airgroupprofile service", "show airgroupprofile domain",
        "show airgroup internal-state statistics verbose", "show airgroup aps",
        "show airgroup status", "show airgroup cache entries verbose",
        "show airgroup servers verbose", "show airgroup servers location unknown",
        "show airgroup servers location cluster", "show airgroup users verbose",
        "show airgroup vlan", "show airgroup cppm entries", "show airgroup cppm server-group",
        "show airgroup cppm-server radius statistics", "show airgroup cppm-server rfc3576 statistics",
        "show airgroup cppm-server query-interval", "show airgroup blocked-service-id",
        "show airgroup tracebuf", "show airgroupservice verbose",
        "show audit-trail | include airgroup", "show airgroup internal-state statistics ppm"
    ],
    "show ipc": [
        "show ipc statistics app-name ucm", "show ipc statistics app-name stm",
        "show ipc statistics app-name stm-lopri", "show ipc statistics app-name sapm",
        "show ipc statistics app-name authmgr", "show ipc statistics app-name snmp",
        "show ipc statistics app-name fpapps", "show ipc statistics app-name pdm",
        "show ipc statistics app-name licensemgr", "show ipc statistics app-name mdns"
    ],
    "show gsm": [
        "show gsm debug channel all status", "show gsm application all status",
        "show gsm debug channel ap", "show gsm application cluster_mgr memory",
        "show gsm application auth memory", "show gsm application tunneled_node_mgr memory",
        "show gsm debug channel cluster", "show gsm debug channel bucket_map",
        "show gsm debug channel sectun", "show gsm debug channel sta",
        "show gsm debug channel bss", "show gsm debug channel cluster_sta",
        "show gsm debug channel cluster_bss", "show gsm debug channel cluster_ap",
        "show gsm debug channel cluster_aac", "show gsm debug channel rep_key",
        "show gsm debug channel remote_ip_user", "show gsm debug channel dds_peer",
        "show gsm debug channel radio", "show gsm lookup channel rep_key key rep_key 5",
        "show gsm debug channel web_cc_info", "show gsm debug channel mac_user",
        "show gsm debug channel mac_user metadata", "show gsm debug channel user",
        "show gsm debug channel user metadata", "show gsm debug channel ip_user",
        "show gsm debug channel ip_user metadata", "show gsm debug channel tunneled_node",
        "show gsm debug channel tunneled_node metadata", "show gsm debug channel tunneled_user",
        "show gsm debug channel tunneled_user metadata"
    ],
    "show ap": [
        "show ap global acl-table", "show ap database long", "show ap database-summary",
        "show ap bss-table", "show ap radio-summary", "show ap debug counters",
        "show ap debug client-mgmt-counters", "show ap debug sta-msg-stats",
        "show ap debug gsm-counters", "show ap essid", "show ap active",
        "show ap spectrum monitors", "show ap mesh active", "show ap mesh topology long",
        "show ap association", "show ap image version", "show ap regulatory",
        "show ap wmm-flow", "show ap license-usage", "show ap vlan-usage",
        "show ap arm state", "show ap active voip-only", "show ap arm client-match summary advanced",
        "show ap arm client-match history", "show ap arm client-match unsupported",
        "show ap arm client-match pending", "show ap arm client-match msg-stats",
        "show ap image-preload status all", "show ap debug cluster-node-state verbose",
        "show ap debug bucketmap-state verbose", "show ap debug bucketmap-state uac dormant verbose",
        "show ap debug cluster-counters", "show ap analytics recommendations radio-setting database all",
        "show ap analytics recommendations radio-setting running all",
        "show ap analytics recommendations ap-setting database all",
        "show ap analytics recommendations ap-setting running all",
        "show ap analytics recommendations stats all", "show ap greenap amon pending-ap",
        "show ap greenap counters", "show ap greenap request pending-ap all",
        "show ap thermal amon pending-ap", "show stm perf-history"
    ],
    "show license": [
        "show license verbose", "show license aggregate", "show keys all",
        "show license-usage client verbose - This command is applicable only on the license server",
        "show license heartbeat stats", "show license server-table", "show license client-table",
        "show license-usage client", "show license-usage web-cc", "show license debug",
        "show license limits", "show license debug feature-bits", "show license-pool-profile-root",
        "show license-pool-profile", "show license debug auth-feature-bits", "show ap license-usage"
    ],
    "show crypto": [
        "show datapath crypto counters", "show datapath station crypto-counters", "show crypto dp",
        "show crypto dynamic-map", "show crypto ipsec sa", "show crypto ipsec sa summary",
        "show crypto ipsec transform-set", "show crypto isakmp groupname", "show crypto isakmp key",
        "show crypto isakmp policy", "show crypto isakmp sa", "show crypto isakmp sa summary",
        "show crypto isakmp stats", "show crypto isakmp vlan", "show crypto map",
        "show crypto-local isakmp ca-certificate", "show crypto-local isakmp certificate-group",
        "show crypto-local isakmp server-certificate", "show crypto-local isakmp dpd",
        "show crypto-local pki CRL", "show crypto-local pki TrustedCA",
        "show crypto-local pki service-ocsp-responder", "show crypto-local pki ocsp-client-stats",
        "show crypto-local pki OCSPResponderCert", "show crypto-local pki OCSPSignerCert",
        "show crypto-local pki rcp", "show crypto-local pki PublicCert",
        "show crypto-local pki ServerCert", "show crypto pki CRL", "show crypto pki TrustedCA",
        "show crypto pki OCSPResponderCert", "show crypto pki OCSPSignerCert",
        "show crypto pki PublicCert", "show crypto pki ServerCert", "show crypto-local isakmp ppk"
    ],
    "show threshold": [
        "show threshold-limits controlpath-memory", "show threshold-limits no-of-aps",
        "show threshold-limits no-of-locals", "show threshold-limits user-capacity",
        "show threshold-limits total-tunnel-capacity"
    ],
    "show ha": [
        "show ha group-profile", "show ha group-membership", "show ha ap table",
        "show ha heartbeat counters"
    ],
    "show dpi": [
        "show datapath session dpi | include O,IP", "show datapath session ipv6 dpi | include O,IP",
        "show dpi custom-app all", "show dpi application all", "show dpi application custom-app all",
        "show dpi application category all", "show dpi application category user-defined all"
    ],
    "show aaa": [
        "show auth-tracebuf", "show aaa authentication downloaded-cp-profiles",
        "show aaa authentication all", "show aaa authentication-server all",
        "show aaa authentication-server radius statistics",
        "show aaa authentication-server tacacs statistics",
        "show aaa authentication-server ldap statistics",
        "show aaa authentication-server radsec-status-all", "show aaa bandwidth-contracts",
        "show aaa radius-attributes", "show aaa authentication-server internal statistics",
        "show aaa derivation-rules server-group", "show aaa derivation-rules user",
        "show aaa server-group summary", "show aaa authentication captive-portal customization",
        "show aaa state configuration", "show aaa state messages", "show aaa state ap-group",
        "show aaa authentication vpn", "show aaa authentication vpn default",
        "show aaa authentication vpn default-cap", "show aaa authentication vpn default-rap",
        "show aaa authentication vpn default-iap", "show aaa state debug-statistics",
        "show aaa fqdn-server-names", "show aaa authentication dot1x", "show aaa auth-survivability",
        "show aaa auth-survivability-cache"
    ],
    "show iap": [
        "show aaa authentication vpn default-iap", "show iap trusted-branch-db",
        "show iap detailed-table", "show iap table long", "show iap statistics",
        "show iap subnets-summary"
    ],
    "show openflow": [
        "show openflow-profile", "show openflow capabilities", "show openflow controller",
        "show openflow ports", "show openflow statistics", "show openflow debug event",
        "show openflow debug ports", "show openflow debug flows",
        "show openflow debug ap-client state detail", "show openflow flow-table",
        "show openflow flows statistics", "show datapath openflow statistics",
        "show datapath openflow acl", "show datapath openflow acl-action-table",
        "show datapath openflow auxiliary"
    ],
    "show acl": [
        "show datapath acl id 2700", "show datapath acl id 2701", "show datapath acl id 2702",
        "show rights", "show rights downloaded-user-roles", "show acl hits",
        "show acl acl-table", "show acl ace-table all", "show ap global acl-table",
        "show datapath openflow acl", "show datapath openflow acl-action-table",
        "show acl ace-table acl 4", "show datapath acl id 4", "show netdestination",
        "show policy-domain group-profile"
    ],
    "show memory": [
        "show memory", "show storage", "show memory ecc", "show memory debug",
        "show memory cluster_mgr", "show memory auth", "show threshold-limits controlpath-memory",
        "show gsm application cluster_mgr memory", "show gsm application auth memory",
        "show gsm application tunneled_node_mgr memory", "show memory ofa",
        "show memory mdns", "show disk-health", "show usb"
    ],
    "show cpu": [
        "show cpuload", "show cpuload current", "show iostat"
    ],
    "show audit": [
        "show audit-trail history", "show audit-trail", "show audit-trail | include airgroup"
    ],
    "show web-cc": [
        "show web-cc stats", "show web-cc status", "show license-usage web-cc",
        "show datapath web-cc counters", "show datapath web-cc", "show datapath session web-cc",
        "show datapath session web-cc counters", "show datapath session ipv6 web-cc",
        "show datapath session ipv6 web-cc counters", "show web-cc global-bandwidth-contract all"
    ],
    "show dds": [
        "show dds debug rkey", "show dds debug stats", "show dds debug peers"
    ],
    "show mgmt": [
        "show interface mgmt", "show mgmt-server message-counters process stm",
        "show mgmt-server message-counters process tm"
    ],
    "show sapm": [
        "show ipc statistics app-name sapm", "show sapm cluster nodestate verbose",
        "show sapm-bucketmap", "show sapm-debug", "show sapm netdest active",
        "show sapm statistics papi-messages", "show sapm statistics sap-messages"
    ],
    "show websocket": [
        "show websocket clearpass", "show websocket debug clearpass",
        "show websocket state clearpass", "show websocket statistics clearpass"
    ],
    "show est": [
        "show est status", "show est status all"
    ],
    "show amon": [
        "show amon msg-buffer-size", "show amon source-interface",
        "show ap greenap amon pending-ap", "show ap thermal amon pending-ap"
    ],
    "show switches": [
        "show switch ip", "show switches", "show switches debug", "show switches regulatory",
        "show cluster-switches", "show conductor-local stats", "show conductor-redundancy"
    ],
    "show configuration": [
        "show boot", "show switches", "show switches debug", "show configuration failure",
        "show configuration failure all", "show aaa state configuration",
        "show vpdn l2tp configuration", "show vpdn pptp configuration",
        "show bulkedit configuration"
    ],
    "show process": [
        "show processes", "show process monitor statistics", "show process fpapps task-stats",
        "show process fpapps message-queue-stats", "show process fpapps timer-stats",
        "show mgmt-server message-counters process stm", "show mgmt-server message-counters process tm"
    ],
    "show boot": [
        "show version", "show image version", "show boot", "show boot history",
        "show boot upgrade-history", "show audit-trail history", "show audit-trail",
        "show crashinfo"
    ],
    "show firewall": [
        "show firewall", "show firewall-cp", "show firewall-cp internal", "show ipv6 firewall"
    ],
    "show ip": [
        "show switch ip", "show datapath ip-reassembly counters", "show ip access-list brief",
        "show ip nexthop-list", "show ip interface brief", "show ip health-check verbose",
        "show ip route", "show ip route stats", "show ip route counters", "show ip ospf",
        "show ip ospf interface", "show ip ospf neighbor", "show ip ospf database",
        "show ip ospf debug route", "show ip ospf subnet", "show ip ospf redistribute",
        "show ip ospf rapng-vpn aggregate-routes", "show ip ospf static aggregate-routes",
        "show ip mobile global", "show ip mobile domain", "show ip mobile active-domains",
        "show ip mobile hat", "show ip mobile host", "show ip mobile visitor",
        "show ip mobile binding", "show ip mobile tunnel", "show ip mobile traffic",
        "show ip dhcp option-82", "show ip dhcp vlan", "show ip dhcp database",
        "show ip dhcp statistics", "show ip dhcp binding failover-peer", "show ip dhcp binding",
        "show ip dhcp reserved", "show ip dhcp relay counters", "show ip radius source-interface",
        "show ip igmp config", "show ip igmp interface", "show ip igmp group",
        "show ip igmp proxy-group", "show ip igmp proxy-mobility-group", "show ip igmp counters",
        "show ip igmp proxy-stats", "show ip igmp proxy-mobility-stats",
        "show ip igmp cluster proxy-group", "show ip igmp cluster info",
        "show ip igmp cluster client-info", "show ip igmp cluster bss-info",
        "show ip igmp cluster aac-info", "show ip igmp cluster dmo-off-info",
        "show ip igmp cluster stats", "show ip mobile multicast-vlan-table"
    ],
    "show igmp": [
        "show ip igmp config", "show ip igmp interface", "show ip igmp group",
        "show ip igmp proxy-group", "show ip igmp proxy-mobility-group", "show ip igmp counters",
        "show ip igmp proxy-stats", "show ip igmp proxy-mobility-stats",
        "show ip igmp cluster proxy-group", "show ip igmp cluster info",
        "show ip igmp cluster client-info", "show ip igmp cluster bss-info",
        "show ip igmp cluster aac-info", "show ip igmp cluster dmo-off-info",
        "show ip igmp cluster stats"
    ],
    "show ucc": [
        "show ucc call-info cdrs", "show ucc call-info cdrs detail", "show ucc client-info",
        "show ucc client-info detail", "show ucc trace-buffer sip", "show ucc trace-buffer sccp",
        "show ucc trace-buffer skype4b", "show ucc statistics counter call global",
        "show ucc statistics counter call client", "show ucc internal-state",
        "show ucc facetime", "show ucc h323", "show ucc ich", "show ucc jabber",
        "show ucc noe", "show ucc sccp", "show ucc sip", "show ucc skype4b",
        "show ucc vocera", "show ucc wificalling", "show ucc webrtc", "show ucc teams",
        "show ucc dns-ip-learning", "show ucc trace-buffer jabber", "show ucc rtpa-config",
        "show ucc rtpa-report", "show ucc session-idle-timeout", "show ucc dns-ip-learning"
    ],
    "show wms": [
        "show wms general", "show wms system", "show wms counters"
    ],
    "show ipv6": [
        "show datapath session ipv6 verbose", "show datapath session ipv6 internal",
        "show datapath session ipv6 high-value", "show datapath session ipv6 perf",
        "show datapath session ipv6 dhcp-perf", "show datapath tunnel ipv6 verbose",
        "show datapath user ipv6", "show datapath remote-user table ipv6",
        "show datapath route ipv6", "show datapath tunnel ipv6", "show datapath route-cache ipv6",
        "show ipv6 global", "show ipv6 firewall", "show ipv6 nexthop-list",
        "show ipv6 dhcp database", "show ipv6 dhcp binding", "show ipv6 dhcp relay-option",
        "show ipv6 dhcp vlan", "show ipv6 dhcp helper", "show ipv6 dhcp-client",
        "show ipv6 dhcp relay counters", "show ipv6 pd status", "show ipv6 ra status",
        "show ipv6 ra proxy", "show ipv6 mld config", "show ipv6 mld interface",
        "show ipv6 mld group", "show ipv6 mld proxy-group", "show ipv6 mld proxy-mobility-group",
        "show ipv6 mld counters", "show ipv6 mld proxy-stats", "show ipv6 mld proxy-mobility-stats",
        "show datapath ipv6-mcast group", "show datapath ipv6-mcast destination",
        "show datapath ipv6-mcast station", "show ipv6 mld cluster proxy-group",
        "show ipv6 mld cluster dmo-off-info", "show ipv6 interface", "show ipv6 interface brief",
        "show ipv6 route", "show ipv6 neighbors", "show ipv6 netlink stats",
        "show vrrp ipv6", "show vrrp ipv6 stats all", "show datapath papi remote-device-table ipv6",
        "show datapath session ipv6 | include O,IP", "show datapath session ipv6 dpi | include O,IP",
        "show datapath session ipv6 web-cc", "show datapath session ipv6 web-cc counters"
    ],
    "show dns": [
        "ip domain lookup", "ip name-server 10.5.110.231", "ip name-server 10.5.110.232"
    ],
    "show allowlist": [
        "show allowlist-db cpsec-status", "show allowlist-db cpsec", "show allowlist-db rap-status",
        "show allowlist-db rap long", "show allowlist-db seq-pendlist"
    ],
    "show tpm": [
        "show tpm cert-info", "show tpm errorlog"
    ],
    "show cpsec": [
        "show allowlist-db cpsec-status", "show allowlist-db cpsec", "show control-plane-security",
        "show cp-stats", "show cp-bwcontracts"
    ],
    "show dot1x": [
        "show dot1x ap-table", "show dot1x supplicant-info list-all",
        "show dot1x supplicant-info statistics", "show dot1x machine-auth-cache",
        "show dot1x counters", "show dot1x watermark history", "show dot1x watermark table active",
        "show dot1x watermark table pending", "show aaa authentication dot1x",
        "show dot1x certificates details", "show auth-tracebuf"
    ],
    "show vpdn": [
        "show vpdn l2tp configuration", "show vpdn l2tp local pool", "show vpdn pptp configuration",
        "show vpdn pptp local pool", "show vpdn tunnel l2tp", "show vpn-dialer"
    ],
    "show user": [
        "show datapath user counters", "show datapath user table", "show datapath user ipv6",
        "show threshold-limits user-capacity", "show datapath remote-user counters",
        "show datapath remote-user table ipv4", "show datapath remote-user table ipv6",
        "show rights downloaded-user-roles", "show aaa derivation-rules user",
        "show station-table", "show user-table", "show user-table verbose", "show rights",
        "show log user-debug all", "show log user all", "show auth-tracebuf",
        "show policy-domain group-profile"
    ],
    "show vrrp": [
        "show vrrp", "show vrrp stats all", "show vrrp ipv6", "show vrrp ipv6 stats all"
    ],
    "show ntp": [
        "show ntp authentication-keys", "show ntp servers", "show ntp status",
        "show ntp trusted-keys"
    ],
    "show tunneled-node": [
        "show tunneled-node config", "show tunneled-node state"
    ],
    "show Layer2/3": [
        "show spanning-tree", "show spantree", "show trunk", "show interface",
        "show lacp summary", "show vrrp", "show interface mgmt", "show interface vlan 1",
        "show datapath l3-interface", "show ip interface brief", "show interface loopback",
        "show interface tunnel", "show interface counters", "show vlan",
        "show vlan mapping", "show vlan-assignment", "show mac-address-table",
        "show arp", "show gap-debug"
    ],
    "show info": [
        "show syslocation", "show loginsessions", "show ssh", "show roleinfo",
        "show version", "show image version", "show ca-bundle version", "show country",
        "show country trail", "show inventory", "show alarms summary", "show alarms",
        "show slots", "show gap-debug", "show crashinfo", "show local-userdb",
        "show database synchronize", "show profile-errors", "show fake_ade_cnt",
        "show netexthdr default", "show netstat stats"
    ],
    "show stm": [
        "show stm perf-history", "show ipc statistics app-name stm",
        "show ipc statistics app-name stm-lopri", "show mgmt-server message-counters process stm"
    ],
    "show wmm": [
        "show ap wmm-flow", "show wmm tspec-statistics"
    ],
    "show snmp": [
        "show snmp inform stats", "show ipc statistics app-name snmp"
    ],
    "show wificalling": [
        "show ucc wificalling", "show voice wificalling"
    ],
    "show papi": [
        "show datapath papi counters", "show papi kernel-socket-stats",
        "show datapath papi counters all", "show datapath papi remote-device-table counters",
        "show datapath papi remote-device-table", "show datapath papi remote-device-table ipv6",
        "show sapm statistics papi-messages"
    ],
    "show uplink": [
        "show uplink", "show uplink signal", "show uplink connection logs all"
    ],
    "show pan-gp": [
        "show pan-gp portal-info", "show pan-gp gateway-info"
    ],
    "show running": [
        "show running-config"
    ]
}

# Create a mapping from commands to buckets
command_to_bucket = {}
for bucket in bucket_order:
    for command in buckets[bucket]:
        command_to_bucket[command] = bucket

# Function to slugify bucket names for HTML IDs
def slugify(name):
    return re.sub(r'\W+', '-', name).lower()

# Function to parse the log file into blocks
def parse_log_file(file_path):
    blocks = []
    current_block = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith("show "):
                if current_block:  # If there's an existing block, append it
                    blocks.append(current_block)
                current_block = [line]  # Start a new block
            else:
                current_block.append(line)  # Add line to current block
        if current_block:  # Append the last block
            blocks.append(current_block)
    return blocks

# Function to generate the HTML content
def generate_html(bucket_to_blocks, bucket_order):
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>HPE ArubaOS Tech-Support Analyzer</title>
    <style>
        body { background-color: #f5f5f5; }
        .bucket { display: none; }
        .command-output { display: none; margin: 5px 0 0 0; padding: 5px; font-size: 14px; }
        .command-output.expanded { display: block; background-color: #e0e0e0; }
        .toggle-btn { background: none; border: none; font-size: 18px; cursor: pointer; margin-right: 10px; }
        .heading { display: inline-block; border: 12px solid green; padding: 2px 10px; }
        .heading h1 { font-size: 24px; margin: 0; }
        #bucket-search { font-size: 16px; padding: 5px; width: 300px; margin-bottom: 5px; }
        #bucket-select { font-size: 16px; padding: 5px; width: 300px; }
        pre { background: #f4f4f4; padding: 5px; border: 1px solid #ddd; margin: 0; }
        h3 { margin: 0; display: inline; }
        .command-header { margin-bottom: 5px; display: flex; align-items: center; }
        .button-container { width: 300px; margin: 5px auto 0; display: flex; justify-content: space-between; }
        .button-container button { font-size: 16px; padding: 5px; width: 145px; }
        .font-size-container { width: 300px; margin: 5px auto; text-align: center; }
    </style>
    <script>
        function showBucket(bucketId) {
            var buckets = document.querySelectorAll('.bucket');
            buckets.forEach(function(b) { b.style.display = 'none'; });
            if (bucketId) { document.getElementById(bucketId).style.display = 'block'; }
        }

        function toggleOutput(button) {
            var output = button.parentElement.nextElementSibling;
            if (output.classList.contains('expanded')) {
                output.classList.remove('expanded');
                button.textContent = '+';
                button.style.color = 'green';
            } else {
                output.classList.add('expanded');
                button.textContent = '-';
                button.style.color = 'red';
            }
        }

        function collapseAll() {
            var bucketId = document.getElementById('bucket-select').value;
            if (bucketId) {
                var bucket = document.getElementById(bucketId);
                var outputs = bucket.querySelectorAll('.command-output');
                outputs.forEach(function(output) { output.classList.remove('expanded'); });
                var buttons = bucket.querySelectorAll('.toggle-btn');
                buttons.forEach(function(button) { 
                    button.textContent = '+'; 
                    button.style.color = 'green'; 
                });
            }
        }

        function expandAll() {
            var bucketId = document.getElementById('bucket-select').value;
            if (bucketId) {
                var bucket = document.getElementById(bucketId);
                var outputs = bucket.querySelectorAll('.command-output');
                outputs.forEach(function(output) { output.classList.add('expanded'); });
                var buttons = bucket.querySelectorAll('.toggle-btn');
                buttons.forEach(function(button) { 
                    button.textContent = '-'; 
                    button.style.color = 'red'; 
                });
            }
        }

        document.addEventListener('DOMContentLoaded', function() {
            var searchInput = document.getElementById('bucket-search');
            var select = document.getElementById('bucket-select');
            
            searchInput.addEventListener('input', function() {
                var filter = searchInput.value.toLowerCase();
                var options = select.options;
                for (var i = 1; i < options.length; i++) {
                    var option = options[i];
                    if (option.text.toLowerCase().includes(filter)) {
                        option.style.display = '';
                    } else {
                        option.style.display = 'none';
                    }
                }
            });
        });

        function adjustFontSize() {
            var slider = document.getElementById('font-size-slider');
            var outputs = document.querySelectorAll('.command-output');
            outputs.forEach(function(output) {
                output.style.fontSize = slider.value + 'px';
            });
        }
    </script>
</head>
<body>
    <!-- Centered Heading -->
    <div style="text-align: center;">
        <div class="heading">
            <h1>HPE ArubaOS Tech-Support Analyzer</h1>
        </div>
    </div>

    <!-- Dropdown and Buttons -->
    <div style="text-align: center; margin-top: 10px;">
        <input type="text" id="bucket-search" placeholder="Search buckets...">
        <select id="bucket-select" onclick="this.size=1;" onchange="showBucket(this.value)">
            <option value="">Select a bucket</option>
"""
    # Add dropdown options
    for bucket in bucket_order:
        slug = slugify(bucket)
        html_content += f'            <option value="{slug}">{html.escape(bucket)}</option>\n'

    html_content += """
        </select>
        <div class="button-container">
            <button onclick="collapseAll()">Collapse All</button>
            <button onclick="expandAll()">Expand All</button>
        </div>
        <div class="font-size-container">
            <label for="font-size-slider">Adjust Show Command Font Size:</label>
            <input type="range" id="font-size-slider" min="12" max="24" value="14" oninput="adjustFontSize()">
        </div>
    </div>
"""

    # Add bucket sections without bucket name
    for bucket in bucket_order:
        slug = slugify(bucket)
        html_content += f'    <div id="{slug}" class="bucket">\n'
        for block in bucket_to_blocks[bucket]:
            command = block[0].rstrip()
            output = ''.join(block[1:])
            html_content += '        <div class="command">\n'
            html_content += '            <div class="command-header">\n'
            html_content += '                <button class="toggle-btn" onclick="toggleOutput(this)" style="color: green;">+</button>\n'
            html_content += f'                <h3>{html.escape(command)}</h3>\n'
            html_content += '            </div>\n'
            html_content += f'            <pre class="command-output">{html.escape(output)}</pre>\n'
            html_content += '        </div>\n'
        html_content += '    </div>\n'

    html_content += """
</body>
</html>
"""
    return html_content

# Main execution
def main():
    if len(sys.argv) < 4:
        print("Usage: python3 script_bucket.py <input_file> <output_html> <log_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_html = sys.argv[2]
    log_file = sys.argv[3]

    # Set up logging
    logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("Bucket script started.")

    # Check if the input file exists
    if not os.path.exists(input_file):
        logger.error(f"The input file does not exist at: {input_file}")
        sys.exit(f"The input file does not exist at: {input_file}")
    
    # Create the output directory if it doesn't exist
    output_dir = os.path.dirname(output_html)
    os.makedirs(output_dir, exist_ok=True)
    
    # Parse the log file
    blocks = parse_log_file(input_file)
    
    # Categorize blocks into buckets with dynamic matching for 'show datapath <string>'
    bucket_to_blocks = defaultdict(list)
    for block in blocks:
        command = block[0].rstrip()
        bucket = command_to_bucket.get(command)
        if not bucket:
            # Dynamically match 'show datapath' commands
            if command.startswith("show datapath "):
                bucket = "show datapath"
        if bucket:
            bucket_to_blocks[bucket].append(block)
    
    # Generate and write HTML
    html_content = generate_html(bucket_to_blocks, bucket_order)
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info(f"HTML file generated at: {output_html}")
    print(f"HTML file generated at: {output_html}")

if __name__ == "__main__":
    main()