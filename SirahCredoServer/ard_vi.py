
import sys
import time
import threading

__author__ = "Yves Auad"


def _isPython3():
    return sys.version_info[0] >= 3

class Arduino:

    def __init__(self):
        self.pos = b'0'
        self.control_thread = None
        self.successful = True

    def get_pos(self):
        a = int(self.pos.decode())
        return a

    def set_pos(self, position):
        if position > 180:
            return None
        if position < 0:
            return None

        self.pos = (str(position)).encode()
        return None

    def wobbler_on(self, current, intensity):
        self.wobbler_thread = threading.Thread(target=self.wobbler_loop, args=(current, intensity), )
        self.wobbler_thread.start()

    def wobbler_loop(self, current, intensity):
        self.wobbler_thread = threading.currentThread()
        while getattr(self.wobbler_thread, "do_run", True):
            if getattr(self.wobbler_thread, "do_run", True): time.sleep(1. / 2)
            self.set_pos(current - intensity)
            if getattr(self.wobbler_thread, "do_run", True): time.sleep(1. / 2)
            self.set_pos(current)

    def wobbler_off(self):
        self.wobbler_thread.do_run = False
