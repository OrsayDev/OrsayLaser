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
        self.sendmessage = sendmessage
        self.control_thread = None
        self.cur1 = b'1\n'
        self.cur2 = b'1\n'
        self.shutter = b'CLOSED\n'
        self.diode = b'OFF\n'
        self.q = b'OFF\n'

    def query(self, mes):
        if mes == '?C1\n':
            val = format(float(self.cur1.decode('UTF-8').replace('\n', '')) + 0.01 * numpy.random.randn(1)[0], '.2f')
            val = (str(val) + '\n').encode()
            return val
        if mes == '?C2\n':
            val = format(float(self.cur2.decode('UTF-8').replace('\n', '')) + 0.01 * numpy.random.randn(1)[0], '.2f')
            val = (str(val) + '\n').encode()
            return val
        if mes == '?SHT\n':
            return self.shutter
        if mes == '?D\n':
            return self.diode
        if mes == '?G\n':
            return self.q

    def comm(self, mes):
        if mes == 'SHT:1\n':
            self.shutter = b'OPEN\n'
        if mes == 'SHT:0\n':
            self.shutter = b'CLOSED\n'
        if 'C1' in mes:
            val = str(mes.replace("C1:", ""))
            self.cur1 = val.encode()
        if 'C2' in mes:
            val = str(mes.replace("C2:", ""))
            self.cur2 = val.encode()
        if mes == 'D:0\n':
            self.diode = b'OFF\n'
        if mes == 'D:1\n':
            self.diode = b'ON\n'
        if mes == 'G:0\n':
            self.q = b'OFF\n'
        if mes == 'G:1\n':
            self.q = b'ON\n'
        return None

    '''def pw_control_receive(self, cur):
        self.pow=round(cur/100., 2) #remember we need to divide by 100

    def pw_control_thread(self, arg):
        self.control_thread=threading.currentThread()
        while getattr(self.control_thread, "do_run", True):
            self.comm('C1:'+str(self.pow)+'\n')
            self.comm('C2:'+str(self.pow)+'\n')
            time.sleep(0.1)
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
        self.control_thread.do_run=False'''
