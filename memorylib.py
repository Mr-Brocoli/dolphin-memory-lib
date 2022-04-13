import ctypes
import struct
from struct import pack, unpack
from ctypes import wintypes, sizeof, addressof, POINTER, pointer
from ctypes.wintypes import DWORD, ULONG, LONG, WORD
from multiprocessing import shared_memory

# Various Windows structs/enums needed for operation
NULL = 0

TH32CS_SNAPHEAPLIST = 0x00000001
TH32CS_SNAPPROCESS  = 0x00000002
TH32CS_SNAPTHREAD   = 0x00000004
TH32CS_SNAPMODULE   = 0x00000008
TH32CS_SNAPALL      = TH32CS_SNAPHEAPLIST | TH32CS_SNAPPROCESS | TH32CS_SNAPTHREAD | TH32CS_SNAPMODULE
assert TH32CS_SNAPALL == 0xF


PROCESS_QUERY_INFORMATION   = 0x0400
PROCESS_VM_OPERATION        = 0x0008
PROCESS_VM_READ             = 0x0010
PROCESS_VM_WRITE            = 0x0020

MEM_MAPPED = 0x40000

ULONG_PTR = ctypes.c_ulonglong

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [ ( 'dwSize' , DWORD ) ,
                 ( 'cntUsage' , DWORD) ,
                 ( 'th32ProcessID' , DWORD) ,
                 ( 'th32DefaultHeapID' , ctypes.POINTER(ULONG)) ,
                 ( 'th32ModuleID' , DWORD) ,
                 ( 'cntThreads' , DWORD) ,
                 ( 'th32ParentProcessID' , DWORD) ,
                 ( 'pcPriClassBase' , LONG) ,
                 ( 'dwFlags' , DWORD) ,
                 ( 'szExeFile' , ctypes.c_char * 260 ) ]
                 
                 
class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [    ( 'BaseAddress' , ctypes.c_void_p),
                    ( 'AllocationBase' , ctypes.c_void_p),
                    ( 'AllocationProtect' , DWORD),
                    ( 'PartitionID' , WORD),
                    ( 'RegionSize' , ctypes.c_size_t),
                    ( 'State' , DWORD),
                    ( 'Protect' , DWORD),
                    ( 'Type' , DWORD)]
 
 
class PSAPI_WORKING_SET_EX_BLOCK(ctypes.Structure):
    _fields_ = [    ( 'Flags', ULONG_PTR),
                    ( 'Valid', ULONG_PTR),
                    ( 'ShareCount', ULONG_PTR),
                    ( 'Win32Protection', ULONG_PTR),
                    ( 'Shared', ULONG_PTR),
                    ( 'Node', ULONG_PTR),
                    ( 'Locked', ULONG_PTR),
                    ( 'LargePage', ULONG_PTR),
                    ( 'Reserved', ULONG_PTR),
                    ( 'Bad', ULONG_PTR),
                    ( 'ReservedUlong', ULONG_PTR)]
                    
                    
#class PSAPI_WORKING_SET_EX_INFORMATION(ctypes.Structure):
#    _fields_ = [    ( 'VirtualAddress' , ctypes.c_void_p),
#                    ( 'VirtualAttributes' , PSAPI_WORKING_SET_EX_BLOCK)]

class PSAPI_WORKING_SET_EX_INFORMATION(ctypes.Structure):
    _fields_ = [    ( 'VirtualAddress' , ctypes.c_void_p),
                    #( 'Flags', ULONG_PTR),
                    ( 'Valid', ULONG_PTR, 1)]
                    #( 'ShareCount', ULONG_PTR),
                    #( 'Win32Protection', ULONG_PTR),
                    #( 'Shared', ULONG_PTR),
                    #( 'Node', ULONG_PTR),
                    #( 'Locked', ULONG_PTR),
                    #( 'LargePage', ULONG_PTR),
                    #( 'Reserved', ULONG_PTR),
                    #( 'Bad', ULONG_PTR),
                    #( 'ReservedUlong', ULONG_PTR)]
                    
    #def print_values(self):
    #    for i,v in self._fields_:
    #        print(i, getattr(self, i))


# The find_dolphin function is based on WindowsDolphinProcess::findPID() from 
# aldelaro5's Dolphin memory engine
# https://github.com/aldelaro5/Dolphin-memory-engine

"""
MIT License

Copyright (c) 2017 aldelaro5

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

class Dolphin(object):
    def __init__(self):
        self.pid = -1
        self.memory = None
        #new
        self.mem2 = ctypes.create_string_buffer(0x4000000)
        self.memptr = ctypes.c_char_p(0)
        self.memptrint = 0
        self.m_hdolphinSUS = None
        
    def reset(self):
        self.pid = -1
        self.memory = None 
        
    def find_dolphin(self, skip_pids=[]):
        entry = PROCESSENTRY32()
        
        entry.dwSize = sizeof(PROCESSENTRY32)
        snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, NULL)
        print(addressof(entry), hex(addressof(entry)))
        a = ULONG(addressof(entry))
        
        self.pid = -1
        
        if ctypes.windll.kernel32.Process32First(snapshot, pointer(entry)):   
            if entry.th32ProcessID not in skip_pids and entry.szExeFile in (b"Dolphin.exe", b"DolphinQt2.exe", b"DolphinWx.exe"):
                self.pid = entry.th32ProcessID 
            else:
                while ctypes.windll.kernel32.Process32Next(snapshot, pointer(entry)):
                    if entry.th32ProcessID in skip_pids:
                        continue
                    if entry.szExeFile in (b"Dolphin.exe", b"DolphinQt2.exe", b"DolphinWx.exe"):
                        self.pid = entry.th32ProcessID
        #MEM2 READING AND WRITING MOMENT | I DON'T KNOW HOW THIS WORKS!
        m_hDolphin = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION | PROCESS_VM_READ |PROCESS_VM_WRITE, False, self.pid);
        info = MEMORY_BASIC_INFORMATION()
        p = NULL
        i = 0
        while i < 5000:
            ctypes.windll.kernel32.VirtualQueryEx(m_hDolphin, ctypes.c_wchar_p(p), ctypes.byref(info), ctypes.sizeof(info))
            #print('regionSus', hex(info.RegionSize))
            if info.RegionSize == 0x4000000:
                self.memptr = ctypes.c_char_p(info.BaseAddress)
                self.memptrint = info.BaseAddress
                bytesRead = ctypes.c_ulong(0)
                print('regionSus located', hex(info.BaseAddress))
                ctypes.windll.kernel32.ReadProcessMemory(m_hDolphin, self.memptr, self.mem2, 0x3800000, ctypes.byref(bytesRead))
                self.m_hdolphinSUS = m_hDolphin
                if(self.mem2[:10] != b'\x02\x9f\x00\x10\x02\x9f\x003\x02\x9f'):
                    p += info.RegionSize
                    print("ohno")
                    continue
                print("amogus")
                break
            p += info.RegionSize
            i += 1
        #END OF MEM2 READING AND WRITING MOMENT
                    
            
        ctypes.windll.kernel32.CloseHandle(snapshot)
        
        if self.pid == -1:
            return False 
        
        return True
    
    def init_shared_memory(self):
        try:
            self.memory = shared_memory.SharedMemory('dolphin-emu.'+str(self.pid))
            return True
        except FileNotFoundError:
            return False
        
    #def read_ram(self, offset, size):
    #    return self.memory.buf[offset:offset+size]
    #brocoli's new read_ram moment which is terrible
    def read_ram(self, offset, size):
        if(offset >= 0x1<<28):
            offset -= 0x1<<28
            bytesRead = ctypes.c_ulong(0)
            ctypes.windll.kernel32.ReadProcessMemory(self.m_hdolphinSUS, self.memptr, self.mem2, 0x3800000, ctypes.byref(bytesRead))
            return self.mem2[offset:offset+size]
        return self.memory.buf[offset:offset+size]
    
    def write_ram(self, offset, data):
        self.memory.buf[offset:offset+len(data)] = data
    
    def read_uint32(self, addr):
        assert addr >= 0x80000000
        value = self.read_ram(addr-0x80000000, 4)

        return unpack(">I", value)[0]
    
    def write_uint32(self, addr, val):
        assert addr >= 0x80000000
        return self.write_ram(addr - 0x80000000, pack(">I", val))

    def read_float(self, addr):
        assert addr >= 0x80000000
        value = self.read_ram(addr - 0x80000000, 4)

        return unpack(">f", value)[0]

    def write_float(self, addr, val):
        assert addr >= 0x80000000
        return self.write_ram(addr - 0x80000000, pack(">f", val))

    
"""with open("ctypes.txt", "w") as f:
    for a in ctypes.__dict__:
        f.write(str(a))
        f.write("\n")"""

class xfbInfo:
    def __init__(self, gameId, width, height, xfbStarts, xfbSize):
        self.gameId = gameId
        self.width = width
        self.height = height
        self.xfbStarts = xfbStarts
        self.xfbSize = xfbSize
        
if __name__ == "__main__":
    dolphin = Dolphin()
    import multiprocessing 
    
    if dolphin.find_dolphin():

        print("Found Dolphin!")
    else:
        print("Didn't find Dolphin")

    print(dolphin.pid)
    
    dolphin.init_shared_memory()
    if dolphin.init_shared_memory():
        print("We found MEM1 and/or MEM2!")
    else:
        print("We didn't find it...")
    
    import random 
    randint = random.randint
    from timeit import default_timer
    
    start = default_timer()
    
    print("Testing Shared Memory Method")
    start = default_timer()
    gameid = dolphin.read_uint32(0x80000000)
    count = 500000
    for i in range(count):
        value = randint(0, 2**32-1)
        dolphin.write_uint32(0x80000000, value)
        
        result = dolphin.read_uint32(0x80000000)
        assert result == value
    diff = default_timer()-start 
    print(count/diff, "per sec")
    print("time: ", diff)
    dolphin.write_uint32(0x80000000, gameid)
    
    #BROCOLI STUPID CODE STARTS HERE
    import numpy as np
    import cv2
    import io
    import asyncio
    from PIL import ImageGrab
    
    xfbData = [xfbInfo('RMGE', 640, 456, [0, 0, 0], 0xa9600),
               xfbInfo('SB4E', 640, 456, [0, 0, 0], 0xa9600),
               xfbInfo('KB4E', 640, 456, [0, 0, 0], 0xa9600),
              xfbInfo('GMSE', 640, 448, [0], 0xa5000),
              xfbInfo('GQPE', 640, 456, [0], 0xf9600)]
    xfbActive = None
    for x in range(len(xfbData)):
        sus = dolphin.read_ram(0, 0x4)
        sus = chr(sus[0]) + chr(sus[1]) + chr(sus[2]) + chr(sus[3])
        if sus == xfbData[x].gameId:
            xfbActive = xfbData[x]
            break
    outputwidth = int((640)+640*0.5)
    outputheight = int((456)+456*0.5)
    def renderMain(windowName, xfbStartOverride=0, xfbVal=0, wOffset=0, hOffset=0):
        if xfbStartOverride == 0:
            xfbStartOverride = xfbActive.xfbStarts[xfbVal]
        xfbRead = io.BytesIO(dolphin.read_ram(xfbStartOverride, xfbActive.xfbSize)) 
            
        frame_len = int((xfbActive.width + wOffset) * (xfbActive.height + hOffset) * 2)
        shape = ((xfbActive.height + hOffset), (xfbActive.width + wOffset), 2)
        raw = xfbRead.read(int(frame_len))
        yuv = np.frombuffer(raw, dtype=np.uint8)
        yuv = yuv.reshape(shape)
        #yuv = cv2.resize(yuv, (0, 0), fx=0.5, fy=0.5)

        cv2.namedWindow(windowName, cv2.WINDOW_NORMAL)        # Create window with freedom of dimensions
        cv2.resizeWindow(windowName, outputwidth, outputheight)    
        bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB_YUY2)
        
        cv2.imwrite("amogus.jpg", bgr)
        
        cv2.imshow(windowName, bgr)
    
    xfbVal = 0
    if xfbActive.gameId == "GMSE":
        while True:
            sussy = dolphin.read_uint32(dolphin.read_uint32((dolphin.read_uint32(0x803e9700)+0x1c))+4)-0x80000000
            renderMain("SMS moment", sussy)
            cv2.waitKey(32)
    elif xfbActive.gameId == "SB4E" or xfbActive.gameId == "KB4E":
        while True:
            try:
                dolphin.write_uint32(0x807E5CA0, 1)
                sussy = dolphin.read_uint32((dolphin.read_uint32(0x807D62A0)+0x0))-0x80000000
                renderMain("SMG2 Player2", sussy)
                cv2.waitKey(32)
            except:
                pass
    elif xfbActive.gameId == 'GQPE':
        xfbActive.xfbStarts[0] = dolphin.read_uint32(0x803cbaf4)-0x80000000
        while True:
            renderMain("BFBB P2")
            cv2.waitKey(32)
    
