import serial
import sys
import time

__author__ = "Yves Auad"


def _isPython3():
    return sys.version_info[0] >= 3

class SpectraPhysics:

    def __init__(self, SERIAL_PORT='COM11'):
        self.pow = 20.
        self.control_thread = None
        self.ser = serial.Serial()
        self.ser.baudrate = 57600
        self.ser.port = SERIAL_PORT
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.timeout = 1

        self.cur1 = b'0.10\n'
        self.cur2 = b'0.10\n'
        self.shutter = b'CLOSED\n'
        self.diode = b'OFF\n'
        self.q = b'OFF\n'
        self.t1 = b'26.00\n'
        self.t2 = b'34.00\n'

        try:
            if not self.ser.is_open:
                self.ser.open()
            self.successful = True
        except:
            print('***POWER SUPPLY***: Could not open serial port.')
            self.successful = False

        self.ser.write('D:0\n'.encode())
        self.ser.readline()

        self.ser.write('G:0\n'.encode())
        self.ser.readline()

        self.ser.write('C1:00.10\n'.encode())
        self.ser.readline()

        self.ser.write('C2:00.10\n'.encode())
        self.ser.readline()

        self.ser.write('Q:0\n'.encode())
        self.ser.readline()

    def flush(self):
        self.ser.flush()

    def query(self, mes):
        try:
            self.ser.write(mes.encode())
            answ = self.ser.readline()
            if mes=='?SHT\n':
                self.shutter = answ
            elif mes=='?T2\n':
                self.t2 = answ
            elif mes=='?T1\n':
                self.t1=answ
            elif mes=='?D\n':
                self.diode=answ
            elif mes=='?G\n':
                self.q=answ
            elif mes=='?C1\n':
                self.cur1 = answ
            elif mes=='?C2\n':
                self.cur2 = answ
            return answ
        except:
            self.ser.close()
            time.sleep(0.05)
            self.ser.open()
            time.sleep(0.05)
            self.ser.write(mes.encode())
            return self.ser.readline()

    def comm(self, mes):
        try:
            self.ser.write(mes.encode())
            self.ser.readline()  # clean buffer
            return None
        except:
            self.ser.write(mes.encode())
            self.ser.readline()  # clean buffer
            return None


