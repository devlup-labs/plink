'''
Function Name: retrieve_metadata 
Purpose: to collect receiver's metadata : public_ip, port, free_space, timestamp, session_id
Inputs:  
    -public_ip : public ip of the receiver
    -port : opened port for connection
    -session_id : session id of the operation
     
Outputs:  
    - returns dictionary which contains metadata : public_ip, port, free_space, timestamp, session_id 

'''

import shutil
from datetime import datetime

def retrieve_metadata(public_ip,port,session_id):
    
    total, used, free = shutil.disk_usage("/")
    
    return {
        "public_ip": public_ip,
        "port": port,
        "free_space": free,
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id
    }