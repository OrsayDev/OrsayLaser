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

class SpectraPhysics:

    def __init__(self, sendmessage):
        self.sendmessage=sendmessage
        self.ser = serial.Serial()
        self.ser.baudrate=57600
        self.ser.port='COM11'
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.bytesize=serial.EIGHTBITS
        self.ser.timeout=1
		
        try:
            if not self.ser.is_open:
                self.ser.open()
                time.sleep(0.5)
        except:
            self.sendmessage(61)
		

    def query(self, mes):
        self.ser.write(mes.encode())		
        return self.ser.readline()
		
    def comm(self, mes):
        self.ser.write(mes.encode())
        self.ser.readline() #clean buffer
        return None
		
		
