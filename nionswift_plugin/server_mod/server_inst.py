# standard libraries
from nion.utils import Event
from nion.utils import Observable

import threading
import numpy
import socket

GREEN = (numpy.ones((15, 25), dtype=numpy.uint32)) * 2000000000
RED = (numpy.ones((15, 25), dtype=numpy.uint32)) * 4000000000

class serverDevice(Observable.Observable):
    def __init__(self):
        self.property_changed_event = Event.Event()

        self.on_time = 0.02

        self.__colorLaser = RED
        self.__colorPM0 = RED
        self.__colorPM1 = RED
        self.__colorPS = RED
        self.__colorArd = RED

    def init(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect(('127.0.0.1', 65432))
        self.s.sendall('bc'.encode())
        data = self.s.recv(512)

        if data == b'bc':
            return True
        else:
            return False

    def off(self, which):
        if which=='LASER':
            self.color_laser = 'red'
        elif which=='PM0':
            self.color_pm0 = 'red'
        elif which=='PM1':
            self.color_pm1 = 'red'
        elif which=='PS':
            self.color_ps = 'red'
        elif which=='ARD':
            self.color_ard = 'red'

    def loop(self):
        threading.Thread(target=self.read, args=(),).start()

    def read(self):
        data = self.s.recv(512)
        if b'LASER' in data:
            self.color_laser='green'
        if b'POWER_SUPPLY' in data:
            self.color_ps='green'
        if b'POWERMETER0' in data:
            self.color_pm0='green'
        if b'POWERMETER1' in data:
            self.color_pm1='green'
        if b'ARDUINO' in data:
            self.color_ard='green'
        self.loop()

    @property
    def color_laser(self):
        return self.__colorLaser

    @color_laser.setter
    def color_laser(self, value):
        if value=='red':
            self.__colorLaser = RED
        else:
            self.__colorLaser = GREEN
            threading.Timer(self.on_time, self.off, args=(['LASER'])).start()
        self.property_changed_event.fire("color_laser")

    @property
    def color_pm0(self):
        return self.__colorPM0

    @color_pm0.setter
    def color_pm0(self, value):
        if value == 'red':
            self.__colorPM0 = RED
        else:
            self.__colorPM0 = GREEN
            threading.Timer(self.on_time, self.off, args=(['PM0'])).start()
        self.property_changed_event.fire('color_pm0')

    @property
    def color_pm1(self):
        return self.__colorPM1

    @color_pm1.setter
    def color_pm1(self, value):
        if value=='red':
            self.__colorPM1 = RED
        else:
            self.__colorPM1 = GREEN
            threading.Timer(self.on_time, self.off, args=(['PM1'])).start()
        self.property_changed_event.fire('color_pm1')

    @property
    def color_ps(self):
        return self.__colorPS

    @color_ps.setter
    def color_ps(self, value):
        if value=='red':
            self.__colorPS = RED
        else:
            self.__colorPS = GREEN
            threading.Timer(self.on_time, self.off, args=(['PS'])).start()
        self.property_changed_event.fire('color_ps')

    @property
    def color_ard(self):
        return self.__colorArd

    @color_ard.setter
    def color_ard(self, value):
        if value=='red':
            self.__colorArd = RED
        else:
            self.__colorArd = GREEN
            threading.Timer(self.on_time, self.off, args=(['ARD'])).start()
        self.property_changed_event.fire('color_ard')