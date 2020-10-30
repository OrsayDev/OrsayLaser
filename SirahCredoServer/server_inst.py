# standard libraries
from nion.utils import Event
from nion.utils import Observable
from nion.swift.model import HardwareSource

import time
import threading

import numpy
import socket

class serverDevice(Observable.Observable):
    def __init__(self):
        self.property_changed_event = Event.Event()

        self.__laser = False

    def init(self):
        self.osc = False
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect(('127.0.0.1', 65432))
        self.s.sendall('bc'.encode())
        data = self.s.recv(512)
        if data == b'bc':
            return True
        else:
            return False

    def loop(self):
        threading.Thread(target=self.read, args=(),).start()

    def read(self):
        time.sleep(0.02)
        self.laser_blink=False
        data = self.s.recv(512)
        if b'query' in data:
            self.laser_blink=True
        self.loop()

    @property
    def laser_blink(self):
        if self.__laser:
            return 'x'
        else:
            return 'o'

    @laser_blink.setter
    def laser_blink(self, value):
        self.__laser = value
        print(value)
        self.property_changed_event.fire('laser_blink')