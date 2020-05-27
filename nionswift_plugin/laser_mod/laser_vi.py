import sys
import logging
import time
import threading

__author__ = "Yves Auad"

def _isPython3():
    return sys.version_info[0] >= 3

def SENDMYMESSAGEFUNC(sendmessagefunc):
    return sendmessagefunc

class SirahCredoLaser:

    def __init__(self, sendmessage:callable)->None:
        #logging.info(sendmessage)
        self.sendmessage=sendmessage

    def virtual_thread(self, start: float, final: float, stepping: int):
        latency = abs(float(final) - float(start))*1.0/20.0 + 2.0
        time.sleep(latency)
        logging.info(latency)
        if (stepping == 1):
            self.sendmessage(3)
        if (stepping == 0):
            self.sendmessage(2)

    def setWL(self, wavelength: float, current_wavelength: float):
        if (float(current_wavelength) == float(wavelength)):
            self.sendmessage(1)
        else:
            threading.Thread(target=self.virtual_thread, args=(wavelength, current_wavelength, 0)).start()

    def set_1posWL(self, cur_wavelength: float, step: float):
        threading.Thread(target=self.virtual_thread, args=(cur_wavelength, float(cur_wavelength)+float(step), 1)).start()

