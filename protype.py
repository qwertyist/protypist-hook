
from defines import *
import time
import pymem
import listener

def connect(uuid):
    protype_listener = listener.listener()

    try:
        process = pymem.Pymem("ProType.exe")
    except: 
        return 1
    print("Process handle:", process.process_handle)
    base_address = pymem.process.module_from_name(process.process_handle, "RICHED20.dll").lpBaseOfDll
    print("Riched20 base address: ", hex(base_address))
    pid = process.process_id
    print(pid)
    process.close_process()
    print ("before attach")
    protype_listener.attach(int(pid))
    print ("after attach")
    time.sleep(1)
    protype_listener.bp_set(base_address + 0x5643A)
    protype_listener.run(uuid)