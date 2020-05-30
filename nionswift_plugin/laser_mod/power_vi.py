import sys
import logging
import time
import threading
import numpy
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

__author__ = "Yves Auad"

def _isPython3():
    return sys.version_info[0] >= 3

def SENDMYMESSAGEFUNC(sendmessagefunc):
    return sendmessagefunc

class TLPowerMeter:

    def __init__(self, sendmessage):
        self.sendmessage=sendmessage
        self.pwthread = None

    def pw_random_periodic(self):
        self.pwthread = threading.Timer(0.5, self.pw_random_periodic) #auto execution
        self.pwthread.start()
        self.sendmessage(100)
