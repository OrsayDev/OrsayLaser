from .NKTP_DLL import *
import logging

'''
print('Find modules on all existing and accessible ports - Might take a few seconds to complete.....')
if (getLegacyBusScanning()):
    print('Scanning following ports in legacy mode:', getAllPorts())
else:
    print('Scanning following ports in normal mode:', getAllPorts())

# Use the openPorts function with Auto & Live settings. This will scan and detect modules
# on all ports returned by the getAllPorts function.
# Please note that a port being in use by another application, will show up in this list but will
# not show any devices due to this port being inaccessible.
print(openPorts(getAllPorts(), 1, 1))

# All ports returned by the getOpenPorts function has modules (ports with no modules will automatically be closed)
print('Following ports has modules:', getOpenPorts())

# Traverse the getOpenPorts list and retrieve found modules via the deviceGetAllTypesV2 function
portlist = getOpenPorts().split(',')
for portName in portlist:
    result, devList = deviceGetAllTypesV2(portName)
    for devId in range(0, len(devList)):
        if (devList[devId] != 0):
            print('Comport:',portName,'Device type:',"0x%0.4X" % devList[devId],'at address:',devId)

#Read the serial number
# This is the SuperK Fianium
rdResult, FWVersionStr = registerReadAscii('COM5', 15, 0x65, -1)
print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))

# This is the SuperK Varia
rdResult, FWVersionStr = registerReadAscii('COM5', 16, 0x65, -1)
print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))

# This is the Ethernet
rdResult, FWVersionStr = registerReadAscii('COM5', 14, 0x65, -1)
print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))

# Setting the IP address
_ = registerWriteU8('COM5', 14, 0xb0, 192, 0)
_ = registerWriteU8('COM5', 14, 0xb0, 168, 1)
_ = registerWriteU8('COM5', 14, 0xb0, 0, 2)
_ = registerWriteU8('COM5', 14, 0xb0, 21, 3)

# Setting the gateway
_ = registerWriteU8('COM5', 14, 0xb1, 192, 0)
_ = registerWriteU8('COM5', 14, 0xb1, 168, 1)
_ = registerWriteU8('COM5', 14, 0xb1, 0, 2)
_ = registerWriteU8('COM5', 14, 0xb1, 200, 3)

# Setting the subnet
_ = registerWriteU8('COM5', 14, 0xb2, 255, 0)
_ = registerWriteU8('COM5', 14, 0xb2, 255, 1)
_ = registerWriteU8('COM5', 14, 0xb2, 255, 2)
_ = registerWriteU8('COM5', 14, 0xb2, 0, 3)

# Setting the dhcp
_ = registerWriteU8('COM5', 14, 0xb5, 1, 0)


# reading the IP address
_, ip0 = registerReadU8('COM5', 14, 0xb0, 0)
_, ip1 = registerReadU8('COM5', 14, 0xb0, 1)
_, ip2 = registerReadU8('COM5', 14, 0xb0, 2)
_, ip3 = registerReadU8('COM5', 14, 0xb0, 3)

# reading the gateway
_, g0 = registerReadU8('COM5', 14, 0xb1, 0)
_, g1 = registerReadU8('COM5', 14, 0xb1, 1)
_, g2 = registerReadU8('COM5', 14, 0xb1, 2)
_, g3 = registerReadU8('COM5', 14, 0xb1, 3)

# reading the subnet
_, sn0 = registerReadU8('COM5', 14, 0xb2, 0)
_, sn1 = registerReadU8('COM5', 14, 0xb2, 1)
_, sn2 = registerReadU8('COM5', 14, 0xb2, 2)
_, sn3 = registerReadU8('COM5', 14, 0xb2, 3)



_, port = registerReadU16('COM5', 14, 0xb4, -1)
_, dhcp = registerReadU8('COM5', 14, 0xb5, -1)

print('Reading IP adress version str:', ip0, ip1, ip2, ip3, port, dhcp)
print('Reading gateway version str:', g0, g1, g2, g3)
print('Reading subnet version str:', sn0, sn1, sn2, sn3)
'''

def init_ethernet_connection(name: str = 'EthernetPort1'):
    # Create the Internet port
    addResult = pointToPointPortAdd(name,
                                    pointToPointPortData('192.168.0.20', 10001, '192.168.0.21', 10001, 0, 100))
    print('Creating ethernet port', P2PPortResultTypes(addResult))

    getResult, portdata = pointToPointPortGet('EthernetPort1')
    print('Getting ethernet port', portdata, P2PPortResultTypes(getResult))

    # Open the Internet port
    # Not nessesary, but would speed up the communication, since the functions does
    # not have to open and close the port on each call
    openResult = openPorts(name, 0, 0)
    print('Opening the Ethernet port:', PortResultTypes(openResult))

    _, status0 = registerReadU8('COM5', 14, 0x66, 0)
    print('reading the status:', status0)

    # Example - Reading of the Firmware Revision register 0x64(regId) in ADJUSTIK at address 128(devId)
    # index = 2, because the str starts at byte index 2
    rdResult, FWVersionStr = registerReadAscii(name, 14, 0x65, -1)  # ethernet (0x81)
    print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))
    rdResult, FWVersionStr = registerReadAscii(name, 15, 0x65, -1)  # superK fianium (0x88)
    print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))
    rdResult, FWVersionStr = registerReadAscii(name, 16, 0x65, -1)  # superK varia (0x68)
    print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))

class SuperFianium:
    def __init__(self, connectionId):
        self.connectionId = connectionId
        self.interlock = True
        self.pulse_picker = 1

    # Emission Property
    @property
    def emission(self):
        return registerReadU8(self.connectionId, 15, 0x30, 0)

    @emission.setter
    def emission(self, value: int):
        rdResult = registerWriteU8(self.connectionId, 15, 0x30, value, 0)
        if rdResult != 0:
            logging.info('***LASER***: problem in setting emission')

    # Interlock Property
    @property
    def interlock(self):
        return bool(registerReadU8(self.connectionId, 15, 0x32, 0))

    @interlock.setter
    def interlock(self, value: bool):
        rdResult = registerWriteU8(self.connectionId, 15, 0x32, int(value), 0)
        if rdResult != 0:
            logging.info('***LASER***: problem in setting interlock')

    # Power Property
    @property
    def power(self):
        result, value = registerReadU16(self.connectionId, 15, 0x37, 0)
        if result != 0:
            logging.info('***LASER***: problem in reading power')
        return int(value / 10)

    @power.setter
    def power(self, value: int):
        rdResult = registerWriteU16(self.connectionId, 15, 0x37, int(value) * 10, 0)
        if rdResult != 0:
            logging.info('***LASER***: problem in setting power')

    # Pulse Picker Property
    @property
    def pulse_picker(self):
        result, value = registerReadU16(self.connectionId, 15, 0x34, 0)
        return value

    @pulse_picker.setter
    def pulse_picker(self, value: int):
        rdResult = registerWriteU16(self.connectionId, 15, 0x34, int(value), 0)
        if rdResult != 0:
            logging.info('***LASER***: problem in setting pulse picker')

    # NIM Delay Property
    @property
    def nim_delay(self):
        return registerReadU16(self.connectionId, 15, 0x39, 0)

    @nim_delay.setter
    def nim_delay(self, value: int):
        rdResult = registerWriteU16(self.connectionId, 15, 0x39, int(value), 0)
        if rdResult != 0:
            logging.info('***LASER***: problem in setting NIM delay')


class Varia():
    def __init__(self, connectionId):
        self.connectionId = connectionId


# fianium = SuperFianium('EthernetPort1')
# fianium.emission = 0
# fianium.power = 50
# print(fianium.power)
#
# # Close all ports
# closeResult = closePorts('')
# print('Close result: ', PortResultTypes(closeResult))

