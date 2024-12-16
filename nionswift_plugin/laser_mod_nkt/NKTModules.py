from .NKTP_DLL import *
import logging, time, threading

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

# def init_ethernet_connection(name: str = 'EthernetPort1',
#                              ip_host: str = '192.168.0.20', ip_laser: str = '192.168.0.21', port = 10001):
#     # Create the Internet port
#     addResult = pointToPointPortAdd(name,
#                                     pointToPointPortData(ip_host, port, ip_laser, port, 0, 100))
#     logging.info(f'***NKT CH***: Creating ethernet port {P2PPortResultTypes(addResult)}.')
#
#     getResult, portdata = pointToPointPortGet('EthernetPort1')
#     logging.info(f'***NKT CH***: Getting ethernet port. {portdata} and {P2PPortResultTypes(getResult)}.')
#
#     # Open the Internet port
#     # Not nessesary, but would speed up the communication, since the functions does
#     # not have to open and close the port on each call
#     openResult = openPorts(name, 0, 0)
#     logging.info(f'***NKT CH***: Opening the Ethernet port: {PortResultTypes(openResult)}.')
#
#     _, status0 = registerReadU8(name, 14, 0x66, 0)
#     logging.info(f'***NKT CH***: reading the status: {status0}.')
#
#     # Example - Reading of the Firmware Revision register 0x64(regId) in ADJUSTIK at address 128(devId)
#     # index = 2, because the str starts at byte index 2
#     rdResult, FWVersionStr = registerReadAscii(name, 14, 0x65, -1)  # ethernet (0x81)
#     print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))
#     #rdResult, FWVersionStr = registerReadAscii(name, 15, 0x65, -1)  # superK fianium (0x88)
#     #print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))
#     #rdResult, FWVersionStr = registerReadAscii(name, 16, 0x65, -1)  # superK varia (0x68)
#     #print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))

class ConnectionHandler():
    def __init__(self, connectionId, ip_host: str = '192.168.1.33',
                 ip_laser: str = '192.168.1.45', port = 10001):
        self.connectionId = connectionId
        self.__lock = threading.Lock()
        if 'COM' in connectionId:
            openResult = openPorts(self.connectionId, 0, 0)
            logging.info(f'***NKT CH***: Opening the comport: {PortResultTypes(openResult)}.')
        else:
            # Create the Internet port
            addResult = pointToPointPortAdd(self.connectionId,
                                            pointToPointPortData(ip_host, port, ip_laser, port, 0, 100))
            logging.info(f'***NKT CH***: Creating ethernet port {P2PPortResultTypes(addResult)}.')

            getResult, portdata = pointToPointPortGet(self.connectionId)
            logging.info(f'***NKT CH***: Getting ethernet port. {portdata} and {P2PPortResultTypes(getResult)}.')

            # Open the Internet port
            # Not nessesary, but would speed up the communication, since the functions does
            # not have to open and close the port on each call
            openResult = openPorts(self.connectionId, 0, 0)
            logging.info(f'***NKT CH***: Opening the Ethernet port: {PortResultTypes(openResult)}.')

            _, status0 = registerReadU8(self.connectionId, 14, 0x66, 0)
            logging.info(f'***NKT CH***: reading the status: {status0}.')

            # Example - Reading of the Firmware Revision register 0x64(regId) in ADJUSTIK at address 128(devId)
            # index = 2, because the str starts at byte index 2
            #rdResult, FWVersionStr = registerReadAscii(self.connectionId, 14, 0x65, -1)  # ethernet (0x81)
            #print('Reading firmware version str:', FWVersionStr, RegisterResultTypes(rdResult))

    def check_instruments(self):
        logging.info('Find modules on all existing and accessible ports - Might take a few seconds to complete.....')
        if (getLegacyBusScanning()):
            logging.info(f'Scanning following ports in legacy mode: {getAllPorts()}.')
        else:
            logging.info(f'Scanning following ports in normal mode: {getAllPorts()}.')

        # Use the openPorts function with Auto & Live settings. This will scan and detect modules
        # on all ports returned by the getAllPorts function.
        # Please note that a port being in use by another application, will show up in this list but will
        # not show any devices due to this port being inaccessible.
        logging.info(openPorts(getAllPorts(), 1, 1))

        # All ports returned by the getOpenPorts function has modules (ports with no modules will automatically be closed)
        logging.info(f'Following ports has modules: {getOpenPorts()}.')

        # Traverse the getOpenPorts list and retrieve found modules via the deviceGetAllTypesV2 function
        portlist = getOpenPorts().split(',')
        for portName in portlist:
            result, devList = deviceGetAllTypesV2(portName)
            for devId in range(0, len(devList)):
                if devList[devId] != 0:
                    logging.info(f'Comport: {portName}. Device type: {devList[devId]} at address: {devId}.')


    def readU16(self, which: str, instrument_id: int, register: int, offset: int = 0):
        with self.__lock:
            result, value = registerReadU16(self.connectionId, instrument_id, register, offset)
            if result != 0:
                logging.info(f'***LASER***: problem in reading {which}. Error {RegisterResultTypes(result)}.')
            return value

    def writeU16(self, which: str, instrument_id: int, register: int, value: int, offset: int = 0):
        with self.__lock:
            result = registerWriteU16(self.connectionId, instrument_id, register, value, offset)
            if result != 0:
                logging.info(f'***LASER***: problem in writing {which}. Error {RegisterResultTypes(result)}.')

    def readU8(self, which: str, instrument_id: int, register: int, offset: int = 0):
        with self.__lock:
            result, value = registerReadU8(self.connectionId, instrument_id, register, offset)
            if result != 0:
                logging.info(f'***LASER***: problem in reading {which}. Error {RegisterResultTypes(result)}.')
            return value

    def writeU8(self, which: str, instrument_id: int, register: int, value: int, offset: int = 0):
        with self.__lock:
            result = registerWriteU8(self.connectionId, instrument_id, register, value, offset)
            if result != 0:
                logging.info(f'***LASER***: problem in writing {which}. Error {RegisterResultTypes(result)}.')

    def readASCII(self, which: str, instrument_id: int, register: int, offset: int = 0):
        with self.__lock:
            result, value = registerReadAscii(self.connectionId, instrument_id, register, offset)
            if result != 0:
                logging.info(f'***LASER***: problem in reading ASCII {which}. Error {RegisterResultTypes(result)}.')
                return 'None'
            return value

class SuperFianium:
    def __init__(self, connetionHandler: ConnectionHandler):
        self.connetionHandler = connetionHandler
        self.interlock = True
        self.pulse_picker = 2

    def ping(self):
        return self.connetionHandler.readASCII('ping', 15, 0x65, 0)

    # Emission Property
    @property
    def emission(self):
        return self.connetionHandler.readU8('emission', 15, 0x30)

    @emission.setter
    def emission(self, value: int):
        self.connetionHandler.writeU8('emission', 15, 0x30, value, 0)

    # Interlock Property
    @property
    def interlock(self):
        return self.connetionHandler.readU8('interlock', 15, 0x32)

    @interlock.setter
    def interlock(self, value: bool):
        self.connetionHandler.writeU8('interlock', 15, 0x32, int(value), 0)

    # Power Property
    @property
    def power(self):
        return self.connetionHandler.readU16('power', 15, 0x37) / 10

    @power.setter
    def power(self, value: int):
        self.connetionHandler.writeU16('power', 15, 0x37, int(value) * 10, 0)

    # Pulse Picker Property
    @property
    def pulse_picker(self):
        return self.connetionHandler.readU16('pulse picker', 15, 0x34)

    @pulse_picker.setter
    def pulse_picker(self, value: int):
        self.connetionHandler.writeU16('pulse picker', 15, 0x34, int(value), 0)

    # NIM Delay Property
    @property
    def nim_delay(self):
        return self.connetionHandler.readU16('nim delay', 15, 0x39)

    @nim_delay.setter
    def nim_delay(self, value: int):
        self.connetionHandler.writeU16('nim delay', 15, 0x39, int(value), 0)


class Varia():
    def __init__(self, connectionHandler: ConnectionHandler):
        self.connetionHandler = connectionHandler

    def ping(self):
        return self.connetionHandler.readASCII('ping', 16, 0x65, 0)

    # Filter setpoint 1. The neutral density filter
    @property
    def filter_setpoint1(self):
        return self.connetionHandler.readU16('filter setpoint1', 16, 0x32) / 10

    @filter_setpoint1.setter
    def filter_setpoint1(self, value: int):
        self.connetionHandler.writeU16('filter setpoint1', 16, 0x32, int(value) * 10, 0)

    # Filter setpoint 2. This is SWP (short-wave-pass filter)
    @property
    def filter_setpoint2(self):
        return self.connetionHandler.readU16('filter setpoint2', 16, 0x33) / 10

    @filter_setpoint2.setter
    def filter_setpoint2(self, value: int):
        self.connetionHandler.writeU16('filter setpoint1', 16, 0x33, int(value) * 10, 0)

    # Filter setpoint 3. This is the LWP (long-wave-pass filter)
    @property
    def filter_setpoint3(self):
        return self.connetionHandler.readU16('filter setpoint3', 16, 0x34) / 10

    @filter_setpoint3.setter
    def filter_setpoint3(self, value: int):
        self.connetionHandler.writeU16('filter setpoint3', 16, 0x34, int(value) * 10, 0)

    def read_status_bits(self):
        return self.connetionHandler.readU16('status bit', 16, 0x66)

    def given_status_bits(self, bit: int):
        status = self.read_status_bits()
        return (status >> bit) & 1

    def filter_moving(self):
        status = self.read_status_bits()
        filter1_moving = (status >> 12) & 1
        filter2_moving = (status >> 13) & 1
        filter3_moving = (status >> 14) & 1
        return filter1_moving or filter2_moving or filter3_moving

class RFDriver():
    def __init__(self, connection_handler: ConnectionHandler):
        self.connection_handler = connection_handler