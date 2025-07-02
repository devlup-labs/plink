'''
Function Name: retrieve_metadata
Purpose: to collect receiver's metadata : public_ip, port, free_space, timestamp, session_id
Inputs:
    - None
Outputs:
    - returns dictionary which contains metadata free_space and timestamp

'''

import shutil
from datetime import datetime

def retrieve_metadata():

    total, used, free = shutil.disk_usage("/")

    return {
        "free_space": free,
        "timestamp": datetime.now().isoformat(),
    }
