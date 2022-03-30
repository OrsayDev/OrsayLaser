# standard libraries
from nion.utils import Event
from nion.utils import Observable
from nion.swift.model import HardwareSource

import logging
import threading
import time
import numpy
import socket

from SirahCredoServer import power
from SirahCredoServer import hv

#from Modules import Kinesis_PMC

from . import control_routine as ctrlRout

def SENDMYMESSAGEFUNC(sendmessagefunc):
    return sendmessagefunc

class LaserServerHandler():

    def __init__(self, callback, CHOST, CPORT, which = 'None'):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((CHOST, CPORT))
        self.s.settimeout(None)
        self.callback = callback
        self.name = which.encode()
        self.on = True
        self.s.sendall(which.encode())
        data = self.s.recv(512)
        time.sleep(0.05)

    def server_ping(self):
        try:
            header = b'server_ping'
            msg = header
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() == 'Server Alive':
                logging.info('***NS CLIENT***: Server ON.')
                return True
            else:
                return False
        except ConnectionResetError:
            self.connection_error_handler()
            return False
        except:
            return False

    def shutdown(self):
        self.on = False
        self.s.close()

    def connection_error_handler(self):
        self.shutdown()
        self.callback(666)

    ## Sirah Credo Laser Function

    def set_hardware_wl(self, wl):
        try:
            header = b'set_hardware_wl'
            msg = header + bytes(4)
            msg = msg + format(wl, '.8f').rjust(16, '0').encode()
            msg = msg + bytes(4)
            msg = msg + b'LASER'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***NS CLIENT***: Bad communication. Error 01.')
        except ConnectionResetError:
            self.connection_error_handler()

    def get_hardware_wl(self):
        try:
            header = b'get_hardware_wl'
            msg = header + bytes(4)
            msg = msg + b'LASER'
            self.s.sendall(msg)
            data = self.s.recv(512)
            data=data[:-9]
            return (float(data.decode()), 0)
        except ConnectionResetError:
            self.connection_error_handler()
            #this is pump laser wavelength and show us there is an error
            return (532.000, 0)

    def setWL(self, wl, cur_wl):
        try:
            header = b'setWL'
            msg = header + bytes(4)
            msg = msg + format(wl, '.8f').rjust(16, '0').encode()
            msg = msg + bytes(4)
            msg = msg + format(cur_wl, '.8f').rjust(16, '0').encode()
            msg = msg + bytes(4)
            msg = msg + b'LASER'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data[:-9] == b'message_01':
                return 1
            elif data[:-9] == b'message_02':
                return 2
            else:
                logging.info('***NS CLIENT***: Bad communication. Error 03.')
                return None
        except ConnectionResetError:
            self.connection_error_handler()
            return None

    def abort_control(self):
        try:
            header = b'abort_control'
            msg = header + bytes(4)
            msg = msg + b'LASER'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***NS CLIENT***: Bad communication. Error 04.')
        except ConnectionResetError:
            self.connection_error_handler()

    def set_scan_thread_locked(self):
        try:
            header = b'set_scan_thread_locked'
            msg = header + bytes(4)
            msg = msg + b'LASER'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data[:-9] == b'1':
                return True
            elif data[:-9] == b'0':
                return False
            else:
                logging.info('***NS CLIENT***: Bad communication. Error 05.')
                return False
        except ConnectionResetError:
            self.connection_error_handler()
            return False

    def set_scan_thread_release(self):
        try:
            header = b'set_scan_thread_release'
            msg = header + bytes(4)
            msg = msg + b'LASER'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***NS CLIENT***: Bad communication. Error 06.')
        except ConnectionResetError:
            self.connection_error_handler()

    def set_scan_thread_check(self):
        try:
            header = b'set_scan_thread_check'
            msg = header + bytes(4)
            msg = msg + b'LASER'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data[:-9] == b'1':
                return True
            elif data[:-9] == b'0':
                return False
            else:
                logging.info('***NS CLIENT***: Bad communication. Error 07.')
        except ConnectionResetError:
            self.connection_error_handler()

    def set_scan_thread_hardware_status(self):
        try:
            header = b'set_scan_thread_hardware_status'
            msg = header + bytes(4)
            msg = msg + b'LASER'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data[:-9] == b'2':
                return 2
            elif data[:-9] == b'3':
                logging.info(
                    "***NS CLIENT***: Laser Motor is moving. You can not change wavelength while last one is still "
                    "moving. Please increase camera dwell time or # of averages in order to give time to our slow "
                    "hardware.")
                return 3
            else:
                logging.info('***NS CLIENT***: Bad communication. Error 08.')
                return None
        except ConnectionResetError:
            self.connection_error_handler()
            return None

    def set_scan(self, cur, step, pts):
        try:
            header = b'set_scan'
            msg = header + bytes(4)
            msg = msg + format(cur, '.8f').rjust(16, '0').encode()
            msg = msg + bytes(4)
            msg = msg + format(step, '.8f').rjust(16, '0').encode()
            msg = msg + bytes(4)
            msg = msg + format(pts, '.0f').rjust(8, '0').encode()  # int is 8 bytes here
            msg = msg + bytes(4)
            msg = msg + b'LASER'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***NS CLIENT***: Bad communication. Error 09.')
        except ConnectionResetError:
            self.connection_error_handler()

    ## POWER SUPPLY RELATED FUNCTIONS ##

    def query(self, my_message):
        try:
            header = b'query'
            msg = header + bytes(3) #power supply sends 00-00-00
            msg = msg + my_message.encode()
            msg = msg + bytes(3)
            msg = msg + b'POWER_SUPPLY'
            self.s.sendall(msg)
            data = self.s.recv(512)
            return data[:-15]
        except ConnectionResetError:
            self.connection_error_handler()

    def comm(self, my_message):
        try:
            header = b'comm'
            msg = header + bytes(3) #power supply sends 00-00-00
            msg = msg + my_message.encode()
            msg = msg + bytes(3)
            msg = msg + b'POWER_SUPPLY'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***NS CLIENT***: Bad communication. Error 12.') #must return None
        except ConnectionResetError:
            self.connection_error_handler()

    ## POWER METER RELATED FUNCTIONS ##

    def pw_read(self, which, wl):
        try:
            header = b'pw_read'+which.encode()
            msg = header + bytes(5) #power meter sends 00-00-00-00-00
            msg = msg + format(wl, '.8f').rjust(16, '0').encode()
            msg = msg + bytes(5)
            msg = msg + b'POWERMETER'+which.encode()
            self.s.sendall(msg)
            data = self.s.recv(512)
            return float(data[:-16].decode())
        except ConnectionResetError:
            self.connection_error_handler()

    def pw_reset(self, which):
        try:
            header = b'pw_reset'+which.encode()
            msg = header + bytes(5) #power supply sends 00-00-00-00-00
            msg = msg + b'POWERMETER'+which.encode()
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***NS CLIENT***: Bad communication. Error 14.') #must return None
        except ConnectionResetError:
            self.connection_error_handler()

    def pw_set_avg(self, avg, which):
        try:
            header = b'pw_set_avg'+which.encode()
            msg = header + bytes(5) #power supply sends 00-00-00-00-00
            msg = msg + format(avg, '.0f').rjust(8, '0').encode() # 8 bytes for int
            msg = msg + bytes(5)
            msg = msg + b'POWERMETER'+which.encode()
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***NS CLIENT***: Bad communication. Error 15.') #must return None
        except ConnectionResetError:
            self.connection_error_handler()

    def get_pos(self):
        try:
            header = b'get_pos'
            msg = header + bytes(6) #power supply sends 00-00-00-00-00-00
            msg = msg + b'ARDUINO'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode():
                return int(data[:-13].decode())
            else:
                return 0
        except ConnectionResetError:
            self.connection_error_handler()

    def set_pos(self, pos):
        try:
            header = b'set_pos'
            msg = header + bytes(6) #power supply sends 00-00-00-00-00-00
            msg = msg + format(pos, '.0f').rjust(8, '0').encode() # 8 bytes for int
            msg = msg + bytes(6)
            msg = msg + b'ARDUINO'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***NS CLIENT***: Bad communication. Error 16.') #must return None
        except ConnectionResetError:
            self.connection_error_handler()

    def wobbler_on(self, pos, step):
        try:
            header = b'wobbler_on'
            msg = header + bytes(6) #power supply sends 00-00-00-00-00-00
            msg = msg + format(pos, '.0f').rjust(8, '0').encode() # 8 bytes for int
            msg = msg + bytes(6)
            msg = msg + format(step, '.0f').rjust(8, '0').encode() # 8 bytes for int
            msg = msg + bytes(6)
            msg = msg + b'ARDUINO'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***NS CLIENT***: Bad communication. Error 17.') #must return None
        except ConnectionResetError:
            self.connection_error_handler()

    def wobbler_off(self):
        try:
            header = b'wobbler_off'
            msg = header + bytes(6) #power supply sends 00-00-00-00-00-00
            msg = msg + b'ARDUINO'
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***NS CLIENT***: Bad communication. Error 18.') #must return None
        except ConnectionResetError:
            self.connection_error_handler()


class gainDevice(Observable.Observable):

    def __init__(self):
        self.property_changed_event = Event.Event()
        self.free_event = Event.Event()
        self.communicating_event = Event.Event()
        self.busy_event = Event.Event()

        self.call_monitor = Event.Event()
        self.call_data = Event.Event()
        self.append_monitor_data = Event.Event()
        self.append_data = Event.Event()
        self.end_data_monitor = Event.Event()
        self.end_data = Event.Event()

        #below is related to handling an unexpected server shutdown
        self.server_shutdown = Event.Event()

        # this is related to the images taken periodically
        self.det_acq = Event.Event()

        self.__start_wav = 575.0
        self.__finish_wav = 595.0
        self.__step_wav = 1.0
        self.__pts = int((self.__finish_wav - self.__start_wav) / self.__step_wav + 1)
        self.__avg = 10
        self.__tpts = int(self.__avg * self.__pts)
        self.__power = 0.
        self.__power02 = 0.
        self.__power_transmission = 0.
        self.__power_ref = 0.
        self.__cubeRT = 10
        self.__autoLock = True
        self.__tdc_status = False
        self.__diode = 0.10
        self.__servo_pos = 0
        self.__servo_pos_initial = self.__servo_pos
        self.__servo_pts = 0
        self.__servo_wobbler = False
        self.__ctrl_type = 1
        self.__delay = 1000 * 1e-9
        self.__width = 250 * 1e-9
        self.__fb_status = False
        self.__counts = 0
        self.__frequency = 5000
        self.__acq_number = 0  # this is a strange variable. This measures how many gain acquire you did in order to
        # create new displays every new acquisition
        self.__powermeter_avg = 10
        self.__servo_step = 2
        self.__nper_pic = 0
        self.__dye = 0
        self.__host = "127.0.0.1"
        self.__port = 65432
        self.__hv = 0
        self.__hvAbs = [0, 0]
        self.__hvRatio = 0
        self.__piezoStep = 100
        self.__mpos = [0, 0, 0, 0]

        self.__camera = None
        self.__data = None

        self.__thread = None
        self.__status = True #we start it true because before init everything must be blocked. We free after a succesfull init
        self.__abort_force = False
        self.__power_ramp = False
        self.__bothPM = False
        self.__per_pic = True
        self.__per_pic = True

        self.__serverLaser = None
        self.__serverPM = [None, None]
        self.__serverPS = None
        self.__serverArd = None

        #self.__piezoMotor = Kinesis_PMC.TLKinesisPiezoMotorController('97101311', pollingTime=100, TIMEOUT=3.0)
        #if not self.__piezoMotor:
        #    logging.info('***LASER***: Piezo motor was not detected. Using the simulation piezo.')
        #self.__mpos = self.__piezoMotor.GetCurrentPositionAll()

        self.__control_sendmessage = ctrlRout.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__controlRout = ctrlRout.controlRoutine(self.__control_sendmessage)

        self.__OrsayScanInstrument = None
        self.__camera = None

        self.__DEBUG = False

    def server_instrument_ping(self):
        self.__serverLaser.server_ping()

    def server_instrument_shutdown(self):
        for server in [self.__serverLaser, self.__serverPM[0], self.__serverPS, self.__serverArd]:
            server.shutdown()

    def init(self):
        #Looking for orsay_camera_eels. If not, check orsay_camera_tp3. If not, grab usim
        for hards in HardwareSource.HardwareSourceManager().hardware_sources:  # finding eels camera. If you don't
            # find, use usim eels
            if hasattr(hards, 'hardware_source_id'):
                if hards.hardware_source_id == "orsay_camera_kuro":
                    self.__camera = hards

        if self.__camera == None:
            for hards in HardwareSource.HardwareSourceManager().hardware_sources:  # finding eels camera. If you dont
                # find, use usim eels
                if hasattr(hards, 'hardware_source_id'):
                    if hards.hardware_source_id == 'orsay_camera_timepix3':
                        self.__camera = hards

        if self.__camera == None:
            for hards in HardwareSource.HardwareSourceManager().hardware_sources:  # finding eels camera. If you dont
                # find, use usim eels
                if hasattr(hards, 'hardware_source_id'):
                    if hards.hardware_source_id == 'orsay_camera_eels':
                        self.__camera = hards

        if self.__camera == None:
            for hards in HardwareSource.HardwareSourceManager().hardware_sources:  # finding eels camera. If you dont
                # find, use usim eels
                if hasattr(hards, 'hardware_source_id'):
                    if hards.hardware_source_id == 'usim_eels_camera':
                        self.__camera = hards

        if not self.__camera:
            logging.info('***LASER***: No camera was found.')
        else:
            logging.info(f'***LASER***: Camera {self.__camera.hardware_source_id} properly loaded. EELS/EEGS acquistion is good to go.')

        self.__OrsayScanInstrument = HardwareSource.HardwareSourceManager().get_hardware_source_for_hardware_source_id(
            "orsay_scan_device")
        if not self.__OrsayScanInstrument:
            logging.info('***LASER***: Could not find SCAN module. Check for issues.')
            logging.info('***LASER***: If usim available, grabbing usim Scan Device.')
            self.__OrsayScanInstrument = HardwareSource.HardwareSourceManager().get_hardware_source_for_hardware_source_id(
                "usim_scan_device")
            if not self.__OrsayScanInstrument: logging.info(
                '***LASER***: Could not find USIM SCAN module. Check nionswift website for instructions.')

            # # CLARITY: # self.__OrsayScanInstrument is the same as the way I did with the camera. If i have put a
            # if hards.hardware_source_id == "usim_scan_device": self.__scan = hards, the dir(self.__scan) and dir(
            # self.__OrsayScanInstrument) are identical

        else:
            logging.info('***LASER***: SCAN module properly loaded.')

        self.__laser_message = SENDMYMESSAGEFUNC(self.sendMessageFactory())

        try:
            if self.__host == '127.0.0.1':
                from SirahCredoServer.server import ServerSirahCredoLaser
                ss = ServerSirahCredoLaser(self.__host, self.__port)
                threading.Thread(target=ss.main, args=()).start()
                logging.info('***LASER***: Connecting to local Host.')
                self.__DEBUG = True
            elif self.__host == '129.175.82.159':
                self.__DEBUG = False
                logging.info('***LASER***: Connecting to VG Lumiere.')
            elif self.__host == '192.168.199.9':
                self.__DEBUG = False
                logging.info('***LASER***: Connecting to Raspberry Pi.')

            logging.info(f'***LASER***: Trying to connect in Host {self.__host} using Port {self.__port}.')
            self.__serverLaser = LaserServerHandler(self.__laser_message, self.__host, self.__port, 'laser')
            self.__serverPM = [LaserServerHandler(self.__laser_message, self.__host, self.__port, 'pm01'),
                               power.TLPowerMeter('USB0::0x1313::0x8072::1908893::INSTR')]
            if not self.__serverPM[1].successful:
                logging.info('***LASER***: 2nd powermeter not found. Trying second powermeter.')
                self.__serverPM[1] = power.TLPowerMeter('USB0::0x1313::0x8072::1912791 ::INSTR')
                if not self.__serverPM[1].successful:
                    logging.info('***LASER***: 2nd powermeter not found (again). Entering in debug mode.')
                    from SirahCredoServer.virtualInstruments import power_vi
                    self.__serverPM[1] = power_vi.TLPowerMeter('USB0::0x1313::0x8072::1908893::INSTR')
            self.__serverPS = LaserServerHandler(self.__laser_message, self.__host, self.__port, 'ps')
            self.__serverArd = LaserServerHandler(self.__laser_message, self.__host, self.__port, 'ard')
            self.__serverHV = hv.HVDeflector()

            if self.__serverLaser.server_ping():
                logging.info('***LASER***: Connection with server successful.')
                if self.__camera and self.__OrsayScanInstrument:
                    if hasattr(self.__OrsayScanInstrument.scan_device, 'orsayscan'):
                        self.fast_blanker_status_f = False #fast blanker OFF
                        self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(0, -1, self.__width, True, 0, self.__delay)
                    self.sht_f = False  # shutter off
                    self.run_status_f = False
                    self.servo_f = 165
                    self.powermeter_avg_f = self.__powermeter_avg

                    ## LASER WAVELENGTH AND POWER SUPPLY CHECK ##
                    self.property_changed_event.fire("cur_wav_f")
                    self.property_changed_event.fire('q_f')
                    self.property_changed_event.fire('d_f')
                    self.property_changed_event.fire('cur_d1_f')
                    self.property_changed_event.fire('cur_d2_f')
                    self.property_changed_event.fire('sht_f')
                    self.property_changed_event.fire("cur_d_f")
                    self.property_changed_event.fire("cur_d_edit_f")
                    self.property_changed_event.fire('t_d1_f')
                    self.property_changed_event.fire('t_d2_f')
                    return True
                else:
                    return False
            else:
                logging.info(
                    '***LASER***: Server seens to exist but it is not accepting connections. Please put it to Hang or disconnect other users.')
                return False
        except ConnectionRefusedError:
            logging.info('***LASER***: No server was found. Check if server is hanging and it is in the good host.')
            return False

    def sht(self):
        if self.sht_f == 'CLOSED':
            self.sht_f = True
        else:
            self.sht_f = False

    def lock(self):
        self.property_changed_event.fire("locked_power_f")
        self.free_event.fire("all")

    def hard_reset(self):
        self.__serverPM[0].pw_reset('0')
        self.__serverPM[1].pw_reset()

    def upt(self):
        self.property_changed_event.fire("cur_wav_f")
        self.property_changed_event.fire("power_f")
        self.property_changed_event.fire("power02_f")
        self.property_changed_event.fire("power_transmission_f")
        self.property_changed_event.fire('t_d1_f')
        self.property_changed_event.fire('t_d2_f')
        self.property_changed_event.fire('cur_d1_f')
        self.property_changed_event.fire('cur_d2_f')

        if not self.__status:
            self.free_event.fire("all")

    def grab_det(self, mode, index, npic, show):
        logging.info("***LASER***: Scanning Full Image.")
        # this gets frame parameters
        det_frame_parameters = self.__OrsayScanInstrument.get_current_frame_parameters()
        # this multiplies pixels(x) * pixels(y) * pixel_time
        frame_time = self.__OrsayScanInstrument.calculate_frame_time(det_frame_parameters)
        self.__OrsayScanInstrument.start_playing()
        time.sleep(frame_time * 1.2)  # 20% more of the time for a single frame
        det_di = self.__OrsayScanInstrument.grab_next_to_start()

        self.__OrsayScanInstrument.abort_playing()
        self.det_acq.fire(det_di, mode, index, npic, show)

    def abt(self):
        logging.info('***LASER***: Abort Measurement.')
        if not self.__abort_force:
            self.__abort_force = True
            self.__serverLaser.abort_control()  # abort laser thread as well.
        try:
            self.__thread.join()
        except AttributeError:
            pass

        logging.info(f'***LASER***: Number of Threads current alive is {threading.active_count()}')
        self.run_status_f = False  # force free GUI

    def acq_mon(self):
        if self.__serverLaser.server_ping():
            self.__thread = threading.Thread(target=self.acq_monThread)
            self.__thread.start()

    """
    def acq_trans(self):
        self.__acq_number += 1
        if self.__serverLaser.server_ping():
            self.__thread = threading.Thread(target=self.acq_transThread)
            self.__thread.start()
    """

    def acq_pr(self):
        if self.__serverLaser.server_ping():
            self.__thread = threading.Thread(target=self.acq_prThread)
            self.__thread.start()

    def acq(self):
        if self.__serverLaser.server_ping():
            self.__thread = threading.Thread(target=self.acqThread)
            self.__thread.start()

    def acq_monThread(self):
        '''
        Monitor thread. This blocks GUI and is used to loop over second powermeter in order to align
        optical fiber or do whatever you want.

        Notes
        -----
        Power ramp is there just for a mere convenience. If you measuring power using the side thread, power will
        be automatically controlled depending on your control UI drop down value. If you, for some reason, forget to
        put control to None and start a monitor thread, you will align your fiber with the servo trying to control
        the power! Putting power ramp means that servo is involved in the measurement (by your control value) but
        proportional control must be turned off during measurement. This is exactly what is done using power ramp
        thread.

        '''
        self.run_status_f = self.__power_ramp = self.__bothPM = True
        self.__abort_force = False
        loop_index = 0
        self.call_monitor.fire()
        self.__controlRout.pw_control_thread_on(self.__powermeter_avg * 0.003)
        while not self.__abort_force:
            self.append_monitor_data.fire(self.__power02, loop_index)
            loop_index += 1
            if loop_index == 200: loop_index=0
        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()

        self.end_data_monitor.fire()
        self.__bothPM = self.__power_ramp = False
        self.run_status_f = False

    """
    def acq_transThread(self):
        self.run_status_f = True
        self.__abort_force = False
        self.__bothPM = True
        self.__servo_pos_initial = self.__servo_pos

        if (self.__serverLaser.set_scan_thread_check() and abs(
                self.__start_wav - self.__cur_wav) <= 0.001 and self.__finish_wav > self.__start_wav):

            self.__acq_number += 1
            self.call_data.fire(self.__acq_number, self.pts_f + 0, self.avg_f, self.__start_wav, self.__finish_wav,
                                self.__step_wav, self.__ctrl_type, self.__delay, self.__width, self.__diode, trans=1)
            self.__serverLaser.set_scan(self.__cur_wav, self.__step_wav, self.__pts)
            self.sht_f = True
            self.__controlRout.pw_control_thread_on(self.__powermeter_avg*0.003) #this is mandatory as it measures power
        else:
            logging.info(
                "***LASER***: Last thread was not done || start and current wavelength differs || end wav < start wav")
            self.__abort_force = True

        i = 0  # e-point counter
        i_max = self.__pts
        j = 0  # each frame inside an specific e-point
        j_max = self.__avg  # dont put directly self.__avg because it will keep refreshing UI

        while i < i_max and not self.__abort_force:  # i means our laser WL's
            while j < j_max and not self.__abort_force:  # j is our averages
                time.sleep(self.__powermeter_avg*0.003*1.1) #each measurement takes 0.03
                self.combo_data_f = True  # check laser now. True simply blocks GUI
                self.append_data.fire(self.combo_data_f, i, j, False)
                j += 1
            j = 0
            i += 1
            if (
                    self.__serverLaser.set_scan_thread_hardware_status() == 2 and self.__serverLaser.set_scan_thread_locked()):
                # check if laser changes have finished and thread step is over
                self.__serverLaser.set_scan_thread_release()  # if yes, you can advance
                logging.info("***ACQUISITION***: Moving to next wavelength...")
            else:
                self.abt()  # execute our abort routine (laser and acq thread)
        self.sht_f = False
        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()  # turns off our periodic thread.
        if self.__ctrl_type == 1: self.servo_f = self.__servo_pos_initial  # Even if this is not controlled it doesnt
        # matter
        if self.__ctrl_type == 2: pass  # here you can put the initial current of the power supply. Not implemented yet
        self.combo_data_f = True  # if its controlled then you update servo or power supply right
        while (
                not self.__serverLaser.set_scan_thread_check()):  # thread MUST END for the sake of security. Better to be
            # looped here indefinitely than fuck the hardware
            if self.__serverLaser.set_scan_thread_locked():  # releasing everything if locked
                self.__serverLaser.set_scan_thread_release()
        self.__bothPM = False
        #self.start_wav_f = self.__start_wav
        self.end_data.fire()
        self.run_status_f = False  # acquisition is over
    """

    def acq_prThread(self):
        self.run_status_f = self.__power_ramp = True
        self.__abort_force = False
        self.__servo_pos_initial = self.__servo_pos

        # Laser power resolved thread begins
        p = "acquistion_mode" in self.__camera.get_current_frame_parameters()
        q = self.__camera.get_current_frame_parameters()['acquisition_mode'] == 'Focus' if p else True
        if (self.__serverLaser.set_scan_thread_check() and abs(
                self.__start_wav - self.__cur_wav) <= 0.001 and self.__finish_wav > self.__start_wav and q):
            self.__acq_number += 1
            self.call_data.fire(self.__acq_number, int(self.__servo_pos / self.__servo_step) + 1, self.__avg, self.__start_wav, self.__start_wav, 0.0, 1,
                                self.__delay, self.__width, self.__diode, self.__power_transmission)
            self.__camera.start_playing()
            self.sht_f = True
            self.__controlRout.pw_control_thread_on(self.__powermeter_avg * 0.003 * 4.0)
        else:
            logging.info(
                "***LASER***: Last thread was not done || start and current wavelength differs || end wav < start wav || Not Focus mode.")
            self.run_status_f = False
            return

        i = 0
        i_max = int(self.__servo_pos / self.__servo_step)
        j = 0
        j_max = self.__avg

        while i < i_max and not self.__abort_force:
            while j < j_max and not self.__abort_force:
                last_cam_acq = self.__camera.grab_next_to_finish()[0]
                self.combo_data_f = True
                self.append_data.fire(self.__power02, i, j, last_cam_acq, j==j_max-1 and i%2==0)
                j += 1
            self.servo_f = self.servo_f - self.__servo_step
            j = 0
            # Grabbing pics at the middle is currently disabled.
            #if i in pics_array and self.__per_pic:
            #    self.grab_det("middle", self.__acq_number, i, True)
            i += 1
        self.sht_f = False
        logging.info("***ACQUISITION***: Finishing laser/servo measurement. Acquiring conventional EELS for reference.")
        while j < j_max and not self.__abort_force:
            last_cam_acq = self.__camera.grab_next_to_finish()[0]
            self.append_data.fire(self.__power02, i, j, last_cam_acq, j==j_max-1)
            j += 1
        self.combo_data_f = True
        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()  # turns off our periodic thread.
        self.servo_f = self.__servo_pos_initial  # putting back at the initial position
        self.__power_ramp = False
        #self.grab_det("end", self.__acq_number, 0, True)
        self.end_data.fire()
        self.run_status_f = False

    def acqThread(self):
        self.run_status_f = True
        self.__abort_force = False
        self.__servo_pos_initial = self.__servo_pos

        # Laser thread begins
        p = "acquistion_mode" in self.__camera.get_current_frame_parameters()
        q =  self.__camera.get_current_frame_parameters()['acquisition_mode'] == 'Focus' if p else True
        if (self.__serverLaser.set_scan_thread_check() and abs(
                self.__start_wav - self.__cur_wav) <= 0.001 and self.__finish_wav > self.__start_wav and q):

            self.__acq_number += 1
            self.call_data.fire(self.__acq_number, self.pts_f + 1, self.avg_f, self.__start_wav, self.__finish_wav,
                                self.__step_wav, self.__ctrl_type, self.__delay, self.__width, self.__diode, self.__power_transmission)
            #self.grab_det("init", self.__acq_number, 0, True)  # after call_data.fire
            pics_array = numpy.linspace(0, self.__pts, min(self.__nper_pic + 2, self.__pts + 1), dtype=int)
            pics_array = pics_array[1:]  # exclude zero
            self.__camera.start_playing()
            self.__serverLaser.set_scan(self.__cur_wav, self.__step_wav, self.__pts)
            self.sht_f = True
            self.__controlRout.pw_control_thread_on(self.__powermeter_avg*0.003*4.0)
        else:
            logging.info(
                "***LASER***: Last thread was not done || start and current wavelength differs || end wav < start wav || Not Focus mode.")
            self.run_status_f = False  # acquisition is over
            return
            #self.__abort_force = True

        i = 0  # e-point counter
        i_max = self.__pts
        j = 0  # each frame inside an specific e-point
        j_max = self.__avg  # dont put directly self.__avg because it will keep refreshing UI

        while i < i_max and not self.__abort_force:  # i means our laser WL's
            while j < j_max and not self.__abort_force:  # j is our averages
                last_cam_acq = self.__camera.grab_next_to_finish()[0]  # get camera then check laser.
                self.append_data.fire(self.__power02, i, j, last_cam_acq, j==j_max-1 and i%2==0)
                j += 1
            j = 0
            i += 1
            if (
                    self.__serverLaser.set_scan_thread_hardware_status() == 2 and self.__serverLaser.set_scan_thread_locked()):
                # check if laser changes have finished and thread step is over
                self.__serverLaser.set_scan_thread_release()  # if yes, you can advance
                logging.info("***LASER***: Moving to next wavelength...")
                time.sleep(0.3 * self.__step_wav / (0.5))
                self.combo_data_f = True  # check laser now
            else:
                self.abt()  # execute our abort routine (laser and acq thread)

        self.sht_f = False
        logging.info("***LASER***: Finishing laser measurement. Acquiring conventional EELS for reference.")
        while j < j_max and not self.__abort_force:
            last_cam_acq = self.__camera.grab_next_to_finish()[0]
            self.append_data.fire(self.__power02, i, j, last_cam_acq, j==j_max-1)
            j += 1
        self.combo_data_f = True

        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()  # turns off our periodic thread.
        if self.__ctrl_type == 1: self.servo_f = self.__servo_pos_initial  # Even if this is not controlled it doesnt
        # matter
        if self.__ctrl_type == 2: pass  # here you can put the initial current of the power supply. Not implemented yet
        self.combo_data_f = True  # if its controlled then you update servo or power supply right
        while (
                not self.__serverLaser.set_scan_thread_check()):  # thread MUST END for the sake of security. Better to be
            # looped here indefinitely than fuck the hardware
            if self.__serverLaser.set_scan_thread_locked():  # releasing everything if locked
                self.__serverLaser.set_scan_thread_release()
        #self.grab_det("end", self.__acq_number, 0, True)
        #self.start_wav_f = self.__start_wav
        self.end_data.fire()
        self.run_status_f = False  # acquisition is over

        # 0-20: laser; 21-40: power meter; 41-60: data analyses; 61-80: power supply; 81-100: servo; 101-120: control

    def sendMessageFactory(self):
        def sendMessage(message):
            if message == 101:
                self.property_changed_event.fire("power02_f")
                if self.__bothPM: self.property_changed_event.fire("power_f") #measure both powers
                if self.__bothPM: self.property_changed_event.fire("power_transmission_f")
                if self.__ctrl_type == 1 and not self.__power_ramp:
                    self.servo_f = self.servo_f + 1 if self.__power02 < self.__power_ref else self.servo_f - 1
                    if self.__servo_pos > 180: self.__servo_pos = 180
                    if self.__servo_pos < 0: self.__servo_pos = 0
                if self.__ctrl_type == 2 and not self.__power_ramp:
                    self.__diode = self.__diode + 0.02 if self.__power02 < self.__power_ref else self.__diode - 0.02
                    self.cur_d_f = self.__diode
            elif message == 666:
                self.__abort_force = True
                logging.info('***LASER***: Lost connection with server. Please check if server is active.')
                self.server_shutdown.fire()
            else:
                logging.info(f'***LASER***: Message {message} is not recognizable')
        return sendMessage

    def Laser_stop_all(self):
        self.sht_f = False
        self.fast_blanker_status_f = False

    def wavelength_ready(self):
        if not abs(self.__start_wav - self.__cur_wav) <= 0.005:
            self.property_changed_event.fire("cur_wav_f")  # don't need a thread.
            time.sleep(0.25)
            self.wavelength_ready()
        else:
            self.power_wav_f = self.__cur_wav
            self.run_status_f = False  # this already frees GUI

    def prepare_spim_TP3(self):
        self.sht_f = False
        self.laser_frequency_f = 12000
        self.__OrsayScanInstrument.scan_device.orsayscan.SetLaser(self.__frequency, 0, False, -1)
        self.__OrsayScanInstrument.scan_device.orsayscan.StartLaser(3, 5)
        logging.info('***LASER***: Please open shutter.')

    def over_spim_TP3(self):
        self.sht_f = False
        self.laser_frequency_f = 10000
        self.fast_blanker_status_f = True

    @property
    def start_wav_f(self) -> float:
        return self.__start_wav

    @start_wav_f.setter
    def start_wav_f(self, value: float) -> None:
        self.__start_wav = float(value)
        self.busy_event.fire("all")
        if not self.__status:
            self.property_changed_event.fire("pts_f")
            self.property_changed_event.fire("tpts_f")
            self.run_status_f = True
            response = self.__serverLaser.setWL(self.__start_wav, self.__cur_wav)
            if response == 1:
                logging.info("***LASER***: start WL is current WL")
                self.run_status_f = False
                self.combo_data_f = False #when false, GUI is fre-ed by status
            elif response == 2:
                logging.info("***LASER***: Current WL being updated...")
                self.run_status_f = True
                self.combo_data_f = False #when false, GUI is fre-ed by status
                threading.Timer(0.05, self.wavelength_ready, args=()).start()

    @property
    def finish_wav_f(self) -> float:
        return self.__finish_wav

    @finish_wav_f.setter
    def finish_wav_f(self, value: float) -> None:
        self.__finish_wav = float(value)
        self.property_changed_event.fire("pts_f")
        self.property_changed_event.fire("tpts_f")
        self.free_event.fire("all")

    @property
    def step_wav_f(self) -> float:
        return self.__step_wav

    @step_wav_f.setter
    def step_wav_f(self, value: float) -> None:
        self.__step_wav = float(value)
        self.property_changed_event.fire("pts_f")
        self.property_changed_event.fire("tpts_f")
        self.free_event.fire("all")

    @property
    def avg_f(self) -> int:
        return self.__avg

    @avg_f.setter
    def avg_f(self, value: int) -> None:
        self.__avg = int(value)
        self.property_changed_event.fire("tpts_f")
        self.free_event.fire("all")

    @property
    def tpts_f(self) -> int:
        self.__tpts = int(int(self.__avg) * int(self.__pts))
        return self.__tpts

    @property
    def pts_f(self) -> float:
        self.__pts = int((float(self.__finish_wav) - float(self.__start_wav)) / float(self.__step_wav) + 1)
        return self.__pts

    @property  # we dont set cur_wav but rather start wav.
    def cur_wav_f(self) -> str:
        if not self.__serverLaser:
            return 'None'
        else:
            self.__cur_wav = self.__serverLaser.get_hardware_wl()[0]
            return format(self.__cur_wav, '.4f')

    @property
    def run_status_f(self):
        return str(self.__status)

    @run_status_f.setter
    def run_status_f(self, value):
        self.__status = value
        self.property_changed_event.fire("run_status_f")
        if not value: self.free_event.fire('all')

    @property
    def power_f(self):
        try:
            if self.__DEBUG:
                self.__power = self.__cubeRT * (self.__serverPM[0].pw_read('0', self.__cur_wav) + (self.__diode) ** 2) * (
                        self.__servo_pos + 1) / 180
            else:
                self.__power = self.__cubeRT * self.__serverPM[0].pw_read('0', self.__cur_wav)
            return format(self.__power, '.3f')
        except AttributeError:
            return 'None'

    @property
    def power02_f(self):
        try:
            if self.__DEBUG:
                self.__power02 = self.__cubeRT * (self.__serverPM[1].pw_read(self.__cur_wav) + (self.__diode/2.) ** 2) * (
                        self.__servo_pos + 1) / 180
            else:
                self.__power02 = self.__cubeRT * self.__serverPM[1].pw_read(self.__cur_wav)
            if self.__autoLock and not self.__status: self.property_changed_event.fire("locked_power_f")
            return format(self.__power02, '.3f')
        except:
            return 'None'

    @property
    def power_transmission_f(self):
        try:
            self.__power_transmission = self.__power02 / self.__power
            return format(self.__power_transmission, '.3f')
        except:
            'None'

    @property
    def locked_power_f(self):
        self.__power_ref = self.__power02
        return format(self.__power_ref, '.3f')

    @property
    def auto_lock_f(self):
        return self.__autoLock

    @auto_lock_f.setter
    def auto_lock_f(self, value):
        self.__autoLock = value

    @property
    def cur_d_f(self) -> int:
        try:
            return int(self.__diode*100)
        except AttributeError:
            return 0

    @cur_d_f.setter
    def cur_d_f(self, value: int):
        self.__diode = value / 100.
        cvalue = format(float(self.__diode), '.2f')  # how to format and send to my hardware
        if self.__diode < 30:
            self.__serverPS.comm('C1:' + str(cvalue) + '\n')
            self.__serverPS.comm('C2:' + str(cvalue) + '\n')
        else:
            logging.info('***LASER***: Attempt to put a current outside allowed range. Check global_settings.')

        if not self.__status:
            self.property_changed_event.fire("cur_d1_f")
            self.property_changed_event.fire("cur_d2_f")
            self.property_changed_event.fire("cur_d_f")
            self.property_changed_event.fire("cur_d_edit_f")
            # Power measurement helps us to see where we are
            self.property_changed_event.fire("power_f")
            self.property_changed_event.fire("power02_f")
            self.property_changed_event.fire("power_transmission_f")
            self.free_event.fire("all")

    @property
    def cur_d1_f(self):
        try:
            return self.__serverPS.query('?C1\n').decode('UTF-8').replace('\n', '')
        except:
            return 'None'


    @property
    def cur_d2_f(self):
        try:
            return self.__serverPS.query('?C2\n').decode('UTF-8').replace('\n', '')
        except:
            return 'None'

    @property
    def t_d1_f(self):
        try:
            return self.__serverPS.query('?T1\n').decode('UTF-8').replace('\n', '')
        except:
            return 'None'

    @property
    def t_d2_f(self):
        try:
            return self.__serverPS.query('?T2\n').decode('UTF-8').replace('\n', '')
        except:
            return 'None'

    @property
    def sht_f(self):
        try:
            return self.__serverPS.query('?SHT\n').decode('UTF-8').replace('\n', '')
        except:
            return 'None'

    @sht_f.setter
    def sht_f(self, value: bool):
        if value:
            self.__serverPS.comm('SHT:1\n')
        else:
            self.__serverPS.comm('SHT:0\n')

        self.property_changed_event.fire('sht_f')
        if not self.__status: self.free_event.fire('all')

    @property
    def d_f(self):
        try:
            if self.__serverPS.query('?D\n').decode('UTF-8').replace('\n', '') == 'ON': return True
            else: return False
        except AttributeError:
            return False

    @d_f.setter
    def d_f(self, value: bool):
        if value:
            self.__serverPS.comm('D:1\n')
        else:
            self.__serverPS.comm('D:0\n')

        self.property_changed_event.fire('d_f')  # kill GUI and updates fast OFF response
        threading.Timer(3, self.property_changed_event.fire, args=('d_f',)).start()  # update in case of slow response
        threading.Timer(3.1, self.free_event.fire, args=('all',)).start()  # retake GUI

    @property
    def q_f(self):
        try:
            if self.__serverPS.query('?G\n').decode('UTF-8').replace('\n', '') == 'OPEN': return True
            else: return False
        except AttributeError:
            return False

    @q_f.setter
    def q_f(self, value: bool):
        if value:
            self.__serverPS.comm('G:1\n')
        else:
            self.__serverPS.comm('G:0\n')
        self.property_changed_event.fire('q_f')
        self.free_event.fire("all")

    @property
    def tdc_f(self):
        return self.__tdc_status

    @tdc_f.setter
    def tdc_f(self, value: bool):
        self.__tdc_status = value
        if value:
            self.__OrsayScanInstrument.scan_device.orsayscan.SetTdcLine(1, 2, 13) #Copy Line 05

    @property
    def ascii_f(self):
        return '-'

    @property
    def servo_wobbler_f(self):
        return self.__servo_wobbler

    @servo_wobbler_f.setter
    def servo_wobbler_f(self, value):
        self.__servo_wobbler = value
        if value:
            self.__serverArd.wobbler_on(self.__servo_pos, self.__servo_step)
        else:
            self.__serverArd.wobbler_off()
            time.sleep(1.1 / 2.)
            self.servo_f = self.__servo_pos
        self.property_changed_event.fire('servo_wobbler_f')
        self.free_event.fire('all')

    @property
    def servo_f(self):
        return self.__servo_pos

    @servo_f.setter
    def servo_f(self, value: int):
        if self.servo_wobbler_f: self.servo_wobbler_f = False
        self.__servo_pos = value
        if self.__servo_pos<0: self.__servo_pos=0
        if self.__servo_pos>180: self.__servo_pos=180
        self.__serverArd.set_pos(self.__servo_pos)
        if not self.__status:
            self.__servo_pts = int(self.__servo_pos / self.__servo_step)
            self.property_changed_event.fire("servo_pts_f")
            self.property_changed_event.fire("servo_f")  # this updates my label
            #Power measurement to help us
            self.property_changed_event.fire("power_f")
            self.property_changed_event.fire("power02_f")
            self.property_changed_event.fire("power_transmission_f")
            self.free_event.fire('all')

    @property
    def servo_step_f(self):
        return self.__servo_step

    @servo_step_f.setter
    def servo_step_f(self, value):
        if self.servo_wobbler_f: self.servo_wobbler_f = False
        try:
            self.__servo_step = int(value)
        except:
            self.__servo_step = 1
            logging.info('***LASER***: Please enter an integer for servo step.')
        if not self.__status:
            self.__servo_pts = int(self.__servo_pos / self.__servo_step)
            self.property_changed_event.fire("servo_pts_f")
            self.free_event.fire('all')

    @property
    def servo_pts_f(self):
        return self.__servo_pts

    @property
    def pw_ctrl_type_f(self):
        return self.__ctrl_type

    @pw_ctrl_type_f.setter
    def pw_ctrl_type_f(self, value):
        self.__ctrl_type = value

    @property
    def fast_blanker_status_f(self):
        return self.__fb_status

    @fast_blanker_status_f.setter
    def fast_blanker_status_f(self, value):
        self.__fb_status = value
        if value:
            self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(4, -1, beamontime=self.__width,
                                                                            delay=self.__delay)
            self.__OrsayScanInstrument.scan_device.orsayscan.SetLaser(self.__frequency, 0, False, -1)
            self.__OrsayScanInstrument.scan_device.orsayscan.StartLaser(7)
        else:
            self.__OrsayScanInstrument.scan_device.orsayscan.CancelLaser()
            self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(0, -1, self.__width, True, 0, self.__delay)
        self.property_changed_event.fire('fast_blanker_status_f')
        if not self.__status: self.free_event.fire('all')

    @property
    def laser_delay_f(self):
        return int(self.__delay * 1e9)

    @laser_delay_f.setter
    def laser_delay_f(self, value):
        self.__delay = float(value) / 1e9
        self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(4, -1, beamontime=self.__width,
                                                                                      delay=self.__delay)
        self.property_changed_event.fire('laser_delay_f')
        self.free_event.fire('all')

    @property
    def laser_width_f(self):
        return int(self.__width * 1e9)

    @laser_width_f.setter
    def laser_width_f(self, value):
        self.__width = float(value) / 1e9
        self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(4, -1, beamontime=self.__width,
                                                                                      delay=self.__delay)
        self.property_changed_event.fire('laser_width_f')
        self.free_event.fire('all')

    @property
    def laser_counts_f(self):
        return format(self.__counts, '.1E')

    @laser_counts_f.setter
    def laser_counts_f(self, value):
        self.__counts = value

    @property
    def laser_frequency_f(self):
        return self.__frequency

    @laser_frequency_f.setter
    def laser_frequency_f(self, value):
        self.__frequency = int(value)
        self.property_changed_event.fire('laser_frequency_f')
        self.free_event.fire('all')

    @property
    def combo_data_f(self):
        if self.__ctrl_type == 1 or self.__power_ramp:
            return [self.__cur_wav, self.__power, self.__servo_pos, self.__power02]
        if self.__ctrl_type == 2:
            return [self.__cur_wav, self.__power, self.__diode, self.__power02]
        else:
            return [self.__cur_wav, self.__power, self.__power02]

    @combo_data_f.setter
    def combo_data_f(self, value):
        self.property_changed_event.fire("cur_wav_f")
        if self.__ctrl_type == 1 or self.__power_ramp: self.property_changed_event.fire("servo_f")
        if self.__ctrl_type == 2: self.property_changed_event.fire("cur_d_f")
        if not value and not self.__status: self.free_event.fire('all')

    @property
    def powermeter_avg_f(self):
        return self.__powermeter_avg

    @powermeter_avg_f.setter
    def powermeter_avg_f(self, value):
        try:
            self.__powermeter_avg = int(float(value))
            self.__serverPM[0].pw_set_avg(self.__powermeter_avg, '0')
            self.__serverPM[1].pw_set_avg(self.__powermeter_avg)
        except:
            self.__powermeter_avg = 10
            logging.info("***LASER***: Please enter an integer. Using 10.")

    @property
    def per_pic_f(self):
        return self.__per_pic

    @per_pic_f.setter
    def per_pic_f(self, value):
        self.__per_pic = value

    @property
    def many_per_pic_f(self):
        return self.__nper_pic

    @many_per_pic_f.setter
    def many_per_pic_f(self, value):
        try:
            self.__nper_pic = int(value)
        except:
            self.__nper_pic = 0
            logging.info('***LASER***: Please enter an integer for detectors grab.')

    @property
    def dye_f(self):
        return self.__dye

    @dye_f.setter
    def dye_f(self, value):
        self.__dye = value

    @property
    def host_f(self):
        return self.__host

    @host_f.setter
    def host_f(self, value):
        self.__host = value

    @property
    def port_f(self):
        return self.__port

    @port_f.setter
    def port_f(self, value):
        try:
            self.__port = int(value)
        except TypeError:
            self.__port = 65432
            logging.info('***LASER***: Port must be an integer. Using 65432.')

    @property
    def hv_f(self):
        return self.__hv

    @hv_f.setter
    def hv_f(self, value):
        try:
            self.__hv = int(value)
        except ValueError:
            self.__hv = 0
            logging.info('***LASER***: Value must be an integer. Setting HV to 0.')
        hratio = abs(self.__hvRatio)/100.
        if self.__hvRatio == 0:
            self.__hvAbs = [self.__hv, self.__hv]
        elif self.__hvRatio > 0:
            self.__hvAbs = [self.__hv, (1-hratio)*self.__hv]
        else:
            self.__hvAbs = [(1-hratio)*self.__hv, self.__hv]
        self.__serverHV.set_voltage(self.__hvAbs[0], 'p')
        self.__serverHV.set_voltage(self.__hvAbs[1], 'n')
        self.property_changed_event.fire('hv_f')
        self.free_event.fire('all')

    @property
    def hv_ratio_f(self):
        return self.__hvRatio

    @hv_ratio_f.setter
    def hv_ratio_f(self, value):
        self.__hvRatio = value
        if self.__hvRatio == 0:
            logging.info('***LASER***: Ratio is centered. HV is symmetrical.')
        elif self.__hvRatio > 0:
            logging.info(f'***LASER***: HV is reduced {value}% in HV-.')
        else:
            logging.info(f'***LASER***: HV is reduced {abs(value)}% in HV+.')
        self.property_changed_event.fire('hv_ratio_f')
        self.free_event.fire('all')

    @property
    def piezo_step_f(self):
        return self.__piezoStep

    @piezo_step_f.setter
    def piezo_step_f(self, value):
        try:
            self.__piezoStep = int(value)
        except TypeError:
            self.__piezoStep = 100
            logging.info('***LASER***: Piezo step must be an integer. Using default as 100.')

    @property
    def piezo_m1_f(self):
        #self.__mpos[0] = self.__piezoMotor.GetCurrentPosition(1)
        return self.__mpos[0]

    @piezo_m1_f.setter
    def piezo_m1_f(self, value):
        self.__mpos[0] = value
        #self.__piezoMotor.MoveAbsolute(1, self.__mpos[0])
        self.property_changed_event.fire('piezo_m1_f')
        self.free_event.fire('all')

    @property
    def piezo_m2_f(self):
        #self.__mpos[1] = self.__piezoMotor.GetCurrentPosition(2)
        return self.__mpos[1]

    @piezo_m2_f.setter
    def piezo_m2_f(self, value):
        self.__mpos[1] = value
        #self.__piezoMotor.MoveAbsolute(2, self.__mpos[1])
        self.property_changed_event.fire('piezo_m2_f')
        self.free_event.fire('all')
