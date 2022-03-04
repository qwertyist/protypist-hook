from ctypes import *
from defines import *
from unittest.mock import FunctionTypes
import json
import websocket
try:
    import threading
except ImportError:
    import _thread as thread
import time


kernel32 = windll.kernel32
def on_open(ws):
    print("open ws")
def on_message(ws, message):
    pass
def on_error(ws, error):
    print("error:", error)

def on_close(ws, msg, data):
    print("### closed ###")

def send(ws, buf):
    ws.send(buf)

class listener():
    def __init__(self):
        self.h_process       =     None
        self.pid             =     None
        self.debugger_active =     False
        self.h_thread = None
        self.context = None
        self.text_buffer_pointer = None
        self.text_buffer = None
      #  self.exception = None
      #  self.exception_address = None
        self.breakpoints = {}
        self.first_breakpoint = True
    
    def load(self,path_to_exe):
        creation_flags = DEBUG_PROCESS
        
        startupinfo = STARTUPINFO()
        process_information = PROCESS_INFORMATION()
        
        startupinfo.dwFlags = 0x1
        startupinfo.wShowWindow = 0x0
        
        startupinfo.cb = sizeof(startupinfo)
         
        if kernel32.CreateProcessW(path_to_exe,
                           None,
                           None,
                           None,
                           None,
                           creation_flags,
                           None,
                           None,
                           byref(startupinfo),
                           byref(process_information)):
            
            print ("[*] We have successfully launched the process!")
            print ("[*] PID: %d" % process_information.dwProcessId)
            self.h_process = self.open_process(process_information.dwProcessId)

        else:
            print ("[*] Error: 0x%08x." % kernel32.GetLastError())
            
    def open_process(self,pid):
        h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS,False,pid)
        return h_process
    
    def attach(self,pid):
        self.h_process=self.open_process(pid)
        if kernel32.DebugActiveProcess(pid):
        
            self.debugger_active = True
            self.pid        = int(pid)
           # self.run()
        else:
            print ("[*] Unable to attach to the process")
            
    def run(self, uuid):
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp("ws://localhost:4000/ws",
                              on_open = on_open,
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close,
                              header= {"session: "+uuid})

        wst = threading.Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()
        while self.debugger_active == True:
            self.get_debug_event()
            if self.text_buffer_pointer:
                length =  int.from_bytes(self.read_process_memory(self.text_buffer_pointer,3),'little')
                address = self.read_process_memory(self.text_buffer_pointer+4, 4)
                address = int.from_bytes(address,'little')
                buffer = self.read_text_buffer(address,length-1)
                buf = self.parse_text_buffer(buffer)
                send(ws, buf)

    def get_debug_event(self):
        
        debug_event = DEBUG_EVENT()
        continue_status = DBG_CONTINUE
        
        if kernel32.WaitForDebugEvent(byref(debug_event),0x00a5):
          #  input("Press a key to continue ...")  
          #  self.debugger_active = False
          self.h_thread          = self.open_thread(debug_event.dwThreadId)
          #self.context           = self.get_thread_context(self.h_thread)
          self.context           = self.get_thread_context(h_thread=self.h_thread)
        #print("Event Code: %d Thread ID: %d " % (debug_event.dwDebugEventCode,debug_event.dwThreadId))
        if debug_event.dwDebugEventCode == EXCEPTION_DEBUG_EVENT:
            exception = debug_event.u.Exception.ExceptionRecord.ExceptionCode
            self.exception_address = debug_event.u.Exception.ExceptionRecord.ExceptionAddress
            
            if exception == EXCEPTION_ACCESS_VIOLATION:
                print ("Access Violation Detected.")
            
            elif exception == EXCEPTION_BREAKPOINT:
                continue_status = self.exception_handler_breakpoint()
            
            elif exception == EXCEPTION_GUARD_PAGE:
                print ("Guard Page Access Detected")
                
            elif exception == EXCEPTION_SINGLE_STEP:
                print ("Single Stepping")
                
                
     
        kernel32.ContinueDebugEvent( \
                        debug_event.dwProcessId, \
                        debug_event.dwThreadId, \
                        continue_status)   
    def parse_text_buffer(self, buffer):

        output = {}
        output["text"] = ""
        for b in buffer:
            if b == 13:
                output["text"] += "<br />"
            elif b > 160:
                output["text"] += "&#" + str(b) + ";"
            elif b != 0:
                output["text"] += chr(b)




        return output["text"]


    def read_text_buffer(self, address, length):
        data         = ""
        read_buf     = create_string_buffer(length*2)
        count        = c_ulong(0)
        
        
        kernel32.ReadProcessMemory(self.h_process, address, read_buf, length*2, byref(count))
        data    = read_buf.raw
        
        return data

    def read_process_memory(self,address,length):
        
        data         = ""
        read_buf     = create_string_buffer(length)
        count        = c_ulong(0)
        
        
        kernel32.ReadProcessMemory(self.h_process, address, read_buf, length, byref(count))
        data    = read_buf.raw
        
        return data
    
    
    def write_process_memory(self,address,data):
        
        count  = c_ulong(0)
        length = len(data)
        print(hex(address))
        c_data = c_char_p(data[count.value:])
        print ("CDATA %s ",c_data)

        if not kernel32.WriteProcessMemory(self.h_process, address, c_data, length, byref(count)):
            return False
        else:
            return True
    
    def bp_set(self,address):
        print ("[*] Setting breakpoint at: 0x%08x" % address)
        #if not self.breakpoints.has_key(address):
        if not address in self.breakpoints:

            # store the original byte
            old_protect = c_ulong(0)
            kernel32.VirtualProtectEx(self.h_process, address, 1, PAGE_EXECUTE_READWRITE, byref(old_protect))
            
            original_byte = self.read_process_memory(address, 1)
            if original_byte != False:
                
                # write the INT3 opcode
                if self.write_process_memory(address, b"\xCC"):
                    # register the breakpoint in our internal list
                    self.breakpoints[address] = (original_byte)
                    return True
            else:
                return False

    
    
    def exception_handler_breakpoint(self):
        print ("[*] Exception address: 0x%08x" % self.exception_address)
        # check if the breakpoint is one that we set
        #if not self.breakpoints.has_key(self.exception_address):
        if not self.exception_address in self.breakpoints:
           
                # if it is the first Windows driven breakpoint
                # then let's just continue on
                if self.first_breakpoint == True:
                   self.first_breakpoint = False
                   print ("[*] Hit the first breakpoint.")
                   return DBG_CONTINUE
               
        else:
            
            if not self.text_buffer_pointer:
                print ("[*] Hit user defined breakpoint.")
                # this is where we handle the breakpoints we set 
                # first put the original byte back
                self.write_process_memory(self.exception_address, self.breakpoints[self.exception_address])
                print("write process memory")
                # obtain a fresh context record, reset EIP back to the 
                # original byte and then set the thread's context record
                # with the new EIP value
                self.context = self.get_thread_context(h_thread=self.h_thread)
                print("get thread context")
                self.context.Eip -= 1
                self.text_buffer_pointer = self.context.Edx
                #Eip current executing instruction register
                kernel32.SetThreadContext(self.h_thread,byref(self.context))
                print("set thread context")
                
            continue_status = DBG_CONTINUE

        return continue_status       
    #def exception_handler_breakpoint(self):
    #        print ("[*] Inside the breakpoint handler.")
    #        print ("Exception Address: ox%08x" % self.exception_address)
    #        return DBG_CONTINUE
            
    def detach(self):
        
        if kernel32.DebugActiveProcessStop(self.pid):
            print ("[*] Finished debugging. Exiting ...")
            return True
        else: 
            print ("There was an error")
            return False
    
    def open_thread (self, thread_id):
        
        h_thread = kernel32.OpenThread(THREAD_ALL_ACCESS, None, thread_id)
        
        if h_thread is not None:
            return h_thread
        else:
            print ("[*] Could not obtain a valid thread handle.")
            return False
        
    def enumerate_threads(self):
              
        thread_entry     = THREADENTRY32()
        thread_list      = []
        snapshot         = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, self.pid)
        
        if snapshot is not None:
        
            # You have to set the size of the struct
            # or the call will fail
            thread_entry.dwSize = sizeof(thread_entry)

            success = kernel32.Thread32First(snapshot, byref(thread_entry))

            while success:
                if thread_entry.th32OwnerProcessID == self.pid:
                    thread_list.append(thread_entry.th32ThreadID)
    
                success = kernel32.Thread32Next(snapshot, byref(thread_entry))
            
            # No need to explain this call, it closes handles
            # so that we don't leak them.
            kernel32.CloseHandle(snapshot)
            return thread_list
        else:
            return False
        
    def get_thread_context (self, thread_id=None,h_thread=None):
        
        context = CONTEXT()
        context.ContextFlags = CONTEXT_FULL | CONTEXT_DEBUG_REGISTERS
        
        # Obtain a handle to the thread
        if h_thread is None:
            self.h_thread = self.open_thread(thread_id)
                        
        if kernel32.GetThreadContext(self.h_thread, byref(context)):
            
            return context 
        else:
            return False
            
            
    def func_resolve(self,dll,function):
        print ("getting handle")
        handle = kernel32.GetModuleHandleA(dll)
        print ("in func_resolve after handle")
        address = kernel32.GetProcAddress(handle,function)
        print ("in func_resolve after address")
        kernel32.CloseHandle(handle)
        print ("closing handle")
        return address
    
    def bp_set_hw(self, address, length, condition):
        
        # Check for a valid length value
        if length not in (1, 2, 4):
            return False
        else:
            length -= 1
            
        # Check for a valid condition
        if condition not in (HW_ACCESS, HW_EXECUTE, HW_WRITE):
            return False
        
        # Check for available slots
        if not 0 in self.hardware_breakpoints:
            available = 0
        elif not 1 in self.hardware_breakpoints:
            available = 1
        elif not 2 in self.hardware_breakpoints:
            available = 2
        elif not 3 in self.hardware_breakpoints:
            available = 3
        else:
            return False

        # We want to set the debug register in every thread
        for thread_id in self.enumerate_threads():
            context = self.get_thread_context(thread_id=thread_id)

            # Enable the appropriate flag in the DR7
            # register to set the breakpoint
            context.Dr7 |= 1 << (available * 2)

            # Save the address of the breakpoint in the
            # free register that we found
            if   available == 0: context.Dr0 = address
            elif available == 1: context.Dr1 = address
            elif available == 2: context.Dr2 = address
            elif available == 3: context.Dr3 = address

            # Set the breakpoint condition
            context.Dr7 |= condition << ((available * 4) + 16)

            # Set the length
            context.Dr7 |= length << ((available * 4) + 18)

            # Set this threads context with the debug registers
            # set
            h_thread = self.open_thread(thread_id)
            kernel32.SetThreadContext(h_thread,byref(context))

        # update the internal hardware breakpoint array at the used slot index.
        self.hardware_breakpoints[available] = (address,length,condition)

        return True