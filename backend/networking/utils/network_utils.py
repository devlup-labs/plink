import socket
import requests
from utils.logging import LogType, log


def is_NAT_present(general_logfile_path):
    """Detect NAT presence and type using IP comparison and STUN."""
    log("Starting NAT detection", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        log(f"Local IP detected: {local_ip}", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
        s.close()
    except Exception as e:
        local_ip = f"Error: {e}"
        print(f"Local IP: {local_ip}")
        log(f"Local IP detection failed: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)
        return False
    
    # Get public IP
    try:
        public_ip = requests.get("https://api.ipify.org").text.strip()
    except Exception as e:
        public_ip = f"Error: {e}"
        log(f"Public IP detection failed: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)
        return False
    
    log(f"Public IP detected: {public_ip}", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)

    
    nat_detected = local_ip != public_ip
    log(f"NAT detected: {nat_detected}", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
    
    # STUN NAT type detection
    log("Starting STUN NAT type detection", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
    try:
        import stun
        nat_type, external_ip, external_port = stun.get_ip_info()
        log(f"STUN detected NAT type: {nat_type}, External IP: {external_ip}, External Port: {external_port}", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
    except Exception as e:
        log(f"STUN detection failed: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)
    
    return nat_detected

def is_UPnP_present(general_logfile_path):
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
            return False
        
        log(f"UPnP devices found: {ndevices}", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
        
        try:
            upnp.selectigd()
        except Exception as e:
            log(f"Failed to select UPnP IGD: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)
            return False
        
        # Test if we can get the external IP
        try:
            external_ip = upnp.externalipaddress()
            log(f"UPnP External IP: {external_ip}", log_type=LogType.INFO, status="Success", general_logfile_path = general_logfile_path)
            return True
        except Exception as e:
            log(f"Failed to get UPnP external IP: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)
            return False
            
    except Exception as e:
        log(f"UPnP detection failed: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path = general_logfile_path)
        return False

# if _name_ == "_main_":
#     nat_present = detect_nat()
#     upnp_available = detect_upnp()
    
#     print(f"\n=== Summary ===")
#     print(f"NAT detected: {nat_present}")
#     print(f"UPnP available: {upnp_available}")
