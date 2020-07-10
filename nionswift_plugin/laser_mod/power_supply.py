import serial
import sys
import time

__author__ = "Yves Auad"


def _isPython3():
    return sys.version_info[0] >= 3


def SENDMYMESSAGEFUNC(sendmessagefunc):
    return sendmessagefunc


class SpectraPhysics:

    def __init__(self, sendmessage):
        self.sendmessage = sendmessage
        self.pow = 20.
        self.control_thread = None
        self.ser = serial.Serial()
        self.ser.baudrate = 57600
        self.ser.port = 'COM11'
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.timeout = 1

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
            self.sendmessage(63)
            self.ser.write(mes.encode())
            self.ser.readline()  # clean buffer
            return None


