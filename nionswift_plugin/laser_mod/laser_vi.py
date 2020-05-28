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
        self.ctrl = False
        self.laser_thread = None
        self.__lock=threading.Lock()

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


    def change_control(self):
        self.ctrl = not self.ctrl

    def set_1posWL(self, cur_wavelength: float, step: float):
        self.laser_thread = threading.Thread(target=self.virtual_thread, args=(cur_wavelength, float(cur_wavelength)+float(step), 1))
        self.laser_thread.start()

    def setWL_thread(self, i_pts, step):
        if not self.ctrl:
            with self.__lock:
                latency = round(float(step)*1.0/20.0+0.1, 5)
                time.sleep(latency)
                self.sendmessage(3)
        else:
            self.sendmessage(4)

    def set_scan(self, cur, step, pts):
        #self.laser_thread = threading.Thread(target=self.setWL_thread, args=(cur, float(cur)+float(step))).start()

        #with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        #    for index in range(3):
        #        executor.submit(self.setWL_thread, 1)
            #executor.map(self.setWL_thread, range(3))
        self.ctrl = False
        pool = ThreadPoolExecutor(1)
        for index in range(pts):
            pool.submit(self.setWL_thread, index, step)




