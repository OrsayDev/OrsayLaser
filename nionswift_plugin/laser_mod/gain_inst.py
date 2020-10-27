# standard libraries
from nion.utils import Event
from nion.utils import Observable
from nion.swift.model import HardwareSource

import logging
import threading
import os
import json
import time
import numpy
import socket

abs_path = os.path.abspath(os.path.join((__file__ + "/../"), "global_settings.json"))
with open(abs_path) as savfile:
    settings = json.load(savfile)

DEBUG_pw = settings["PW"]["DEBUG"]
DEBUG_ps = settings["PS"]["DEBUG"]
DEBUG_servo = settings["SERVO"]["DEBUG"]
CAMERA = settings["CAMERA"]["WHICH"]
SCAN = settings["SCAN"]["WHICH"]
MAX_CURRENT = settings["PS"]["MAX_CURRENT"]
CLIENT_HOST = settings["SOCKET_CLIENT"]["HOST"]
CLIENT_PORT = settings["SOCKET_CLIENT"]["PORT"]

DEBUG = DEBUG_pw and DEBUG_ps and DEBUG_servo

if DEBUG_pw:
    pass
else:
    pass

if DEBUG_ps:
    pass
else:
    from SirahCredoServer import power as power, power_vi as power

if DEBUG_servo:
    from . import servo_vi as servo
else:
    from . import servo as servo

from . import control_routine as ctrlRout


def SENDMYMESSAGEFUNC(sendmessagefunc):
    return sendmessagefunc

class LaserServerHandler():

    def __init__(self, callback, CLIENT_HOST = CLIENT_HOST, CLIENT_PORT = CLIENT_PORT):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((CLIENT_HOST, CLIENT_PORT))
        self.s.settimeout(0.5)
        self.callback = callback

    def server_ping(self):
        try:
            header = b'server_ping'
            msg = header
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() == 'Server Alive':
                logging.info('***SERVER***: Server ON.')
                return True
            else:
                return False
        except ConnectionResetError:
            self.connection_error_handler()
            return False
        except:
            return False

    def shutdown(self):
        self.s.close()

    def connection_error_handler(self):
        #server shutdown will be handled in the message below
        self.callback(666)

    ## Sirah Credo Laser Function

    def set_hardware_wl(self, wl):
        try:
            header = b'set_hardware_wl'
            msg = header + bytes(4)
            msg = msg + format(wl, '.8f').rjust(16, '0').encode()
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***SERVER***: Bad communication. Error 01.')
        except ConnectionResetError:
            self.connection_error_handler()

    def get_hardware_wl(self):
        try:
            header = b'get_hardware_wl'
            msg = header + bytes(4)
            self.s.sendall(msg)
            data = self.s.recv(512)
            return (float(data.decode()), 0)
        except ConnectionResetError:
            self.connection_error_handler()
            #this is pump laser wavelength and show us there is an error
            return (532,000, 0)

    def setWL(self, wl, cur_wl):
        try:
            header = b'setWL'
            msg = header + bytes(4)
            msg = msg + format(wl, '.8f').rjust(16, '0').encode()
            msg = msg + bytes(4)
            msg = msg + format(cur_wl, '.8f').rjust(16, '0').encode()
            msg = msg + bytes(4)
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data == b'message_01':
                return 1
            elif data == b'message_02':
                return 2
            else:
                logging.info('***SERVER***: Bad communication. Error 03.')
                return None
        except ConnectionResetError:
            self.connection_error_handler()
            return None

    def abort_control(self):
        try:
            header = b'abort_control'
            msg = header + bytes(4)
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***SERVER***: Bad communication. Error 04.')
        except ConnectionResetError:
            self.connection_error_handler()

    def set_scan_thread_locked(self):
        try:
            header = b'set_scan_thread_locked'
            msg = header + bytes(4)
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data == b'1':
                return True
            elif data == b'0':
                return False
            else:
                logging.info('***SERVER***: Bad communication. Error 05.')
                return False
        except ConnectionResetError:
            self.connection_error_handler()
            return False

    def set_scan_thread_release(self):
        try:
            header = b'set_scan_thread_release'
            msg = header + bytes(4)
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***SERVER***: Bad communication. Error 06.')
        except ConnectionResetError:
            self.connection_error_handler()

    def set_scan_thread_check(self):
        try:
            header = b'set_scan_thread_check'
            msg = header + bytes(4)
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data == b'1':
                return True
            elif data == b'0':
                return False
            else:
                logging.info('***SERVER***: Bad communication. Error 07.')
        except ConnectionResetError:
            self.connection_error_handler()

    def set_scan_thread_hardware_status(self):
        try:
            header = b'set_scan_thread_hardware_status'
            msg = header + bytes(4)
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data == b'2':
                return 2
            elif data == b'3':
                logging.info(
                    "***LASER***: Laser Motor is moving. You can not change wavelength while last one is still "
                    "moving. Please increase camera dwell time or # of averages in order to give time to our slow "
                    "hardware.")
                return 3
            else:
                logging.info('***SERVER***: Bad communication. Error 08.')
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
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***SERVER***: Bad communication. Error 09.')
        except ConnectionResetError:
            self.connection_error_handler()
            self.connection_error_handler()

    ## POWER SUPPLY RELATED FUNCTIONS ##

    def query(self, my_message):
        try:
            header = b'query'
            msg = header + bytes(3) #power supply sends 00-00-00
            msg = msg + my_message.encode()
            self.s.sendall(msg)
            data = self.s.recv(512)
            return data
        except ConnectionResetError:
            self.connection_error_handler()

    def comm(self, my_message):
        try:
            header = b'comm'
            msg = header + bytes(3) #power supply sends 00-00-00
            msg = msg + my_message.encode()
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***SERVER***: Bad communication. Error 12.') #must return None
        except ConnectionResetError:
            self.connection_error_handler()

    ## POWER METER RELATED FUNCTIONS ##

    def pw_set_wl(self, wl, which):
        try:
            header = b'pw_set_wl'+which.encode()
            msg = header + bytes(5) #power supply sends 00-00-00-00-00
            msg = msg + format(wl, '.8f').rjust(16, '0').encode() #16 bytes for float
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***SERVER***: Bad communication. Error 13.') #must return None
        except ConnectionResetError:
            self.connection_error_handler()

    def pw_read(self, which):
        try:
            header = b'pw_read'+which.encode()
            msg = header + bytes(5) #power meter sends 00-00-00-00-00
            self.s.sendall(msg)
            data = self.s.recv(512)
            return float(data.decode())
        except ConnectionResetError:
            self.connection_error_handler()

    def pw_reset(self, which):
        try:
            header = b'pw_reset'+which.encode()
            msg = header + bytes(5) #power supply sends 00-00-00-00-00
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***SERVER***: Bad communication. Error 14.') #must return None
        except ConnectionResetError:
            self.connection_error_handler()

    def pw_set_avg(self, avg, which):
        try:
            header = b'pw_set_avg'+which.encode()
            msg = header + bytes(5) #power supply sends 00-00-00-00-00
            msg = msg + format(avg, '.0f').rjust(8, '0').encode() # 8 bytes for int
            self.s.sendall(msg)
            data = self.s.recv(512)
            if data.decode() != 'None':
                logging.info('***SERVER***: Bad communication. Error 15.') #must return None
        except ConnectionResetError:
            self.connection_error_handler()


class gainDevice(Observable.Observable):

    def __init__(self):
        self.property_changed_event = Event.Event()
        self.free_event = Event.Event()
        self.communicating_event = Event.Event()
        self.busy_event = Event.Event()

        self.call_data = Event.Event()
        self.append_data = Event.Event()
        self.end_data = Event.Event()

        #below is related to handling an unexpected server shutdown
        self.server_shutdown = Event.Event()

        # this is related to the images taken periodically
        self.det_acq = Event.Event()

        self.__start_wav = 575.0
        self.__finish_wav = 595.0
        self.__step_wav = 0.5
        self.__cur_wav = self.__start_wav
        self.__pts = int((self.__finish_wav - self.__start_wav) / self.__step_wav + 1)
        self.__avg = 10
        self.__tpts = int(self.__avg * self.__pts)
        self.__power = 0.
        self.__power02 = 0.
        self.__rt = 10.
        self.__power_transmission = 0.
        self.__power_ref = 0.
        self.__diode = 0.10
        self.__servo_pos = 0
        self.__servo_pos_initial = self.__servo_pos
        self.__servo_pts = 0
        self.__servo_wobbler = False
        self.__ctrl_type = 0
        self.__delay = 1810 * 1e-9
        self.__width = 50 * 1e-9
        self.__fb_status = False
        self.__counts = 0
        self.__frequency = 10000
        self.__acq_number = 0  # this is a strange variable. This measures how many gain acquire you did in order to
        # create new displays every new acquisition
        self.__powermeter_avg = 10
        self.__servo_step = 2
        self.__nper_pic = 2
        self.__dye = 0
        self.__host = CLIENT_HOST
        self.__port = CLIENT_PORT

        self.__camera = None
        self.__data = None

        self.__thread = None
        self.__status = True #we start it true because before init everything must be blocked. We free after a succesfull init
        self.__abort_force = False
        self.__power_ramp = False
        self.__per_pic = True
        self.__per_pic = True

        self.__laser = None

        #self.__power_sendmessage = power.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        #self.__pwmeter = power.TLPowerMeter(self.__power_sendmessage, 'USB0::4883::32882::1907040::0::INSTR')

        #self.__power02_sendmessage = power.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        #self.__pwmeter02 = power.TLPowerMeter(self.__power_sendmessage, 'USB0::0x1313::0x8072::1908893::INSTR')

        #self.__ps_sendmessage = ps.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        #self.__ps = ps.SpectraPhysics(self.__ps_sendmessage)

        self.__servo_sendmessage = servo.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__servo = servo.servoMotor(self.__servo_sendmessage)

        self.__control_sendmessage = ctrlRout.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__controlRout = ctrlRout.controlRoutine(self.__control_sendmessage)

        self.__OrsayScanInstrument = None
        self.__camera = None

    def server_instrument_ping(self):
        self.__laser.server_ping()

    def server_instrument_shutdown(self):
        if self.__laser:
            self.__laser.shutdown()

    def init(self):

        for hards in HardwareSource.HardwareSourceManager().hardware_sources:  # finding eels camera. If you don't
            # find, use usim eels
            if hasattr(hards, 'hardware_source_id'):
                if hards.hardware_source_id == CAMERA:
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
            logging.info('***LASER***: Camera properly loaded. EELS/EEGS acquistion is good to go.')
            logging.info(self.__camera.hardware_source_id)

        self.__OrsayScanInstrument = HardwareSource.HardwareSourceManager().get_hardware_source_for_hardware_source_id(
            SCAN)
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
            logging.info('***LASER***: SCAN module properly loaded. Fast blanker is good to go.')

        self.__laser_message = SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__laser_message02 = SENDMYMESSAGEFUNC(self.sendMessageFactory())
        try:
            logging.info(f'***SERVER***: Trying to connect in Host {self.__host} using Port {self.__port}.')
            self.__laser = LaserServerHandler(self.__laser_message, self.__host, self.__port)
            self.__laser02 = LaserServerHandler(self.__laser_message, self.__host, self.__port)
            if self.__laser.server_ping():
                # Ask where is Laser
                logging.info('***SERVER***: Connection with server successful.')
                #if self.__OrsayScanInstrument and self.__camera:
                if self.__camera:
                    # Handling the beginning. I have put it here instead of simply returning True and
                    # self.__OrsayScanInstrument and self.__camera because these properties affect GUI. I would like
                    # to release GUI only in complete True case
                    if hasattr(self.__OrsayScanInstrument.scan_device, 'orsayscan'):
                        self.fast_blanker_status_f = False #fast blanker OFF
                        self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(0, -1, self.__width, True, 0, self.__delay)
                    self.sht_f = False  # shutter off
                    self.run_status_f = False
                    self.servo_f = 180 #maximum transmission
                    self.powermeter_avg_f = self.__powermeter_avg
                    self.property_changed_event.fire("cur_wav_f") #what is laser wavelength

                    ##POWER SUPPLY CHECK###
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
                    '***SERVER***: Server seens to exist but it is not accepting connections. Please put it to Hang or disconnect other users.')
                return False
        except ConnectionRefusedError:
            logging.info('***SERVER***: No server was found. Check if server is hanging and it is in the good host.')
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
        self.__laser02.pw_reset('0')
        self.__laser02.pw_reset('1')
        #self.__pwmeter.pw_reset()
        #self.__pwmeter02.pw_reset()

    def diode(self, val):
        self.d_f = val

    def q(self, val):
        self.q_f = val

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
        logging.info("***ACQUISITION***: Scanning Full Image.")
        # this gets frame parameters
        det_frame_parameters = self.__OrsayScanInstrument.get_current_frame_parameters()
        # this multiplies pixels(x) * pixels(y) * pixel_time
        frame_time = self.__OrsayScanInstrument.calculate_frame_time(det_frame_parameters)
        # note that i dont know if i defined pixel_time super correctely in orsay_scan_device. I know the number is
        # relatively nice, but i need to check the definition
        det_di = self.__OrsayScanInstrument.grab_next_to_start()
        self.__OrsayScanInstrument.stop_playing()
        time.sleep(frame_time * 1.2)  # 20% more of the time for a single frame
        self.det_acq.fire(det_di, mode, index, npic, show)

    def abt(self):
        logging.info('***LASER***: Abort Measurement.')
        self.__abort_force = True
        self.__laser.abort_control()  # abort laser thread as well.
        self.run_status_f = False  # force free GUI

    def acq_trans(self):
        self.__acq_number += 1
        # check if laser server is alive
        if self.__laser.server_ping():
            self.__thread = threading.Thread(target=self.acq_transThread)
            self.__thread.start()

    def acq_pr(self):
        self.__acq_number += 1
        #check if laser server is alive
        if self.__laser.server_ping():
            self.__thread = threading.Thread(target=self.acq_prThread)
            self.__thread.start()

    def acq(self):
        # check if laser server is alive
        if self.__laser.server_ping():
            self.__thread = threading.Thread(target=self.acqThread)
            self.__thread.start()

    #This is for transmission measurements with the laser. Scan wavelength and get power in both powermeters
    def acq_transThread(self):
        self.run_status_f = True
        self.__abort_force = False
        self.__servo_pos_initial = self.__servo_pos

        # Laser thread begins
        if (self.__laser.set_scan_thread_check() and abs(
                self.__start_wav - self.__cur_wav) <= 0.001 and self.__finish_wav > self.__start_wav):

            self.__acq_number += 1
            self.call_data.fire(self.__acq_number, self.pts_f + 0, self.avg_f, self.__start_wav, self.__finish_wav,
                                self.__step_wav, self.__ctrl_type, self.__delay, self.__width, self.__diode, trans=1)
            self.__laser.set_scan(self.__cur_wav, self.__step_wav, self.__pts)
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
                    self.__laser.set_scan_thread_hardware_status() == 2 and self.__laser.set_scan_thread_locked()):
                # check if laser changes have finished and thread step is over
                self.__laser.set_scan_thread_release()  # if yes, you can advance
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
                not self.__laser.set_scan_thread_check()):  # thread MUST END for the sake of security. Better to be
            # looped here indefinitely than fuck the hardware
            if self.__laser.set_scan_thread_locked():  # releasing everything if locked
                self.__laser.set_scan_thread_release()
        self.run_status_f = False  # acquisition is over
        #self.start_wav_f = self.__start_wav
        self.end_data.fire()


    def acq_prThread(self):
        self.run_status_f = self.__power_ramp = self.sht_f = True
        self.__abort_force = False
        self.__servo_pos_initial = self.__servo_pos
        i_max = int(self.__servo_pos / self.__servo_step)
        j_max = self.__avg
        pics_array = numpy.linspace(0, i_max, min(self.__nper_pic + 2, i_max + 1), dtype=int)
        pics_array = pics_array[1:]  # exclude zero
        self.call_data.fire(self.__acq_number, i_max + 1, j_max, self.__start_wav, self.__start_wav, 0.0, 1,
                            self.__delay, self.__width, self.__diode)
        self.grab_det("init", self.__acq_number, 0, True)  # after call_data.fire
        self.__controlRout.pw_control_thread_on(self.__powermeter_avg*0.003*1.1)
        i = 0
        j = 0
        while i < i_max and not self.__abort_force:
            while j < j_max and not self.__abort_force:
                last_cam_acq = self.__camera.grab_next_to_finish()[0]
                self.combo_data_f = True
                self.append_data.fire(self.combo_data_f, i, j, last_cam_acq)
                j += 1
            self.servo_f = self.servo_f - self.__servo_step
            j = 0
            if i in pics_array and self.__per_pic:
                self.grab_det("middle", self.__acq_number, i, True)
            i += 1
        self.sht_f = False
        logging.info("***ACQUISITION***: Finishing laser/servo measurement. Acquiring conventional EELS for reference.")
        while j < j_max and not self.__abort_force:
            last_cam_acq = self.__camera.grab_next_to_finish()[0]
            self.combo_data_f = True
            self.append_data.fire(self.combo_data_f, i, j, last_cam_acq)
            j += 1
        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()  # turns off our periodic thread.
        self.servo_f = self.__servo_pos_initial  # putting back at the initial position
        self.combo_data_f = True
        self.__power_ramp = False
        self.grab_det("end", self.__acq_number, 0, True)
        self.end_data.fire()
        self.run_status_f = False

    def acqThread(self):
        self.run_status_f = True
        self.__abort_force = False
        self.__servo_pos_initial = self.__servo_pos

        # Laser thread begins
        if (self.__laser.set_scan_thread_check() and abs(
                self.__start_wav - self.__cur_wav) <= 0.001 and self.__finish_wav > self.__start_wav):

            self.__acq_number += 1
            self.call_data.fire(self.__acq_number, self.pts_f + 1, self.avg_f, self.__start_wav, self.__finish_wav,
                                self.__step_wav, self.__ctrl_type, self.__delay, self.__width, self.__diode)
            self.grab_det("init", self.__acq_number, 0, True)  # after call_data.fire
            pics_array = numpy.linspace(0, self.__pts, min(self.__nper_pic + 2, self.__pts + 1), dtype=int)
            pics_array = pics_array[1:]  # exclude zero
            self.__laser.set_scan(self.__cur_wav, self.__step_wav, self.__pts)
            self.sht_f = True
            self.__controlRout.pw_control_thread_on(self.__powermeter_avg*0.003*1.1) #this is mandatory as it measures power
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
                last_cam_acq = self.__camera.grab_next_to_finish()[0]  # get camera then check laser.
                self.combo_data_f = True  # check laser now
                self.append_data.fire(self.combo_data_f, i, j, last_cam_acq)
                j += 1
            j = 0
            if i in pics_array and self.__per_pic:
                self.grab_det("middle", self.__acq_number, i, True)
            i += 1
            if (
                    self.__laser.set_scan_thread_hardware_status() == 2 and self.__laser.set_scan_thread_locked()):
                # check if laser changes have finished and thread step is over
                self.__laser.set_scan_thread_release()  # if yes, you can advance
                logging.info("***ACQUISITION***: Moving to next wavelength...")
            else:
                self.abt()  # execute our abort routine (laser and acq thread)

        self.sht_f = False
        logging.info("***ACQUISITION***: Finishing laser measurement. Acquiring conventional EELS for reference.")
        while j < j_max and not self.__abort_force:
            last_cam_acq = self.__camera.grab_next_to_finish()[0]
            self.combo_data_f = True
            self.append_data.fire(self.combo_data_f, i, j, last_cam_acq)
            j += 1

        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()  # turns off our periodic thread.
        if self.__ctrl_type == 1: self.servo_f = self.__servo_pos_initial  # Even if this is not controlled it doesnt
        # matter
        if self.__ctrl_type == 2: pass  # here you can put the initial current of the power supply. Not implemented yet
        self.combo_data_f = True  # if its controlled then you update servo or power supply right
        while (
                not self.__laser.set_scan_thread_check()):  # thread MUST END for the sake of security. Better to be
            # looped here indefinitely than fuck the hardware
            if self.__laser.set_scan_thread_locked():  # releasing everything if locked
                self.__laser.set_scan_thread_release()
        self.run_status_f = False  # acquisition is over
        self.grab_det("end", self.__acq_number, 0, True)
        #self.start_wav_f = self.__start_wav
        self.end_data.fire()

        # 0-20: laser; 21-40: power meter; 41-60: data analyses; 61-80: power supply; 81-100: servo; 101-120: control

    def sendMessageFactory(self):
        def sendMessage(message):
            if message == 21:
                logging.info('***Power Meter***: Cant write')
            if message == 22:
                logging.info('***Power Meter***: Cant READ a new measurement. Fetching last one instead.')
            if message == 24:
                logging.info('***Power Meter***: Power Meter not ID; Please check hardware.')
            if message == 25:
                logging.info('***Power Meter***: Hardware reset successful.')
            if message == 26:
                logging.info('***Power Meter***: Hardware reset failed.')
            if message == 27:
                logging.info('***Power Meter***: New averaging OK.')
            if message == 28:
                logging.info('***Power Meter***: Could not set new averaging.')
            if message == 61:
                logging.info('***LASER PS***: Could not open serial port. Check if connected and port')
            if message == 62:
                logging.info('***LASER PS***: Could not query properly')
            if message == 63:
                logging.info('***LASER PS***: Could not send command properly')
            if message == 81:
                logging.info('***SERVO***: Could not open serial port. Check if connected')
            if message == 82:
                logging.info('***SERVO***: Could not properly get_pos. Retrying after a flush..')
            if message == 83:
                logging.info('***SERVO***: Could not properly set_pos. Retrying after a flush..')
            if message == 84:
                logging.info('***SERVO***: Angle higher than 180. Holding on 180.')
            if message == 85:
                logging.info('***SERVO***: Angle smaller than 0. Holding on 0.')
            if message == 101:
                self.property_changed_event.fire("power_f")
                #self.property_changed_event.fire("power02_f") #measure both powers
                #self.property_changed_event.fire("power_transmission_f")
                if self.__ctrl_type == 1 and not self.__power_ramp:
                    self.servo_f = self.servo_f + 1 if self.__power < self.__power_ref else self.servo_f - 1
                    if self.__servo_pos > 180: self.__servo_pos = 180
                    if self.__servo_pos < 0: self.__servo_pos = 0
                if self.__ctrl_type == 2:
                    self.__diode = self.__diode + 0.02 if self.__power < self.__power_ref else self.__diode - 0.02
                    self.cur_d_f = self.__diode
            if message == 102:
                logging.info('***CONTROL***: Control OFF but it was never on.')
            if message == 666:
                self.__abort_force = True
                logging.info('***SERVER***: Lost connection with server. Please check if server is active.')
                self.server_shutdown.fire()
        return sendMessage

    def Laser_stop_all(self):
        self.sht_f = False
        self.fast_blanker_status_f = False
        self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(0, -1, self.__width, True, 0, self.__delay)

    def wavelength_ready(self):
        if not abs(self.__start_wav - self.__cur_wav) <= 0.001:
            self.property_changed_event.fire("cur_wav_f")  # don't need a thread.
            time.sleep(0.05)
            self.wavelength_ready()
        else:
            self.run_status_f = False  # this already frees GUI

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
            response = self.__laser.setWL(self.__start_wav, self.__cur_wav)
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
        if not self.__laser:
            return 'None'
        else:
            self.__cur_wav = self.__laser.get_hardware_wl()[0]
            #self.__laser02.pw_set_wl(self.__cur_wav, '0')
            #self.__laser02.pw_set_wl(self.__cur_wav, '1')
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
            if DEBUG_pw:
                self.__power = (self.__laser02.pw_read('0') + (self.__diode) ** 2) * (
                        self.__servo_pos + 1) / 180 if self.sht_f == 'OPEN' else self.__laser02.pw_read('0')
            else:
                self.__power = self.__laser02.pw_read('0')
            return format(self.__power, '.3f')
        except AttributeError:
            return 'None'

    @property
    def power02_f(self):
        try:
            if DEBUG_pw:
                self.__power02 = (self.__laser02.pw_read('1') + (self.__diode/2.) ** 2) * (
                        self.__servo_pos + 1) / 180 if self.sht_f == 'OPEN' else self.__laser02.pw_read('1')
            #self.__power02 = (self.__pwmeter02.pw_read() + (self.__diode/2.) ** 2) * (
            #        self.__servo_pos + 1) / 180 if self.sht_f == 'OPEN' else self.__pwmeter02.pw_read()
            else:
                self.__power02 = self.__laser02.pw_read('1')
                #self.__power02 = self.__pwmeter02.pw_read()
            return format(self.__power02, '.3f')
        except:
            return 'None'

    @property
    def rt_f(self): #this func is the R/T factor for the first powermeter. This will normalize power correctly
        return self.__rt

    @rt_f.setter
    def rt_f(self, value):
        try:
            self.__rt = float(value)
        except:
            self.__rt = 100.
            logging.info('***POWERMETER***: [R]/T factor must be a float. If R/T is 10/90, put 10. Now using 100')

    @property
    def power_transmission_f(self):
        try:
            self.__power_transmission = self.__power02 / self.__power
            return format(self.__power_transmission, '.5f')
        except:
            'None'


    @property
    def locked_power_f(self):
        self.__power_ref = self.__power
        return format(self.__power_ref, '.2f')

    @property
    def cur_d_f(self) -> int:
        return int(self.__diode * 100)

    @cur_d_f.setter
    def cur_d_f(self, value: int):
        self.__diode = value / 100
        cvalue = format(float(self.__diode), '.2f')  # how to format and send to my hardware
        if self.__diode < MAX_CURRENT:
            self.__laser.comm('C1:' + str(cvalue) + '\n')
            self.__laser.comm('C2:' + str(cvalue) + '\n')
        else:
            logging.info('***LASER PS***: Attempt to put a current outside allowed range. Check global_settings.')

        if not self.__status:
            self.property_changed_event.fire("power_f")
            self.property_changed_event.fire("cur_d1_f")
            self.property_changed_event.fire("cur_d2_f")
            self.property_changed_event.fire("cur_d_f")
            self.property_changed_event.fire("cur_d_edit_f")
            self.free_event.fire("all")

    @property
    def cur_d_edit_f(self):
        return self.__diode

    @cur_d_edit_f.setter
    def cur_d_edit_f(self, value):
        self.__diode = float(value)

        if not self.__status:
            self.property_changed_event.fire("power_f")
            self.property_changed_event.fire("cur_d1_f")
            self.property_changed_event.fire("cur_d2_f")
            self.property_changed_event.fire(
                "cur_d_f")  # He will call slider setter so no need to actually update value
            self.property_changed_event.fire("cur_d_edit_f")
            self.free_event.fire("all")

    @property
    def cur_d1_f(self):
        try:
            return self.__laser.query('?C1\n').decode('UTF-8').replace('\n', '')
        except:
            return 'None'

    @property
    def cur_d2_f(self):
        try:
            return self.__laser.query('?C2\n').decode('UTF-8').replace('\n', '')
        except:
            return 'None'

    @property
    def t_d1_f(self):
        try:
            return self.__laser.query('?T1\n').decode('UTF-8').replace('\n', '')
        except:
            return 'None'

    @property
    def t_d2_f(self):
        try:
            return self.__laser.query('?T2\n').decode('UTF-8').replace('\n', '')
        except:
            return 'None'

    @property
    def sht_f(self):
        try:
            return self.__laser.query('?SHT\n').decode('UTF-8').replace('\n', '')
        except:
            return 'None'

    @sht_f.setter
    def sht_f(self, value: bool):
        if value:
            self.__laser.comm('SHT:1\n')
        else:
            self.__laser.comm('SHT:0\n')

        self.property_changed_event.fire('sht_f')
        if not self.__status: self.free_event.fire('all')

    @property
    def d_f(self):
        try:
            return self.__laser.query('?D\n').decode('UTF-8').replace('\n', '')
        except:
            return 'None'

    @d_f.setter
    def d_f(self, value: bool):
        if value:
            self.__laser.comm('D:1\n')
        else:
            self.__laser.comm('D:0\n')

        self.property_changed_event.fire('d_f')  # kill GUI and updates fast OFF response
        threading.Timer(3, self.property_changed_event.fire, args=('d_f',)).start()  # update in case of slow response
        threading.Timer(3.1, self.free_event.fire, args=('all',)).start()  # retake GUI

    @property
    def q_f(self):
        try:
            return self.__laser.query('?G\n').decode('UTF-8').replace('\n', '')
        except:
            return 'None'

    @q_f.setter
    def q_f(self, value: bool):
        if value:
            self.__laser.comm('G:1\n')
        else:
            self.__laser.comm('G:0\n')
        self.property_changed_event.fire('q_f')
        self.free_event.fire("all")

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
            self.__servo.wobbler_on(self.__servo_pos, self.__servo_step)
        else:
            self.__servo.wobbler_off()
            time.sleep(1.1 / 2.)
            self.servo_f = self.__servo_pos
        self.property_changed_event.fire('servo_wobbler_f')
        self.free_event.fire('all')

    @property
    def servo_f(self):
        if not self.__status:
            return int(self.__servo.get_pos().decode('UTF-8'))
        else:
            return self.__servo_pos

    @servo_f.setter
    def servo_f(self, value: int):
        if self.servo_wobbler_f: self.servo_wobbler_f = False
        self.__servo_pos = value
        self.__servo.set_pos(self.__servo_pos)
        if not self.__status:
            self.__servo_pts = int(self.__servo_pos / self.__servo_step)
            self.property_changed_event.fire("servo_pts_f")
            self.property_changed_event.fire("power_f")
            self.property_changed_event.fire("servo_f")  # this updates my label
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
            logging.info('***SERVO***: Please enter an integer.')
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
            self.__OrsayScanInstrument.scan_device.orsayscan.SetLaser(self.__frequency, 5000000, False, -1)
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
        if not DEBUG: self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(4, -1, beamontime=self.__width,
                                                                                      delay=self.__delay)
        self.property_changed_event.fire('laser_delay_f')
        self.free_event.fire('all')

    @property
    def laser_width_f(self):
        return int(self.__width * 1e9)

    @laser_width_f.setter
    def laser_width_f(self, value):
        self.__width = float(value) / 1e9
        if not DEBUG: self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(4, -1, beamontime=self.__width,
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
        if self.fast_blanker_status_f:
            self.fast_blanker_status_f = False
            time.sleep(0.1)
            self.fast_blanker_status_f = True
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
            self.__powermeter_avg = int(value)
            self.__laser02.pw_set_avg(self.__powermeter_avg, '0')
            self.__laser02.pw_set_avg(self.__powermeter_avg, '1')
            #self.__pwmeter.pw_set_avg(self.__powermeter_avg)
            #self.__pwmeter02.pw_set_avg(self.__powermeter_avg)
        except:
            logging.info("***POWERMETER***: Please enter an integer.")

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
            logging.info('***LASER***: Please enter an integer for detectors grab. Using 0 instead.')

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
        self.__port = value
