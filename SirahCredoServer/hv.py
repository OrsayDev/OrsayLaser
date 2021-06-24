"""
Available Requests

*IDN? -> Name and version of the project
IP? -> Return the IP
IP:ALL? -> Return the IP and the gateway
MAC? -> Return the MAC address
ETH? -> Return the state of the Ethernet connection
CMD? -> Return the state of the control (if manual or remote)
HV:DAC? -> Return the % of the DAC control
HV:BOX? -> Return the % of the manual control
HV:REM? -> Return the % of the values read by the HV Supply
HV:MON? -> Return the % of the values from the HV supply output

Available Configurations

CMD:BOX -> Put it in manual control
CMD:COM -> Put it in remote control (default)
HV+ X -> Configure the V+ in %. X must be an integer. 100% is approximately 1000V
HV- X -> Configure the V- in %. X must be an integer. 100% is approximately 1000V
ETH:OFF -> Deactivate the ethernet connection
ETH:DHCP -> Configure the ethernet connection using DHCP
ETH:IP ip:port mask gateway -> Configure the connection using a fix IP address. Default values are
    192.168.1.25:80 255.255.255.0 192.168.1.0

Notes

i) Ethernet configurations are saved and will be loaded when HV box is powered on.
ii) HV box on power on sets both HV outputs to zero.

"""


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

    def set_voltage(self, v, which='b'):
        """

        :param v: Voltage, in V.
        :param which: Polarization of the voltage. V+ is p. V- is n. Both is b.
        :return:
        """
        try:
            veff = int(v/10)
            if v>1000:
                logging.info(f"***HV Deflector***: Voltage must be less than 1000V. No action taken.")
                return
            if which=='p':
                msg = ('HV+ ' + str(veff) + '\n').encode()
            elif which=='n':
                msg = ('HV- ' + str(veff) + '\n').encode()
            elif which=='b':
                msg = ('HV+ ' + str(veff) + '\n' + 'HV- ' + str(veff)).encode()
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