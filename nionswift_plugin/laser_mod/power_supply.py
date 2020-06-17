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
        self.pow=20.
        self.control_thread=None
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
		
        self.ser.write('D:0\n'.encode())
        self.ser.readline()
		
        self.ser.write('G:0\n'.encode())
        self.ser.readline()

        self.ser.write('C1:00.10\n'.encode())
        self.ser.readline()

        self.ser.write('C2:00.10\n'.encode())
        self.ser.readline()
		
        self.ser.write('Q:10000\n'.encode())
        self.ser.readline()
		
		
    def flush(self):
        self.ser.flush()
		
    def query(self, mes):
        try:
            self.ser.write(mes.encode())		
            return self.ser.readline()
        except:
            self.sendmessage(62)
            self.ser.flush()
            self.ser.write(mes.encode())
            return self.ser.readline()
		
    def comm(self, mes):
        try:
            self.ser.write(mes.encode())
            self.ser.readline() #clean buffer
            return None
        except:
            self.sendmessage(63)
            self.ser.flush()
            self.ser.write(mes.encode())
            self.ser.readline() #clean buffer
            return None            
		
    def pw_control_receive(self, cur):
        self.pow=round(cur/100., 2) #remeber we need to divide by 100

    def pw_control_thread(self, arg):
        self.control_thread=threading.currentThread()
        while getattr(self.control_thread, "do_run", True):
            self.comm('C1:'+str(self.pow)+'\n')
            self.comm('C2:'+str(self.pow)+'\n')
            time.sleep(0.1)
            logging.info(self.pow)
            self.sendmessage(79)

    def pw_control_thread_check(self):
        try:
            return getattr(self.control_thread, "do_run")
        except:
            return False

    def pw_control_thread_on(self):
        self.control_thread=threading.Thread(target=self.pw_control_thread, args=("task",))
        self.control_thread.do_run=True
        self.control_thread.start()

    def pw_control_thread_off(self):
        self.control_thread.do_run=False
