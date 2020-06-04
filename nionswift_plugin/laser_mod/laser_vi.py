import sys
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

__author__ = "Yves Auad"

def _isPython3():
    return sys.version_info[0] >= 3

def SENDMYMESSAGEFUNC(sendmessagefunc):
    return sendmessagefunc

class SirahCredoLaser:

    def __init__(self, sendmessage)->None:
        self.sendmessage=sendmessage
        self.abort_ctrl = False
        self.laser_thread = None
        self.thread = None
        self.lock=threading.Lock()

    def set_startWL(self, start: float, final: float):
        latency = round(abs(final - start)*1.0/20.0 + 0.25, 5)
        time.sleep(latency)
        self.sendmessage(2)

    def setWL(self, wavelength: float, current_wavelength: float):
        if (float(current_wavelength) == float(wavelength)):
            self.sendmessage(1)
        else:
            self.laser_thread = threading.Thread(target=self.set_startWL, args=(wavelength, current_wavelength))
            self.laser_thread.start()
            self.laser_thread.join() #this thread has a join() which means you wait until it finishes

    
    
    
    
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

    def set_scan_thread(self, i_pts, step):
        if not self.abort_ctrl:
            self.lock.acquire()
            latency = round(float(step)*1.0/20.0+0.25, 5)
            time.sleep(latency)
            self.sendmessage(3)
        else:
            with self.lock:
                self.sendmessage(4)

    def set_scan(self, cur, step, pts):
        self.abort_ctrl = False
        pool = ThreadPoolExecutor(1)
        for index in range(pts+1):
            self.thread = pool.submit(self.set_scan_thread, index, step)
        
        self.set_scan_thread_release()



