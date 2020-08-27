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
        print(self.thread_wl)
        latency = round(float(5)*1.0/20.0+ 0.5*abs(numpy.random.randn(1)[0])   , 5)
        time.sleep(latency)

    def get_hardware_wl(self):
        return (self.thread_wl, 0)

    def set_startWL(self, wl: float, cur_wl: float):
        self.thread_wl=wl
        latency = round(abs(cur_wl - wl)*1.0/20.0 + 0.25, 5)
        time.sleep(latency)
        time.sleep(5)
        self.sendmessage(2)

    def setWL(self, wavelength: float, current_wavelength: float):
        if (float(current_wavelength) == float(wavelength)):
            self.sendmessage(1)
        else:
            self.laser_thread = threading.Thread(target=self.set_startWL, args=(wavelength, current_wavelength))
            self.laser_thread.start()


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
            return 2 #motor holding. You can advance
        else:
            self.sendmessage(3)
            return 3 #motor moving. Dont advance boys
    
    def set_scan_thread(self, cur, i_pts, step):
        if not self.abort_ctrl:
            self.lock.acquire()
            self.set_hardware_wl(cur+i_pts*step)
        else:
            with self.lock:
                logging.info("Laser abort control function.")
                self.sendmessage(4)

    def set_scan(self, cur, step, pts):
        self.abort_ctrl = False
        pool = ThreadPoolExecutor(1)
        for index in range(pts):
            self.thread = pool.submit(self.set_scan_thread, cur, index, step)

    def dummy_function(self, data_in, data_out):
        return bytes(data_out)


    def main_loop(self):
        while True:
            clientsocket, adress = self.s.accept()
            print(f"Connection from {adress} has been stablished.")
            with clientsocket:
                while True:
                    data = clientsocket.recv(1024)
                    if not data:
                        break

                    if b"dummy_function" in data:
                        return_data = self.dummy_function(data, 4)
                        print(return_data)

                    if b"set_hardware_wl" in data:                 #set_hardware_wl(self, wl):
                        if data[15:19] == bytes(4):
                            wl = data[19: 19+16]
                            self.set_hardware_wl(wl)
                            return_data = 'None'.encode()
                    if b"get_hardware_wl" in data:                 #get_hardware_wl(self):
                        if data[15:19] == bytes(4):
                            return_data = format(self.get_hardware_wl()[0], '.8f').rjust(16, '0').encode()
                            print(return_data)
                    if b"set_startWL" in data:                     #set_startWL(self, wl: float, cur_wl: float):
                        if data[11:15] == bytes(4):
                            pass
                    if b"setWL" in data:                           #setWL(self, wavelength: float, current_wavelength: float):
                        if data[5:9] == bytes(4):
                            pass
                    if b"abort_control" in data:                   #abort_control(self):
                        if data[13:17] == bytes(4):
                            pass
                    if b"set_scan_thread_locked" in data:                 #set_scan_thread_locked(self):
                        if data[22:26] == bytes(4):
                            pass
                    if b"set_scan_thread_release" in data:         #set_scan_thread_release(self):
                        if data[23:27] == bytes(4):
                            pass
                    if b"set_scan_thread_check" in data:           #set_scan_thread_check(self):
                        if data[21:25] == bytes(4):
                            pass
                    if b"set_scan_thread_hardware_status" in data: #set_scan_thread_hardware_status(self):
                        if data[31:35] == bytes(4):
                            pass
                    if b"set_scan_thread" in data:                 #set_scan_thread(self, cur, i_pts, step):
                        if data[15:19] == bytes(4):
                            pass
                    if b"set_scan" in data:                        #set_scan(self, cur, step, pts):
                        if data[8:12] == bytes(4):
                            pass
                        
                    clientsocket.sendall(return_data)

s = ServerSirahCredoLaser()
s.main_loop()
