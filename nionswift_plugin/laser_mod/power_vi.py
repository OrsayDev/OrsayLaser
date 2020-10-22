import sys
import time
import numpy

__author__ = "Yves Auad"

def _isPython3():
    return sys.version_info[0] >= 3

def SENDMYMESSAGEFUNC(sendmessagefunc):
    return sendmessagefunc

class TLPowerMeter:

    def __init__(self, sendmessage, which):
        self.sendmessage=sendmessage
        self.id = which
        self.wl = 580.


    def pw_set_wl(self, cur_wl):
        self.wl=cur_wl
        return None

    def pw_read(self):
        a=-1.0
        val = a*self.wl**2-2*a*585*self.wl+585**2*a+100
        return (val + numpy.random.randn(1)[0])

    def pw_reset(self):
        time.sleep(0.01)
        self.sendmessage(25)
