# Function: is_NAT_present

## Purpose:   
Detects if the current device is behind NAT by comparing local and public IP addresses and tells the NAT type using STUN.

### Parameters:   
None.

### Returns:  
bool:
True if NAT is detected (i.e., local IP ≠ public IP), otherwise False.

### Raises:  
No explicit exceptions raised (all exceptions are caught and handled internally)

### Example:   
python
nat_detected = is_NAT_present()
Output: Prints detection results and returns True/False




# Function: is_UPnP_present

## Purpose:   
Detects if a UPnP-enabled router is available and accessible on the local network. Retrieves external IP if UPnP is available.

### Parameters:   
None.

### Returns:  
bool:
True if a UPnP-enabled IGD is found and its external IP is fetched, otherwise False

### Raises:  
No explicit exceptions raised (all exceptions are caught and handled internally).

### Example:   
python
upnp_available = is_UPnP_present()
Output: Prints UPnP discovery results and returns True/False