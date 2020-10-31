import sys
import time
import numpy

__author__ = "Yves Auad"

def _isPython3():
    return sys.version_info[0] >= 3

class TLPowerMeter:

    def __init__(self, which):
        self.id = which
        self.wl = 580.

    def pw_set_wl(self, cur_wl):
        self.wl=cur_wl
        return None

    def pw_read(self, wl):
        if abs(wl - self.wl) > 0.1:
            self.wl = wl
        a=-1.0
        val = a*wl**2-2*a*585*wl+585**2*a+100
        time.sleep(0.003)
        return abs(val + numpy.random.randn(1)[0])

    def pw_reset(self):
        time.sleep(0.01)

    def pw_set_avg(self, value):
        pass
