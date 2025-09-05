import socket
import threading
import time
import random
import requests
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.logging import log, LogType
import stun

def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        return "127.0.0.1"

def get_external_ip():
    """Get the external/public IP address using multiple services."""
    services = [
        "https://api.ipify.org",
        "https://httpbin.org/ip",
        "https://icanhazip.com",
        "https://ipv4.icanhazip.com",
        "https://checkip.amazonaws.com"
    ]

    for service in services:
        try:
            response = requests.get(service, timeout=5)
            if service == "https://httpbin.org/ip":
                return response.json()['origin'].split(',')[0].strip()
            else:
                return response.text.strip()
        except Exception:
            continue

    return None

def detect_nat_type():
    """Detect NAT type using STUN protocol."""
    try:
        url = "https://raw.githubusercontent.com/pradt2/always-online-stun/master/valid_hosts.txt"
        response = requests.get(url)

        stun_servers = []
        for line in response.text.strip().splitlines():
            if ":" in line:
                host, port = line.rsplit(":", 1)
                stun_servers.append((host, int(port)))

        for server, port in stun_servers:
            try:
                nat_type, external_ip, external_port = stun.get_ip_info(
                    stun_host=server,
                    stun_port=port,
                    source_ip="0.0.0.0",
                    source_port=0
                )
                if nat_type and external_ip:
                    return nat_type, external_ip
            except Exception:
                continue

        return "Unknown", None

    except ImportError:
        # Fallback NAT detection without STUN
        local_ip = get_local_ip()
        external_ip = get_external_ip()

        if local_ip and external_ip:
            if local_ip == external_ip:
                return "Open Internet", external_ip
            else:
                return "NAT (Unknown Type)", external_ip

        return "Unknown", None

def detect_upnp():
    """Detect UPnP availability."""
    try:
        import miniupnpc

        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200

        # Discover UPnP devices
        device_count = upnp.discover()
        if device_count == 0:
            return False

        # Try to select an IGD (Internet Gateway Device)
        try:
            upnp.selectigd()
            # Test if we can get external IP
            external_ip = upnp.externalipaddress()
            return True if external_ip else False
        except Exception:
            return False

    except ImportError:
        return False
    except Exception:
        return False

def is_port_open(port, timeout=2):
    """Check if a specific port is open for UDP binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.bind(('', port))
            return True
    except (socket.error, OSError):
        return False

def find_open_ports(start_port=1024, end_port=65535, num_ports=64, timeout=1):
    """Find available UDP ports for binding."""
    open_ports = []

    # Common ports to try first
    common_ports = [
        1024, 1025, 1026, 1027, 1028, 1029, 1030, 1031,
        8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007,
        9000, 9001, 9002, 9003, 9004, 9005, 9006, 9007,
        12000, 12001, 12002, 12003, 12004, 12005, 12006, 12007,
        15000, 15001, 15002, 15003, 15004, 15005, 15006, 15007,
        20000, 20001, 20002, 20003, 20004, 20005, 20006, 20007,
        25000, 25001, 25002, 25003, 25004, 25005, 25006, 25007,
        30000, 30001, 30002, 30003, 30004, 30005, 30006, 30007
    ]

    # Test common ports first
    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_port = {
            executor.submit(is_port_open, port, timeout): port
            for port in common_ports[:num_ports*2]
        }

        for future in as_completed(future_to_port):
            port = future_to_port[future]
            try:
                if future.result() and len(open_ports) < num_ports:
                    open_ports.append(port)
            except Exception:
                pass

    # If we need more ports, scan random ports in range
    if len(open_ports) < num_ports:
        remaining_needed = num_ports - len(open_ports)
        random_ports = []

        while len(random_ports) < remaining_needed * 3:  # Test more than needed
            port = random.randint(start_port, end_port)
            if port not in open_ports and port not in random_ports:
                random_ports.append(port)

        with ThreadPoolExecutor(max_workers=50) as executor:
            future_to_port = {
                executor.submit(is_port_open, port, timeout): port
                for port in random_ports
            }

            for future in as_completed(future_to_port):
                port = future_to_port[future]
                try:
                    if future.result() and len(open_ports) < num_ports:
                        open_ports.append(port)
                except Exception:
                    pass

    return sorted(open_ports[:num_ports])

def analyse_network(general_logfile_path="app.log"):
    """
    Comprehensive network analysis that returns network metadata.

    Returns:
        dict: Network metadata including NAT type, IPs, UPnP status, and open ports
    """
    log("Starting comprehensive network analysis", LogType.INFO, "Started", general_logfile_path)

    # Get IP addresses
    log("Detecting IP addresses", LogType.INFO, "InProgress", general_logfile_path)
    local_ip = get_local_ip()
    external_ip = get_external_ip()

    if not external_ip:
        log("Failed to detect external IP", LogType.ERROR, "Failure", general_logfile_path)
        external_ip = local_ip  # Fallback

    log(f"Local IP: {local_ip}, External IP: {external_ip}", LogType.INFO, "Success", general_logfile_path)

    # Determine network type
    if local_ip == external_ip:
        network_type = "Public"
        log("Network type: Public (no NAT detected)", LogType.INFO, "Success", general_logfile_path)
    else:
        network_type = "NAT"
        log("Network type: NAT detected", LogType.INFO, "Success", general_logfile_path)

    # Detect NAT type
    log("Detecting NAT type using STUN", LogType.INFO, "InProgress", general_logfile_path)
    nat_type, stun_external_ip = detect_nat_type()

    if stun_external_ip and stun_external_ip != external_ip:
        external_ip = stun_external_ip  # Use STUN result if different

    log(f"NAT type detected: {nat_type}", LogType.INFO, "Success", general_logfile_path)

    # Detect UPnP
    log("Detecting UPnP availability", LogType.INFO, "InProgress", general_logfile_path)
    upnp_enabled = detect_upnp()
    log(f"UPnP enabled: {upnp_enabled}", LogType.INFO, "Success", general_logfile_path)

    # Determine firewall status
    firewall_enabled = network_type == "NAT" and not upnp_enabled
    log(f"Firewall status: {'Enabled' if firewall_enabled else 'Not detected'}", LogType.INFO, "Success", general_logfile_path)

    # Find open ports
    log("Scanning for available UDP ports", LogType.INFO, "InProgress", general_logfile_path)
    open_ports = find_open_ports(num_ports=64)

    if len(open_ports) < 64:
        log(f"Warning: Only found {len(open_ports)} open ports, needed 64", LogType.WARNING, "Partial", general_logfile_path)
        # Fill remaining with sequential ports starting from a high number
        last_port = max(open_ports) if open_ports else 50000
        while len(open_ports) < 64:
            last_port += 1
            if is_port_open(last_port, timeout=0.5):
                open_ports.append(last_port)
            elif last_port > 60000:  # Safety limit
                break

    log(f"Found {len(open_ports)} open UDP ports", LogType.INFO, "Success", general_logfile_path)

    # Compile results
    network_metadata = {
        "network_type": network_type,
        "nat_type": nat_type,
        "upnp_enabled": upnp_enabled,
        "external_ip": external_ip,
        "local_ip": local_ip,
        "firewall_enabled": firewall_enabled,
        "open_ports": open_ports
    }

    log("Network analysis completed successfully", LogType.INFO, "Success", general_logfile_path)
    return network_metadata

if __name__ == "__main__":
    # Test the network analysis
    result = analyse_network()
    print("Network Analysis Results:")
    for key, value in result.items():
        if key == "open_ports":
            print(f"{key}: {len(value)} ports - {value[:10]}..." if len(value) > 10 else f"{key}: {value}")
        else:
            print(f"{key}: {value}")
