# standard libraries
from nion.utils import Event
from nion.utils import Observable

import threading
import numpy
import socket
import logging

GREEN = (numpy.ones((15, 25), dtype=numpy.uint32)) * 4044400440
RED = (numpy.ones((15, 25), dtype=numpy.uint32)) * 4000400000

class serverDevice(Observable.Observable):
    def __init__(self):
        self.property_changed_event = Event.Event()

        self.on_time = 0.01

        self.__serverStatus = RED
        self.__Laser = [RED, RED]
        self.__PM0 = [RED, RED]
        self.__PM1 = [RED, RED]
        self.__PS = [RED, RED]
        self.__Ard = [RED, RED]

    def init(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.s.connect(('129.175.82.159', 65432))
            self.s.sendall('bc'.encode())
            data = self.s.recv(512)
            if data == b'bc':
                self.server_status = 'green'
                logging.info('***SERVER STATUS***: Auxiliary client connected.')
                return True
        except:
            self.server_status = 'red'
            logging.info('***SERVER STATUS***: Auxiliary client not connect. Check server.')
            return False

    def off(self, which):
        if which=='laser_rx':
            self.laser_rx = 'red'
        elif which=='laser_tx':
            self.laser_tx = 'red'

        elif which=='pm0_rx':
            self.pm0_rx = 'red'
        elif which == 'pm0_tx':
            self.pm0_tx = 'red'

        elif which=='pm1_rx':
            self.pm1_rx = 'red'
        elif which=='pm1_tx':
            self.pm1_tx = 'red'

        elif which=='ps_rx':
            self.ps_rx = 'red'
        elif which=='ps_tx':
            self.ps_tx = 'red'

        elif which=='ard_rx':
            self.ard_rx = 'red'
        elif which=='ard_tx':
            self.ard_tx = 'red'

    def loop(self):
        threading.Thread(target=self.read, args=(),).start()

    def read(self):
        data = self.s.recv(512)
        if b'LASERRX' in data:
            self.laser_rx='green'
        if b'LASERTX' in data:
            self.laser_tx='green'

        if b'POWER_SUPPLYRX' in data:
            self.ps_rx='green'
        if b'POWER_SUPPLYTX' in data:
            self.ps_tx='green'

        if b'POWERMETER0RX' in data:
            self.pm0_rx='green'
        if b'POWERMETER0TX' in data:
            self.pm0_tx='green'

        if b'POWERMETER1RX' in data:
            self.pm1_rx='green'
        if b'POWERMETER1TX' in data:
            self.pm1_tx='green'

        if b'ARDUINORX' in data:
            self.ard_rx='green'
        if b'ARDUINOTX' in data:
            self.ard_tx='green'

        if data:
            self.loop()

    @property
    def server_status(self):
        return self.__serverStatus

    @server_status.setter
    def server_status(self, value):
        if value == 'red':
            self.__serverStatus = RED
        else:
            self.__serverStatus = GREEN
        self.property_changed_event.fire('server_status')

    @property
    def laser_rx(self):
        return self.__Laser[0]

    @laser_rx.setter
    def laser_rx(self, value):
        if value=='red':
            self.__Laser[0] = RED
        else:
            self.__Laser[0] = GREEN
            threading.Timer(self.on_time, self.off, args=(['laser_rx'])).start()
        self.property_changed_event.fire("laser_rx")

    @property
    def laser_tx(self):
        return self.__Laser[1]

    @laser_tx.setter
    def laser_tx(self, value):
        if value == 'red':
            self.__Laser[1] = RED
        else:
            self.__Laser[1] = GREEN
            threading.Timer(self.on_time, self.off, args=(['laser_tx'])).start()
        self.property_changed_event.fire("laser_tx")

    @property
    def pm0_rx(self):
        return self.__PM0[0]

    @pm0_rx.setter
    def pm0_rx(self, value):
        if value == 'red':
            self.__PM0[0] = RED
        else:
            self.__PM0[0] = GREEN
            threading.Timer(self.on_time, self.off, args=(['pm0_rx'])).start()
        self.property_changed_event.fire('pm0_rx')

    @property
    def pm0_tx(self):
        return self.__PM0[1]

    @pm0_tx.setter
    def pm0_tx(self, value):
        if value == 'red':
            self.__PM0[1] = RED
        else:
            self.__PM0[1] = GREEN
            threading.Timer(self.on_time, self.off, args=(['pm0_tx'])).start()
        self.property_changed_event.fire('pm0_tx')

    @property
    def pm1_rx(self):
        return self.__PM1[0]

    @pm1_rx.setter
    def pm1_rx(self, value):
        if value == 'red':
            self.__PM1[0] = RED
        else:
            self.__PM1[0] = GREEN
            threading.Timer(self.on_time, self.off, args=(['pm1_rx'])).start()
        self.property_changed_event.fire('pm1_rx')

    @property
    def pm1_tx(self):
        return self.__PM1[1]

    @pm1_tx.setter
    def pm1_tx(self, value):
        if value == 'red':
            self.__PM1[1] = RED
        else:
            self.__PM1[1] = GREEN
            threading.Timer(self.on_time, self.off, args=(['pm1_tx'])).start()
        self.property_changed_event.fire('pm1_tx')

    @property
    def ps_rx(self):
        return self.__PS[0]

    @ps_rx.setter
    def ps_rx(self, value):
        if value=='red':
            self.__PS[0] = RED
        else:
            self.__PS[0] = GREEN
            threading.Timer(self.on_time, self.off, args=(['ps_rx'])).start()
        self.property_changed_event.fire('ps_rx')

    @property
    def ps_tx(self):
        return self.__PS[1]

    @ps_tx.setter
    def ps_tx(self, value):
        if value == 'red':
            self.__PS[1] = RED
        else:
            self.__PS[1] = GREEN
            threading.Timer(self.on_time, self.off, args=(['ps_tx'])).start()
        self.property_changed_event.fire('ps_tx')


    @property
    def ard_rx(self):
        return self.__Ard[0]

    @ard_rx.setter
    def ard_rx(self, value):
        if value=='red':
            self.__Ard[0] = RED
        else:
            self.__Ard[0] = GREEN
            threading.Timer(self.on_time, self.off, args=(['ard_rx'])).start()
        self.property_changed_event.fire('ard_rx')

    @property
    def ard_tx(self):
        return self.__Ard[1]

    @ard_tx.setter
    def ard_tx(self, value):
        if value == 'red':
            self.__Ard[1] = RED
        else:
            self.__Ard[1] = GREEN
            threading.Timer(self.on_time, self.off, args=(['ard_tx'])).start()
        self.property_changed_event.fire('ard_tx')