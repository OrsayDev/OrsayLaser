import serial
import sys
import time
import numpy

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
        self.ser.timeout = 0.2

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

        mes = '?SHT\n'; self.ser.write(mes.encode()); self.shutter=self.ser.readline()
        mes = '?T2\n'; self.ser.write(mes.encode()); self.t2 = self.ser.readline()
        mes = '?T1\n'; self.ser.write(mes.encode()); self.t1 = self.ser.readline()
        mes = '?D\n'; self.ser.write(mes.encode()); self.diode = self.ser.readline()
        mes = '?G\n'; self.ser.write(mes.encode()); self.q = self.ser.readline()
        mes = '?C1\n'; self.ser.write(mes.encode()); self.cur1 = self.ser.readline()
        mes = '?C2\n'; self.ser.write(mes.encode()); self.cur2 = self.ser.readline()

        init_cur1 = float(self.cur1.decode('UTF-8').replace('\n', ''))
        init_cur2 = float(self.cur2.decode('UTF-8').replace('\n', ''))

        self.handle_start(init_cur1, init_cur2)

        self.ser.write('D:0\n'.encode())
        self.ser.readline()

        self.ser.write('G:0\n'.encode())
        self.ser.readline()

        self.ser.write('Q:0\n'.encode())
        self.ser.readline()

    def handle_start(self, init_c1, init_c2):
        for cur_val in numpy.linspace(init_c1, 0.10, 10):
            cur_val = format(float(cur_val), '.2f')
            self.comm('C1:' + str(cur_val) + '\n')
            self.comm('C2:' + str(cur_val) + '\n')
            time.sleep(2.0)


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
            else:
                print('***POWER SUPPLY***: Unknown message.')
            return answ
        except:
            print(f'***POWER SUPPLY***: Could not write/read in laser serial port. Check port.')
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


