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
        self.cur=b'0.10\n'
        self.shutter=b'CLOSED\n'
		
    def query(self, mes):
        if mes=='?C1\n' or mes=='?C2\n':
            return self.cur
            #return float(self.cur)+0.1*numpy.random.randn(1)[0]
        if mes=='?SHT\n':
            return self.shutter
		
    def comm(self, mes):
        if mes=='SHT:1\n':
            self.shutter=b'OPEN\n'
        if mes=='SHT:0\n':
            self.shutter=b'CLOSED\n'
        if 'C1' in mes:
            val=str(mes.replace("C1:", ""))
            self.cur=val.encode()
        return None
		
		
