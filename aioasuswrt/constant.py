"""Constant decleration."""

ALLOWED_KEY_HASHES = [
    "ssh-rsa",
    "rsa-sha2-256",
    "rsa-sha2-512",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
    "ssh-ed25519",
    "ssh-ed448",
]

NETDEV_FIELDS = [
    "tx_bytes",
    "tx_packets",
    "tx_errs",
    "tx_drop",
    "tx_fifo",
    "tx_frame",
    "tx_compressed",
    "tx_multicast",
    "rx_bytes",
    "rx_packets",
    "rx_errs",
    "rx_drop",
    "rx_fifo",
    "rx_colls",
    "rx_carrier",
    "rx_compressed",
]

VPN_COUNT = 5
DEFAULT_DNSMASQ = "/var/lib/misc"
DEFAULT_WAN_INTERFACE = "eth0"
