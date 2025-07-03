import socket
import requests

def detect_nat():
    """Detect NAT presence and type using IP comparison and STUN."""
    print("=== NAT Detection ===")
    
    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception as e:
        local_ip = f"Error: {e}"
        print(f"Local IP: {local_ip}")
        return False
    
    # Get public IP
    try:
        public_ip = requests.get("https://api.ipify.org").text.strip()
    except Exception as e:
        public_ip = f"Error: {e}"
        print(f"Public IP: {public_ip}")
        return False
    
    print(f"Local IP: {local_ip}")
    print(f"Public IP: {public_ip}")
    
    nat_detected = local_ip != public_ip
    print("NAT Status:", "NAT is present" if nat_detected else "No NAT detected")
    
    # STUN NAT type detection
    print("\n-- STUN NAT Type Detection --")
    try:
        import stun
        nat_type, external_ip, external_port = stun.get_ip_info()
        print(f"NAT Type: {nat_type}, Public IP via STUN: {external_ip}, Port: {external_port}")
    except Exception as e:
        print(f"STUN detection failed: {e}")
    
    return nat_detected

def detect_upnp():
    """Detect UPnP availability and capabilities."""
    print("\n=== UPnP Detection ===")
    
    try:
        import miniupnpc
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        
        print("Discovering UPnP devices...")
        ndevices = upnp.discover()
        if ndevices == 0:
            print("UPnP not available (no devices discovered)")
            return False
        
        print(f"{ndevices} UPnP devices discovered.")
        
        try:
            upnp.selectigd()
        except Exception as e:
            print(f"UPnP IGD selection failed: {e}")
            return False
        
        # Test if we can get the external IP
        try:
            external_ip = upnp.externalipaddress()
            print(f"UPnP is available\nExternal IP (UPnP): {external_ip}")
            return True
        except Exception as e:
            print(f"UPnP available, but failed to get external IP: {e}")
            return False
            
    except Exception as e:
        print(f"UPnP detection failed: {e}")
        return False

# if _name_ == "_main_":
#     nat_present = detect_nat()
#     upnp_available = detect_upnp()
    
#     print(f"\n=== Summary ===")
#     print(f"NAT detected: {nat_present}")
#     print(f"UPnP available: {upnp_available}")
