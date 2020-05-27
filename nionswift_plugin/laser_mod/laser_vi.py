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

    def virtual_thread(self, wavelength: float):
        logging.info("Sirah Credo Laser Virtual Instrument")
        time.sleep(2)
        logging.info("Sirah Credo Laser Virtual Instrument")
        self.sendmessage(1)

    def setWL(self, wavelength: float):
        threading.Thread(target=self.virtual_thread, args=(wavelength,)).start()
