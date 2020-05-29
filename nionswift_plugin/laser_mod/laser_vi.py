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
        latency = round(abs(float(final) - float(start))*1.0/20.0 + 0.1, 5)
        time.sleep(latency)
        logging.info(latency)
        self.sendmessage(2)

    def setWL(self, wavelength: float, current_wavelength: float):
        if (float(current_wavelength) == float(wavelength)):
            self.sendmessage(1)
        else:
            threading.Thread(target=self.set_startWL, args=(wavelength, current_wavelength)).start()

    def set_1posWL(self, cur_wavelength: float, step: float):
        self.laser_thread = threading.Thread(target=self.virtual_thread, args=(cur_wavelength, float(cur_wavelength)+float(step), 1))
        self.laser_thread.start()
    
    
    
    
    def abort_control(self):
        self.abort_ctrl = True

    def setWL_thread_locked(self):
        return self.lock.locked()

    def setWL_thread_release(self):
        self.lock.release()

    def setWL_thread_check(self):
        if self.thread==None:
            return False
        else:
            return self.thread.done()

    def setWL_thread(self, i_pts, step):
        if not self.abort_ctrl:
            self.lock.acquire()
            latency = round(float(step)*1.0/20.0+0.25, 5)
            time.sleep(latency)
            self.sendmessage(3)
            #self.lock.release()
        else:
            with self.lock:
                self.sendmessage(4)

    def set_scan(self, cur, step, pts):
        #with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            #executor.map(self.setWL_thread, range(3))

        self.abort_ctrl = False
        pool = ThreadPoolExecutor(1)
        for index in range(pts):
            self.thread = pool.submit(self.setWL_thread, index, step)
        
        self.setWL_thread_release()



