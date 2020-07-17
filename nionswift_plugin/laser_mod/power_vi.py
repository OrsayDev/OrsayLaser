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
        self.wl = 580.


    def pw_set_wl(self, cur_wl):
        self.wl=cur_wl
        return None

    def pw_read(self):
        a=-1.0
        val = a*self.wl**2-2*a*585*self.wl+585**2*a+100
        return (val + numpy.random.randn(1)[0])
