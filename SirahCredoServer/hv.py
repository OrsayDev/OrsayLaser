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
        except socket.timeout:
            logging.info(f"***HV Deflector***: Timeout. Could not connect socket at {(ip, port)}.")
        except:
            logging.info(f"***HV Deflector***: Could not connect socket at {(ip, port)}. Check for issues.")

    def set_voltage(self, v):
        try:
            veff = int(v/10)
            msg = ('HV+ ' + str(veff)+'\n'+'HV- ' + str(veff)).encode()
            self.s.sendall(msg)
            return 200
        except:
            logging.info(f"***HV Deflector***: Problem setting voltage.")
            return 0

    def get_voltage(self):
        try:
            self.s.sendall(b"HV:MON?"); data = sock.recv(512)
            i1 = data.find(b'+'); i2 = data.find(b'%', i1)
            i3 = data.find(b'-'); i4 = data.find(b'%', i3)
            return (int(data[i1+1:i2]), int(data[i3+1:i4]))
        except:
            logging.info(f"***HV Deflector***: Could not query voltage.")
            return (-1, -1)


