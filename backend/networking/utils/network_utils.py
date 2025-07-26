import socket
import requests
from utils.logging import LogType, log


def get_network_details(general_logfile_path):
    """Detect NAT presence and type using IP comparison and STUN."""

    network_details_dict={} #initiates a dictionary for network details

    log("Starting NAT detection", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        network_details_dict["local_ip"] = local_ip if local_ip else "Unavailable"
        log(f"Local IP detected: {local_ip}", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
        
    except Exception as e:
        network_details_dict["local_ip"] = "Unavailable"
        local_ip = f"Error: {e}"
        print(f"Local IP: {local_ip}")
        log(f"Local IP detection failed: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)
    
    # Get public IP
    try:
        public_ip = requests.get("https://api.ipify.org").text.strip()
    except Exception as e:
        public_ip = f"Error: {e}"
        log(f"Public IP detection failed: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)
        
    log(f"Public IP detected: {public_ip}", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)

    if public_ip and network_details_dict["local_ip"] != "Unavailable":
        nat_detected = network_details_dict["local_ip"] != public_ip
        network_type = "NAT" if nat_detected else "Public"
    else:
        nat_detected = None
        network_type = "Unknown"

    network_details_dict["network_type"] = network_type
    log(f"Network type: {network_type}", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
    
    # STUN NAT type detection
    log("Starting STUN NAT type detection", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
    try:
        import stun
        nat_type, external_ip, external_port = stun.get_ip_info()
        network_details_dict["nat_type"]=nat_type if nat_type else "unknown"
        network_details_dict["external_ip"]=external_ip if external_ip else "unavailable"
        log(f"STUN detected NAT type: {nat_type}, External IP: {external_ip}, External Port: {external_port}", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
    except Exception as e:
        log(f"STUN detection failed: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)

    """Detect UPnP availability and capabilities."""
    log("Starting UPnP detection", log_type=LogType.INFO, status="Success" , general_logfile_path = general_logfile_path)
    
    try:
        import miniupnpc
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        log("Discovering UPnP devices...", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
        ndevices = upnp.discover()
        if ndevices == 0:
            log("No UPnP devices found", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)

        
        log(f"UPnP devices found: {ndevices}", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
        
        try:
            upnp.selectigd()
        except Exception as e:
            log(f"Failed to select UPnP IGD: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)
            
        
        # Test if we can get the external IP
        try:
            external_ip = upnp.externalipaddress()
            log(f"UPnP External IP: {external_ip}", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
            network_details_dict["upnp_enabled"] = True
           
        except Exception as e:
            log(f"Failed to get UPnP external IP: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)
            network_details_dict["upnp_enabled"] = False
            
        firewall_enabled = network_details_dict["network_type"] == "NAT" and not network_details_dict["upnp_enabled"]
        network_details_dict["firewall_enabled"] = firewall_enabled
        log(f"Firewall status: {'Enabled' if firewall_enabled else 'Not Detected'}", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)

    except Exception as e:
        log(f"UPnP detection failed: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)
        network_details_dict["upnp_enabled"] = False
        network_details_dict["firewall_enabled"] = False
    
    network_details_dict["open_ports"]=[] #create an empty open ports list to scan and store open ports
    #the dictionary will be called in open ports function file and all the open ports would be appended accordingly

    return network_details_dict
