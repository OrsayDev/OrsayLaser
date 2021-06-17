import socket
import logging

__author__ = "Yves Auad"

class HVDeflector():
    def __init__(self):

        self.successful = False
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(0.1)
            self.s.connect(("192.168.1.37", 80))
            self.successful = True
            logging.info(f"***HV Deflector***: Connected in ChromaTEM.")
        except socket.timeout:
            try:
                self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.s.settimeout(0.1)
                self.s.connect(("129.175.82.70", 80))
                self.successful = True
                logging.info(f"***HV Deflector***: Connected in VG Lumiere.")
            except:
                self.successful = False
                logging.info(f"***HV Deflector***: Fast blanker HV was not found. Check for hardware.")

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
            self.s.sendall(b"HV:MON?\n"); data = self.s.recv(512)
            i1 = data.find(b'+'); i2 = data.find(b'%', i1)
            i3 = data.find(b'-'); i4 = data.find(b'%', i3)
            return (int(data[i1+1:i2]), int(data[i3+1:i4]))
        except:
            logging.info(f"***HV Deflector***: Could not query voltage.")
            return (-1, -1)


