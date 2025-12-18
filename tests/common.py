from copy import deepcopy

from aioasuswrt.structure import new_device

# pylint: skip-file
RX_DATA = ["2703926881", ""]
TX_DATA = ["648110137", ""]
RX = 2703926881
TX = 648110137
TEMP_DATA = [
    ["59 (0x3b)\r"],
    ["69 (0x45)\r"],
    ["CPU temperature	: 77"],
    ["59 (0x3b)\r"],
    ["69 (0x45)\r"],
    ["CPU temperature	: 77"],
]
TEMP_DATA_2ND = [[""], [""], [""], [""], [""], ["81300"], ["81300"]]
NETDEV_DATA = [
    "nter-|   Receive                                                |  Transmit",
    " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed",
    "    lo: 129406077  639166    0    0    0     0          0         0 129406077  639166    0    0    0     0       0          0",
    "  ifb0:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0",
    "  ifb1:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0",
    "  fwd0:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0",
    "  fwd1:       0 32991574    0    0    0     0          0         0 2758131447 21323444    0    0    0     0       0          0",
    "   agg:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0",
    "  eth0: 1376394855 180111514    0    0    0     0          0         0 896208608 161258260    0    0    0     0       0          0",
    " dpsta:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0",
    "  eth1: 240050447 1451957    0    0    0     0          0     47377 2112087504 43036729    0 26277918    0     0       0          0",
    "  eth2:       0       0    0    0    0     0          0         0 3283428721 33007901    0    2    0     0       0          0",
    " vlan1: 72308780 80394316    0    0    0     0          0     91875 102404809 53006688    0    0    0     0       0          0",
    " vlan2:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0",
    "   br0: 4643330713 15198823    0    0    0     0          0         0 5699827990 13109400    0    0    0     0       0          0",
    " wl0.1: 72308780  385338    0    0    0     0          0      7706 311596615 4150488    0 199907    0     0       0          0",
    "ds0.1:       0       0    0    0    0     0          0         0 102404809  805208    0    0    0     0       0          0",
    " tun21:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0",
]
INTERFACES = [
    (
        "lo",
        {
            "rx_bytes": 129406077,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 0,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 639166,
            "tx_bytes": 129406077,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 0,
            "tx_packets": 639166,
        },
    ),
    (
        "ifb0",
        {
            "rx_bytes": 0,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 0,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 0,
            "tx_bytes": 0,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 0,
            "tx_packets": 0,
        },
    ),
    (
        "ifb1",
        {
            "rx_bytes": 0,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 0,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 0,
            "tx_bytes": 0,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 0,
            "tx_packets": 0,
        },
    ),
    (
        "fwd0",
        {
            "rx_bytes": 0,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 0,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 0,
            "tx_bytes": 0,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 0,
            "tx_packets": 0,
        },
    ),
    (
        "fwd1",
        {
            "rx_bytes": 2758131447,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 0,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 21323444,
            "tx_bytes": 0,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 0,
            "tx_packets": 32991574,
        },
    ),
    (
        "agg",
        {
            "rx_bytes": 0,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 0,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 0,
            "tx_bytes": 0,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 0,
            "tx_packets": 0,
        },
    ),
    (
        "eth0",
        {
            "rx_bytes": 896208608,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 0,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 161258260,
            "tx_bytes": 1376394855,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 0,
            "tx_packets": 180111514,
        },
    ),
    (
        "dpsta",
        {
            "rx_bytes": 0,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 0,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 0,
            "tx_bytes": 0,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 0,
            "tx_packets": 0,
        },
    ),
    (
        "eth1",
        {
            "rx_bytes": 2112087504,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 26277918,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 43036729,
            "tx_bytes": 240050447,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 47377,
            "tx_packets": 1451957,
        },
    ),
    (
        "eth2",
        {
            "rx_bytes": 3283428721,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 2,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 33007901,
            "tx_bytes": 0,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 0,
            "tx_packets": 0,
        },
    ),
    (
        "vlan1",
        {
            "rx_bytes": 102404809,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 0,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 53006688,
            "tx_bytes": 72308780,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 91875,
            "tx_packets": 80394316,
        },
    ),
    (
        "vlan2",
        {
            "rx_bytes": 0,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 0,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 0,
            "tx_bytes": 0,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 0,
            "tx_packets": 0,
        },
    ),
    (
        "br0",
        {
            "rx_bytes": 5699827990,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 0,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 13109400,
            "tx_bytes": 4643330713,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 0,
            "tx_packets": 15198823,
        },
    ),
    (
        "wl0.1",
        {
            "rx_bytes": 311596615,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 199907,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 4150488,
            "tx_bytes": 72308780,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 7706,
            "tx_packets": 385338,
        },
    ),
    (
        "ds0.1",
        {
            "rx_bytes": 102404809,
            "rx_carrier": 0,
            "rx_colls": 0,
            "rx_compressed": 0,
            "rx_drop": 0,
            "rx_errs": 0,
            "rx_fifo": 0,
            "rx_packets": 805208,
            "tx_bytes": 0,
            "tx_compressed": 0,
            "tx_drop": 0,
            "tx_errs": 0,
            "tx_fifo": 0,
            "tx_frame": 0,
            "tx_multicast": 0,
            "tx_packets": 0,
        },
    ),
]
LOADAVG_DATA = ["0.23 0.50 0.68 2/167 13095"]
MEMINFO_DATA = ["0.46 0.75 0.77 1/165 2609"]
WL_DATA: list[str | None] = [
    "assoclist 01:02:03:04:06:08\r",
    "assoclist 08:09:10:11:12:14\r",
    "assoclist 08:09:10:11:12:15\r",
    "assoclist AB:CD:DE:AB:CD:EF\r",
]
WL_MIISING_LINE = deepcopy(WL_DATA)
WL_MIISING_LINE.append(None)

WL_DEVICES = {
    "01:02:03:04:06:08": new_device("01:02:03:04:06:08"),
    "08:09:10:11:12:14": new_device("08:09:10:11:12:14"),
    "08:09:10:11:12:15": new_device("08:09:10:11:12:15"),
    "AB:CD:DE:AB:CD:EF": new_device("AB:CD:DE:AB:CD:EF"),
}
ARP_DATA = [
    "? (123.123.123.125) at 01:02:03:04:06:08 [ether]  on eth0\r",
    "? (123.123.123.126) at 08:09:10:11:12:14 [ether]  on br0\r",
    "? (123.123.123.128) at AB:CD:DE:AB:CD:EF [ether]  on br0\r",
    "? (123.123.123.127) at <incomplete>  on br0\r",
    "? (172.16.10.2) at 00:25:90:12:2D:90 [ether]  on br0\r",
    "? (169.254.0.2) at a0:ad:9f:0f:03:d9 [ether] on eth.ai-10\r",
]

ARP_DEVICES = deepcopy(WL_DEVICES)
ARP_DEVICES["01:02:03:04:06:08"].device_data["ip"] = "123.123.123.125"
ARP_DEVICES["01:02:03:04:06:08"].interface["id"] = "eth0"
ARP_DEVICES["08:09:10:11:12:14"].device_data["ip"] = "123.123.123.126"
ARP_DEVICES["08:09:10:11:12:14"].interface["id"] = "br0"
ARP_DEVICES["AB:CD:DE:AB:CD:EF"].device_data["ip"] = "123.123.123.128"
ARP_DEVICES["AB:CD:DE:AB:CD:EF"].interface["id"] = "br0"
ARP_DEVICES["00:25:90:12:2D:90"] = new_device("00:25:90:12:2D:90")
ARP_DEVICES["00:25:90:12:2D:90"].device_data["ip"] = "172.16.10.2"
ARP_DEVICES["00:25:90:12:2D:90"].interface["id"] = "br0"
ARP_DEVICES["A0:AD:9F:0F:03:D9"] = new_device("A0:AD:9F:0F:03:D9")
ARP_DEVICES["A0:AD:9F:0F:03:D9"].device_data["ip"] = "169.254.0.2"
ARP_DEVICES["A0:AD:9F:0F:03:D9"].interface["id"] = "eth.ai-10"
NEIGH_DATA = [
    "123.123.123.125 dev eth0 lladdr 01:02:03:04:06:08 REACHABLE\r",
    "123.123.123.126 dev br0 lladdr 08:09:10:11:12:14 REACHABLE\r",
    "123.123.123.128 dev br0 lladdr ab:cd:de:ab:cd:ef REACHABLE\r",
    "123.123.123.127 dev br0  FAILED\r",
    "123.123.123.129 dev br0 lladdr 08:09:15:15:15:15 DELAY\r",
    "fe80::feff:a6ff:feff:12ff dev br0 lladdr fc:ff:a6:ff:12:ff STALE\r",
    "169.254.0.2 dev eth.ai-10 lladdr a0:ad:9f:0f:03:d9 REACHABLE\r",
]

NEIGH_DEVICES = deepcopy(ARP_DEVICES)
NEIGH_DEVICES["01:02:03:04:06:08"].device_data["status"] = "REACHABLE"
NEIGH_DEVICES["08:09:10:11:12:14"].device_data["status"] = "REACHABLE"
NEIGH_DEVICES["08:09:15:15:15:15"] = new_device("08:09:15:15:15:15")
NEIGH_DEVICES["08:09:15:15:15:15"].device_data["status"] = "DELAY"
NEIGH_DEVICES["08:09:15:15:15:15"].device_data["ip"] = "123.123.123.129"
NEIGH_DEVICES["A0:AD:9F:0F:03:D9"].device_data["status"] = "REACHABLE"
NEIGH_DEVICES["AB:CD:DE:AB:CD:EF"].device_data["status"] = "REACHABLE"
NEIGH_DEVICES["FC:FF:A6:FF:12:FF"] = new_device("FC:FF:A6:FF:12:FF")
NEIGH_DEVICES["FC:FF:A6:FF:12:FF"].device_data["ip"] = (
    "fe80::feff:a6ff:feff:12ff"
)
NEIGH_DEVICES["FC:FF:A6:FF:12:FF"].device_data["status"] = "STALE"
LEASES_DATA = [
    "51910 01:02:03:04:06:08 123.123.123.125 TV 01:02:03:04:06:08\r",
    "79986 01:02:03:04:06:10 123.123.123.127 android 01:02:03:04:06:10\r",
    "23523 08:09:10:11:12:14 123.123.123.126 * 08:09:10:11:12:14\r",
    "35556 08:09:15:15:15:15 123.123.123.129 Test 08:09:15:15:15:15\r",
]

LEASES_DEVICES = deepcopy(NEIGH_DEVICES)
LEASES_DEVICES["01:02:03:04:06:08"].device_data["name"] = "TV"
LEASES_DEVICES["08:09:15:15:15:15"].device_data["name"] = "Test"

WAKE_DEVICES_AP = deepcopy(NEIGH_DEVICES)
WAKE_DEVICES_AP["01:02:03:04:06:08"].interface["name"] = "2G"
WAKE_DEVICES_AP["01:02:03:04:06:08"].interface["mac"] = "A2:2A:54:EC:20:3F"
WAKE_DEVICES_AP["01:02:03:04:06:08"].device_data["rssi"] = -83
WAKE_DEVICES_AP["08:09:15:15:15:15"].interface["name"] = "wired_mac"
WAKE_DEVICES_AP["08:09:15:15:15:15"].interface["mac"] = "A2:2A:54:EC:20:3F"
WAKE_DEVICES_AP["08:09:10:11:12:14"].interface["name"] = "5G"
WAKE_DEVICES_AP["08:09:10:11:12:14"].interface["mac"] = "A2:2A:54:EC:20:3F"
WAKE_DEVICES_AP["08:09:10:11:12:14"].device_data["rssi"] = -68

WAKE_DEVICES = deepcopy(WAKE_DEVICES_AP)
WAKE_DEVICES["01:02:03:04:06:08"].device_data["name"] = "TV"
WAKE_DEVICES["08:09:15:15:15:15"].device_data["name"] = "Test"

WAKE_DEVICES_REQIRE_IP = deepcopy(WAKE_DEVICES)
del WAKE_DEVICES_REQIRE_IP["08:09:10:11:12:15"]

WAKE_DEVICES_REACHABLE = deepcopy(WAKE_DEVICES)
del WAKE_DEVICES_REACHABLE["08:09:15:15:15:15"]

WAKE_DEVICES_REACHABLE_AND_IP = deepcopy(WAKE_DEVICES)
del WAKE_DEVICES_REACHABLE_AND_IP["08:09:15:15:15:15"]
del WAKE_DEVICES_REACHABLE_AND_IP["08:09:10:11:12:15"]

WAKE_DEVICES_AP_NO_IP = deepcopy(WAKE_DEVICES_AP)

CLIENTLIST_DATA = [
    (
        '{"A2:2A:54:EC:20:3F":{"2G":{"01:02:03:04:06:08":'
        '{"ip":"123.123.123.125","rssi":"-83"}},"5G":{"08:09:10:11:12:14":'
        '{"ip":"123.123.123.126","rssi": "-68"}},'
        '"wired_mac":{"08:09:15:15:15:15":{"ip":"123.123.123.129"}}}}'
    )
]

BAD_CLIENTLIST_DATA = [
    (
        '{"A2:2A:54:EC:20:3F":{"2G":{"01:02:03:04:06:08":'
        '{"ip":"123.123.123.125","rssi":"-83"}},"5G":{"08:09:10:11:12:14":'
        '{"ip":"123.123.123.126","rssi": "-68"}},'
        '"wired_mac":{"08:09:15:15:15:15":{"ip":"123.123.123.129"}}}'
    )
]

NVRAM_DHCP_DATA = (
    "dhcp_start=192.168.1.2",
    "dhcp_end=192.168.1.254",
    "dhcp_lease=86400",
    "ipv6_dhcp_end=",
    "ipv6_dhcp_start=",
    "ipv61_dhcp_start=03aa:db87:4216:3505:fa95:5f92:ed0d:2a22",
    "ipv61_dhcp_end=ff44:aa12:d7e9:a39d:7f77:47cb:709e:8809",
    "dhcp_enable_x=1",
    "dhcpd_querylog=1",
    "wan1_vpndhcp=1",
    "wan_dhcpenable_x=1",
    "dhcp_dns1_x=",
    "wan1_dhcpenable_x=1",
    "ipv6_dhcp6s_enable=1",
    "dhcpd_send_wpad=1",
    "wan0_dhcpenable_x=1",
    "dhcpd_dns_router=1",
    "wan0_dhcpfilter_enable=1",
    "vpn_server_dhcp=1",
    "wan_dhcp_qry=1",
    "wan_vpndhcp=1",
    "vpn_server2_dhcp=1",
    "ipv61_dhcp_lifetime=86400",
    "ipv6_dhcp_pd=1",
    "ipv61_dhcp_pd=1",
    "wan1_dhcpfilter_enable=1",
    "dhcp_gateway_x=",
    "dhcpd_lmax=253",
    "ipv61_dhcp6c_release=1",
    "wan0_vpndhcp=1",
    "dhcp_static_x=1",
    "wan_dhcpfilter_enable=1",
    "dhcp_dns2_x=",
    "ipv6_dhcp_lifetime=86400",
    "wan0_dhcp_qry=1",
    "ipv6_6rd_dhcp=1",
    "wan1_dhcp_qry=1",
    "ipv61_6rd_dhcp=1",
    "dhcp_enable_x=1",
    "dhcp_wins_x=",
    "ipv6_dhcp6c_release=1",
    "vpn_server1_dhcp=1",
    "size: 321 bytes (31 left)",  # grep output
    "dhcp_staticlist=<00:00:00:00:00:01>192.168.1.111>><00:00:00:00:00:02>192.168.1.222>>",
)

NVRAM_DHCP_VALUES = {
    "ipv61_dhcp_start": "03aa:db87:4216:3505:fa95:5f92:ed0d:2a22",
    "ipv61_dhcp_end": "ff44:aa12:d7e9:a39d:7f77:47cb:709e:8809",
    "dhcp_enable_x": "1",
    "dhcp_start": "192.168.1.2",
    "dhcp_end": "192.168.1.254",
    "dhcp_lease": "86400",
    "dhcp_static_x": "1",
    "dhcp_staticlist": "<00:00:00:00:00:01>192.168.1.111>><00:00:00:00:00:02>192.168.1.222>>",
    "dhcpd_dns_router": "1",
    "dhcpd_lmax": "253",
    "dhcpd_querylog": "1",
    "dhcpd_send_wpad": "1",
    "ipv61_6rd_dhcp": "1",
    "ipv61_dhcp6c_release": "1",
    "ipv61_dhcp_lifetime": "86400",
    "ipv61_dhcp_pd": "1",
    "ipv6_6rd_dhcp": "1",
    "ipv6_dhcp6c_release": "1",
    "ipv6_dhcp6s_enable": "1",
    "ipv6_dhcp_lifetime": "86400",
    "ipv6_dhcp_pd": "1",
    "vpn_server1_dhcp": "1",
    "vpn_server2_dhcp": "1",
    "vpn_server_dhcp": "1",
    "wan0_dhcp_qry": "1",
    "wan0_dhcpenable_x": "1",
    "wan0_dhcpfilter_enable": "1",
    "wan0_vpndhcp": "1",
    "wan1_dhcp_qry": "1",
    "wan1_dhcpenable_x": "1",
    "wan1_dhcpfilter_enable": "1",
    "wan1_vpndhcp": "1",
    "wan_dhcp_qry": "1",
    "wan_dhcpenable_x": "1",
    "wan_dhcpfilter_enable": "1",
    "wan_vpndhcp": "1",
}

NVRAM_MODEL_DATA = ("model=RT-AC88U", "size: 321 bytes (21 left)")
NVRAM_MODEL_VALUES = {"model": "RT-AC88U"}

NVRAM_QOS_DATA = (
    "qos_reset=0",
    "qos_irates=100,100,100,100,100,0,0,0,0,0",
    "qos_rst=off",
    "qos_sticky=1",
    "qos_overhead=0",
    "qos_orules=",
    "qos_ibw=",
    "qos_type=1",
    "qos_obw1=",
    "qos_syn=on",
    "qos_burst0=",
    "qos_ack=on",
    "qos_burst1=",
    "qos_method=0",
    "qos_atm=0",
    "size: 321 bytes (31 left)",
    "qos_icmp=on",
    "qos_enable=0",
    "qos_obw=",
    "qos_default=3",
    "qos_ibw1=",
    "qos_fin=off",
    "qos_mpu=0",
    "qos_bw_rulelist=",
    "qos_orates=80-100,10-100,5-100,3-100,2-95,0-0,0-0,0-0,0-0,0-0",
    "qos_rulelist=<Web Surf>>80>tcp>0~512>0<HTTPS>>443>tcp>0~512>0<File Transfer>>80>tcp>512~>3<File Transfer>>443>tcp>512~>3",
)
NVRAM_QOS_VALUES = {
    "qos_ack": "on",
    "qos_atm": "0",
    "qos_default": "3",
    "qos_enable": "0",
    "qos_fin": "off",
    "qos_icmp": "on",
    "qos_irates": "100,100,100,100,100,0,0,0,0,0",
    "qos_method": "0",
    "qos_mpu": "0",
    "qos_orates": "80-100,10-100,5-100,3-100,2-95,0-0,0-0,0-0,0-0,0-0",
    "qos_overhead": "0",
    "qos_reset": "0",
    "qos_rst": "off",
    "qos_rulelist": (
        "<Web Surf>>80>tcp>0~512>0<HTTPS>>443>tcp>0~512>0<File "
        "Transfer>>80>tcp>512~>3<File Transfer>>443>tcp>512~>3"
    ),
    "qos_sticky": "1",
    "qos_syn": "on",
    "qos_type": "1",
}

NVRAM_REBOOT_DATA = (
    "reboot_schedule=00000000000",
    "reboot_schedule_enable=0",
    "reboot_time=140",
    "size: 66547 bytes (64525 left)",
)
NVRAM_REBOOT_VALUES = {
    "reboot_schedule": "00000000000",
    "reboot_schedule_enable": "0",
    "reboot_time": "140",
}
NVRAM_WLAN_DATA = {
    "wan_unit=0",
    "wan_dhcpenable_x=1",
    "wan_pppoe_passwd=",
    "wan_clientid_type=0",
    "wan_auth_x=",
    "wan_nat_x=1",
    "ddns_wan_unit=-1",
    "wan_pppoe_service=",
    "wan_pppoe_mru=1492",
    "wan_gateway=1.1.1.1",
    "wan_ppp_echo_failure=10",
    "wan_vendorid=",
    "wan_gateway_x=0.0.0.0",
    "wan_phytype=",
    "wan_hwname=",
    "wan_hwaddr_x=",
    "wan_ppp_echo=1",
    "ddns_last_wan_unit=-1",
    "wan_pppoe_relay=0",
    "wan_enable=1",
    "wan_pppoe_options_x=",
    "wan_dns=2.2.2.2 2.2.8.8",
    "wan_dns2_x=",
    "wan_pppoe_mtu=1492",
    "wan_dhcp_qry=1",
    "wan_vpndhcp=1",
    "wan_netmask_x=0.0.0.0",
    "wan_proto=dhcp",
    "wan_gw_mac=00:00:00:00:00:01",
    "wan_ipaddr_x=0.0.0.0",
    "led_wan_gpio=5",
    "wan_ppp_echo_interval=6",
    "wan_pppoe_idletime=0",
    "wan_hwaddr=00:00:00:00:00:01",
    "size: 66505 bytes (64567 left)",
    "wan_pppoe_username=",
    "wan_ifnames=eth0",
    "wan_pppoe_auth=",
    "wan_pptp_options_x=",
    "wan_clientid=",
    "wan_dns1_x=",
    "wan_pppoe_hostuniq=",
    "wan_upnp_enable=1",
    "wan_ipaddr=8.2.8.1",
    "wan_wins=",
    "wan_mtu=1500",
    "wan_dhcpfilter_enable=1",
    "wan_hostname=",
    "wan_desc=",
    "wan_dnsenable_x=1",
    "wan_pppoe_ac=",
    "wan_heartbeat_x=",
}
NVRAM_WLAN_VALUES = {
    "ddns_last_wan_unit": "-1",
    "ddns_wan_unit": "-1",
    "led_wan_gpio": "5",
    "wan_clientid_type": "0",
    "wan_dhcp_qry": "1",
    "wan_dhcpenable_x": "1",
    "wan_dhcpfilter_enable": "1",
    "wan_dns": "2.2.2.2 2.2.8.8",
    "wan_dnsenable_x": "1",
    "wan_enable": "1",
    "wan_gateway": "1.1.1.1",
    "wan_gateway_x": "0.0.0.0",
    "wan_gw_mac": "00:00:00:00:00:01",
    "wan_hwaddr": "00:00:00:00:00:01",
    "wan_ifnames": "eth0",
    "wan_ipaddr": "8.2.8.1",
    "wan_ipaddr_x": "0.0.0.0",
    "wan_mtu": "1500",
    "wan_nat_x": "1",
    "wan_netmask_x": "0.0.0.0",
    "wan_ppp_echo": "1",
    "wan_ppp_echo_failure": "10",
    "wan_ppp_echo_interval": "6",
    "wan_pppoe_idletime": "0",
    "wan_pppoe_mru": "1492",
    "wan_pppoe_mtu": "1492",
    "wan_pppoe_relay": "0",
    "wan_proto": "dhcp",
    "wan_unit": "0",
    "wan_upnp_enable": "1",
    "wan_vpndhcp": "1",
}

NVRAM_FIRMWARE_DATA = {
    "webs_notif_flag=",
    "webs_last_info=",
    "firmware_check_enable=1",
    "webs_chg_sku=0",
    "webs_state_info_am=000_00_0",
    "webs_SG_mode=0",
    "webs_state_update=1",
    "buildno=000.00",
    "webs_state_info=0000_000_00_0",
    "webs_state_url=",
    "webs_update_enable=1",
    "webs_state_flag=0",
    "firmver_org=0.0.0.0",
    "webs_update_time=02:00",
    "buildinfo=Mon Jan 01 00:00:00 UTC 2020 root@17e",
    "webs_update_trigger=GUI_CFG",
    "webs_state_error=0",
    "buildno_org=000.00",
    "webs_state_upgrade=",
    "firmver=0.0.0.0",
    "firmware_path=",
    "size: 66505 bytes (64567 left)",
}
NVRAM_FIRMWARE_VALUES = {
    "buildinfo": "Mon Jan 01 00:00:00 UTC 2020 root@17e",
    "buildno": "000.00",
    "buildno_org": "000.00",
    "firmver": "0.0.0.0",
    "firmver_org": "0.0.0.0",
    "firmware_check_enable": "1",
    "webs_SG_mode": "0",
    "webs_chg_sku": "0",
    "webs_state_error": "0",
    "webs_state_flag": "0",
    "webs_state_info": "0000_000_00_0",
    "webs_state_info_am": "000_00_0",
    "webs_state_update": "1",
    "webs_update_enable": "1",
    "webs_update_time": "02:00",
    "webs_update_trigger": "GUI_CFG",
}

NVRAM_LABEL_MAC_DATA = (
    "label_mac=00:00:00:00:00:01",
    "size: 66505 bytes (64567 left)",
)
NVRAM_LABEL_MAC_VALUES = {"label_mac": "00:00:00:00:00:01"}

HOST_DATA = (
    "127.0.0.1 localhost.localdomain localhost",
    "192.168.1.1 RT-AC88U-2780. RT-AC88U-2780",
    "192.168.1.1 RT-AC88U-2780.local",
)
