import serial
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

class servoMotor:

    def __init__(self, sendmessage):
        self.sendmessage=sendmessage
        self.pos=b'0'
        self.control_thread=None
		
    def get_pos(self):
        return self.pos
		
    def set_pos(self, position):
        if position>180:
            self.sendmessage(84)
            return None
        if position<0:
            self.sendmessage(85)
            return None

        self.pos=(str(position)).encode()
        return None            
		

    def wobbler_on(self, current, intensity):
        self.wobbler_thread = threading.Thread(target=self.wobbler_loop, args=(current, intensity),)
        self.wobbler_thread.start()

    def wobbler_loop(self, current, intensity):
        self.wobbler_thread = threading.currentThread()
        while getattr(self.wobbler_thread, "do_run", True):
            if getattr(self.wobbler_thread, "do_run", True): time.sleep(1./2)
            self.set_pos(current-intensity)
            if getattr(self.wobbler_thread, "do_run", True): time.sleep(1./2)
            self.set_pos(current)
    
    def wobbler_off(self):
        self.wobbler_thread.do_run=False
