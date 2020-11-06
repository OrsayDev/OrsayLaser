import serial
import sys
import time
import threading

__author__ = "Yves Auad"


def _isPython3():
    return sys.version_info[0] >= 3

class Arduino:

    def __init__(self, SERIAL_PORT='COM15'):
        self.pow = 20.
        self.control_thread = None
        self.ser = serial.Serial()
        self.ser.baudrate = 9600
        self.ser.port = SERIAL_PORT
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.timeout = 2

        try:
            if not self.ser.is_open:
                self.ser.open()
                self.ser.readline()
            self.successful = True
        except:
            print("***ARDUINO***: Could not open serial port.")
            self.successful = False


    def get_pos(self):
        self.ser.write(b'?POS\n')
        a = self.ser.readline()
        try:
            return int(a.decode())
        except:
            return 'None'

    def set_pos(self, position):
        if position > 180:
            return None
        if position < 0:
            return None
        try:
            self.ser.write(('POS:' + str(position) + '\n').encode())
            return None
        except:
            self.ser.flush()
            self.ser.write(('POS:' + str(position) + '\n').encode())
            return None

    def wobbler_on(self, current, intensity):
        self.wobbler_thread = threading.Thread(target=self.wobbler_loop, args=(current, intensity), )
        self.wobbler_thread.start()

    def wobbler_loop(self, current, intensity):
        self.wobbler_thread = threading.currentThread()
        while getattr(self.wobbler_thread, "do_run", True):
            if getattr(self.wobbler_thread, "do_run", True): time.sleep(1. / 2)
            self.set_pos(current - intensity)
            if getattr(self.wobbler_thread, "do_run", True): time.sleep(1. / 2)
            self.set_pos(current)

    def wobbler_off(self):
        self.wobbler_thread.do_run = False
