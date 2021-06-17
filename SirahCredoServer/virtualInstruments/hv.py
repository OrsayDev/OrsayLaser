import socket
import logging

__author__ = "Yves Auad"

class HVDeflector():
    def __init__(self, ip="129.175.82.70", port = 80):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(1)
        self.successful = False
        try:
            self.s.connect((ip, port))
            self.successful = True
        except:
            logging.info(f"***HV Deflector***: Could not connect socket at {(ip, port)}.")

    def set_voltage(self, v):
        try:
            veff = int(v/10)
            plus = ('HV+ ' + str(veff)).encode()
            less = ('HV+ ' + str(veff)).encode()
            self.s.sendall(plus)
            self.s.sendall(less)
            return 200
        except:
            return 0

    def get_voltage(self):
        try:
            self.s.sendall(b"HV:MON?")
            data = sock.recv(512)
            index1 = data.find(b'+')
            index2 = data.find(b'%', index1)

            index3 = data.find(b'-')
            index4 = data.find(b'%', index3)
            return (int(data[index1+1:index2]), int(data[index3+1:index4]))
        except:
            return (-1, -1)


