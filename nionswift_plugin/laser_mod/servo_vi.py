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
		
