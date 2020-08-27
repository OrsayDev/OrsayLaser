import socket
import threading
import sys
import logging
import time
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

__author__ = "Yves Auad" 

class ServerSirahCredoLaser:

    def __init__(self):
        print("***SERVER***: Initializing Server...")
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(('127.0.0.1', 65432))
        self.s.listen(5)

        self.abort_ctrl = False
        self.laser_thread = None
        self.thread = None
        self.thread_wl = 575.0
        self.lock=threading.Lock()

    def set_hardware_wl(self, wl):
        self.thread_wl=wl
        latency = round(float(5)*1.0/20.0+ 0.5*abs(numpy.random.randn(1)[0])   , 5)
        time.sleep(latency)

    def get_hardware_wl(self):
        return (self.thread_wl, 0)

    def set_startWL(self, wl: float, cur_wl: float):
        self.thread_wl=wl
        latency = round(abs(cur_wl - wl)*1.0/20.0 + 0.25, 5)
        time.sleep(latency)
        time.sleep(5)
        #return b'message_02'
        #self.sendmessage(2)

    def setWL(self, wavelength: float, current_wavelength: float):
        if (float(current_wavelength) == float(wavelength)):
            #self.sendmessage(1)
            return b'message_01'
        else:
            self.laser_thread = threading.Thread(target=self.set_startWL, args=(wavelength, current_wavelength))
            self.laser_thread.start()
            return b'message_02'

    def abort_control(self):
        self.abort_ctrl = True

    def set_scan_thread_locked(self):
        return self.lock.locked()

    def set_scan_thread_release(self):
        self.lock.release()

    def set_scan_thread_check(self):
        if self.thread==None:
            return True #if there is none then its done
        else:
            return self.thread.done()

    def set_scan_thread_hardware_status(self):
        if self.lock.locked():
            return 2 #motor holding. You can avance
        else:
            self.sendmessage(3)
            return 3 #motor moving. Do not avance
    
    def set_scan_thread(self, cur, i_pts, step):
        if not self.abort_ctrl:
            self.lock.acquire()
            self.set_hardware_wl(cur+i_pts*step)
        else:
            with self.lock:
                logging.info("Laser abort control function.")
                self.sendmessage(4)
                #return b'message_04'

    def set_scan(self, cur: float, step: float, pts: int):
        self.abort_ctrl = False
        pool = ThreadPoolExecutor(1)
        for index in range(pts):
            self.thread = pool.submit(self.set_scan_thread, cur, index, step)

    def main_loop(self):
        while True:
            clientsocket, adress = self.s.accept()
            print(f"Connection from {adress} has been stablished.")
            with clientsocket:
                while True:
                    data = clientsocket.recv(512)
                    if not data:
                        break

                    print(data)

                    if b"set_hardware_wl" in data:                 #set_hardware_wl(self, wl). no return
                        if data[15:19] == bytes(4):
                            wl = float(data[19: 35].decode()) #16 bytes
                            self.set_hardware_wl(wl)
                            return_data = 'None'.encode()
                    
                    if b"get_hardware_wl" in data:                 #get_hardware_wl(self). return
                        if data[15:19] == bytes(4):
                            return_data = format(self.get_hardware_wl()[0], '.8f').rjust(16, '0').encode()
                    
                    if b"setWL" in data:                           #setWL(self, wavelength: float, current_wavelength: float). no return
                        if data[5:9] == bytes(4) and data[25:29] == bytes(4):
                            wl = float(data[9:25].decode()) #16 bytes
                            cur_wl = float(data[29:45].decode()) # 16 bytes
                            return_data = self.setWL(wl, cur_wl)

                    
                    if b"abort_control" in data:                   #abort_control(self). No return
                        if data[13:17] == bytes(4):
                            self.abort_control()
                            return_data = 'None'.encode()
                    
                    if b"set_scan_thread_locked" in data:                 #set_scan_thread_locked(self). return
                        if data[22:26] == bytes(4):
                            return_data = self.set_scan_thread_locked()
                            if return_data:
                                return_data = b'1'
                            else:
                                return_data = b'0'
                    
                    if b"set_scan_thread_release" in data:         #set_scan_thread_release(self). no return
                        if data[23:27] == bytes(4):
                            self.set_scan_thread_release()
                            return_data = 'None'.encode()
                    
                    if b"set_scan_thread_check" in data:           #set_scan_thread_check(self). return
                        if data[21:25] == bytes(4):
                            return_data = self.set_scan_thread_check()
                            if return_data:
                                return_data = b'1'
                            else:
                                return_data = b'0'

                    if b"set_scan_thread_hardware_status" in data: #set_scan_thread_hardware_status(self). return
                        if data[31:35] == bytes(4):
                            return_data = self.set_scan_thread_hardware_status()
                            if return_data == 2:
                                return_data = b'2'
                            else:
                                return_data = b'3'
                    
                    if b"set_scan" in data:                        #set_scan(self, cur, step, pts). no return
                        if data[8:12] == bytes(4) and data[28:32] == bytes(4) and data[48:52] == bytes(4):
                            cur = float(data[12:28].decode()) #16 bytes
                            step = float(data[32:48]) #16 bytes
                            pts = int(data[52:60]) #8 bytes
                            return_data = 'None'.encode()
                        
                    clientsocket.sendall(return_data)

s = ServerSirahCredoLaser()
s.main_loop()
