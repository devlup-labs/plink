import socket
import miniupnpc
import stun
from utils.logging import LogType, log

PORT_START = 49152
PORT_END = 65535

def scan_ports(network_metadata,general_logfile_path) :

    #for UPnP
    if network_metadata.get("UPnP" , False):
        try:
            upnp = miniupnpc.UPnP()
            upnp.discoverdelay = 200
            upnp.discover()
            upnp.selectigd()
            
            upnp_ports = []
            for port in range(PORT_START,PORT_END+1):
                try:
                    upnp.addportmapping(port, 'TCP', upnp.lanaddr, port, 'plink-transfer', '')
                    upnp_ports.append(port)
                    if len(upnp_ports) == 64:
                        break
                except:
                    continue
            log(
                f"scanning of upnp ports complete",
                LogType.INFO,
                "Success",
                general_logfile_path,
                True
            )
            
            return upnp_ports
        
        except Exception as e :
            log(f"Error in scanning upnp ports : {e}",
            LogType.ERROR,
            "Failure",
            general_logfile_path,
            True
            )
            
    # for NAT
    elif network_metadata.get("NAT",False) :
        try :
            open_ports=[]

            _, external_ip, _ = stun.get_ip_info()
            
            if not external_ip:
                raise Exception("STUN failed to retrieve public IP.")

            for port in range(PORT_START, PORT_END + 1):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5) 
                    result = s.connect_ex((external_ip, port))
                    if result == 0:
                        open_ports.append(port)
                    if len(open_ports)==64 :
                        break
            log(
                f"scanning of open ports complete",
                LogType.INFO,
                "Success",
                general_logfile_path,
                True
            )

            return open_ports
        
        except Exception as e :
            log(f"Error in scanning open ports : {e}",
            LogType.ERROR,
            "Failure",
            general_logfile_path,
            True
            )
            
    # if UPnP andNAt both aren't present      
    else:
        try:
            local_ports = []
            
            for port in range(PORT_START, PORT_END + 1):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.bind(('0.0.0.0', port))
                        local_ports.append(port)
                        if len(local_ports) == 64:
                            break
                    except:
                        continue

            log(
                f"scanning of local ports complete",
                LogType.INFO,
                "Success",
                general_logfile_path,
                True
            )

            return local_ports

        except Exception as e:
            log(f"Error finding local ports: {e}",
            LogType.ERROR,
            "Failure",
            general_logfile_path,
            True
            )

