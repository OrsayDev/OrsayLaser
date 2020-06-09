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


    def pw_set_wl(self, cur_WL):
        return None

    def pw_read(self):
        return numpy.random.randn(1)[0]
