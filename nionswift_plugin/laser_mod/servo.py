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
        self.pow=20.
        self.control_thread=None
        self.ser = serial.Serial()
        self.ser.baudrate=9600
        self.ser.port='COM15'
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.bytesize=serial.EIGHTBITS
        self.ser.timeout=2
		
        try:
            if not self.ser.is_open:
                self.ser.open()
                time.sleep(0.5)
        except:
            self.sendmessage(81)
		
        self.ser.readline()
		
 
    def get_pos(self):
        try:
            self.ser.write(b'?POS\n')		
            return self.ser.readline()
        except:
            self.sendmessage(82)
            self.ser.flush()
            self.ser.write(b'?POS\n')		
            return self.ser.readline()
		
    def set_pos(self, position):
        if position>180:
            self.sendmessage(84)
            return None
        if position<0:
            self.sendmessage(85)
            return None
        try:
            self.ser.write(('POS:'+str(position)+'\n').encode())
            return None
        except:
            self.sendmessage(83)
            self.ser.flush()
            self.ser.write(('POS:'+str(position)+'\n').encode())
            return None            
		
