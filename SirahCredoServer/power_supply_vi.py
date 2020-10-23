import sys
import numpy

__author__ = "Yves Auad"


def _isPython3():
    return sys.version_info[0] >= 3

class SpectraPhysics:

    def __init__(self):
        self.control_thread = None
        self.cur1 = b'1\n'
        self.cur2 = b'1\n'
        self.shutter = b'CLOSED\n'
        self.diode = b'OFF\n'
        self.q = b'OFF\n'
        self.t1 = b'26.00\n'
        self.t2 = b'34.00\n'

        self.sucessfull = True

    def query(self, mes):
        if mes == '?C1\n':
            val = format(float(self.cur1.decode('UTF-8').replace('\n', '')) + 0.01 * numpy.random.randn(1)[0], '.2f')
            val = (str(val) + '\n').encode()
            return val
        if mes == '?C2\n':
            val = format(float(self.cur2.decode('UTF-8').replace('\n', '')) + 0.01 * numpy.random.randn(1)[0], '.2f')
            val = (str(val) + '\n').encode()
            return val
        if mes == '?T1\n':
            val = format(float(self.t1.decode('UTF-8').replace('\n', '')) + 0.01 * numpy.random.randn(1)[0], '.2f')
            val = (str(val) + '\n').encode()
            return val
        if mes == '?T2\n':
            val = format(float(self.t2.decode('UTF-8').replace('\n', '')) + 0.01 * numpy.random.randn(1)[0], '.2f')
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

