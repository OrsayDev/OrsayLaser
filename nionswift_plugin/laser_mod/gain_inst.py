# standard libraries
from nion.utils import Event
from nion.utils import Observable
from nion.swift.model import HardwareSource
from nion.swift.model import DataItem

import logging
import time
import threading
import os
import json

from . import gain_data as gdata

abs_path = os.path.abspath(os.path.join((__file__+"/../"), "global_settings.json"))
with open(abs_path) as savfile:
    settings = json.load(savfile)

DEBUG_pw = settings["PW"]["DEBUG"]
DEBUG_laser = settings["LASER"]["DEBUG"]
DEBUG_ps = settings["PS"]["DEBUG"]
DEBUG_servo = settings["SERVO"]["DEBUG"]

if DEBUG_pw:
    from . import power_vi as power
else:
    from . import power as power

if DEBUG_laser:
    from . import laser_vi as laser
else:
    from . import laser as laser

if DEBUG_ps:
    from . import power_supply_vi as ps
else:
    from . import power_supply as ps

if DEBUG_servo:
    from . import servo_vi as servo
else:
    from . import servo as servo

from . import control_routine as ctrlRout


class gainDevice(Observable.Observable):

    def __init__(self):
        self.property_changed_event = Event.Event()
        self.free_event = Event.Event()
        self.communicating_event = Event.Event()
        self.busy_event = Event.Event()

        self.__start_wav = 575.0
        self.__finish_wav = 605.0
        self.__step_wav = 1.0
        self.__cur_wav = self.__start_wav
        self.__pts = int((self.__finish_wav - self.__start_wav) / self.__step_wav + 1)
        self.__avg = 20
        self.__tpts = int(self.__avg * self.__pts)
        self.__dwell = 10
        self.__power = 0.
        self.__power_ref = 0.
        self.__diode = 10
        self.__servo_pos = 0
        self.__ctrl_type = 0

        self.__camera = None
        self.__data = None

        self.__thread = None
        self.__status = False
        self.__stored = False
        self.__abort_force = False

        self.__sendmessage = laser.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__laser = laser.SirahCredoLaser(self.__sendmessage)

        self.__power_sendmessage = power.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__pwmeter = power.TLPowerMeter(self.__power_sendmessage)

        self.__ps_sendmessage = ps.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__ps = ps.SpectraPhysics(self.__ps_sendmessage)

        self.__data_sendmessage = gdata.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__gdata = gdata.gainData(self.__data_sendmessage)

        self.__servo_sendmessage = servo.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__servo = servo.servoMotor(self.__servo_sendmessage)

        self.__control_sendmessage = ctrlRout.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__controlRout = ctrlRout.controlRoutine(self.__control_sendmessage)

    def init(self):

        for hards in HardwareSource.HardwareSourceManager().hardware_sources:  # finding eels camera. If you dont find, use usim eels
            if hasattr(hards, 'hardware_source_id'):
                if hards.hardware_source_id == 'orsay_camera_eire':
                    self.__camera = hards

        if self.__camera == None:
            for hards in HardwareSource.HardwareSourceManager().hardware_sources:  # finding eels camera. If you dont find, use usim eels
                if hasattr(hards, 'hardware_source_id'):
                    if hards.hardware_source_id == 'usim_eels_camera':
                        self.__camera = hards

        self.__frame_parameters = self.__camera.get_current_frame_parameters()
        logging.info(self.__camera.hardware_source_id)
        self.dwell_f=0.1

    def sht(self):
        if self.sht_f == 'CLOSED':
            self.sht_f = True
        else:
            self.sht_f = False

    def lock(self):
        self.property_changed_event.fire("locked_power_f")
        self.free_event.fire("all")

    def diode(self, val):
        self.d_f = val

    def q(self, val):
        self.q_f = val

    def more_cur(self):
        self.cur_d_f += 5

    def less_cur(self):
        self.cur_d_f -= 5

    def more_servo(self):
        self.servo_f += 2
        self.property_changed_event.fire('servo_f')
        self.free_event.fire("all")

    def less_servo(self):
        self.servo_f -= 2
        self.property_changed_event.fire('servo_f')
        self.free_event.fire("all")

    def upt(self):

        self.property_changed_event.fire("cur_wav_f")
        self.property_changed_event.fire("power_f")
        if not self.__status:
            self.free_event.fire("all")

    def acq(self):
        self.__camera.set_current_frame_parameters(self.__frame_parameters)
        self.__thread = threading.Thread(target=self.acqThread)
        self.__thread.start()

    def gen(self):
        if self.__stored:
            self.stored_status_f = False
            intensity_calibration = self.__data[0][
                0].intensity_calibration  # we first pick up this parameter here and modify later on
            dimensional_calibrations = self.__data[0][0].dimensional_calibrations
            sum_data, max_index = self.__gdata.send_raw_MetaData(
                self.__data)  # this aligned and returns data to be appended in a data_item
            data_item = DataItem.DataItem(large_format=True)  # Creating Data Item
            data_item.set_data(sum_data)  # Setting data
            int_cal, dim_cal = self.__gdata.data_item_calibration(intensity_calibration, dimensional_calibrations,
                                                                  self.__start_wav, self.__step_wav, 0.013,
                                                                  max_index)  # Modifying and setting int/dimensional calib. Check gain_data.py for info on how this is done
            data_item.set_intensity_calibration(int_cal)
            data_item.set_dimensional_calibrations(dim_cal)

            data_item2 = DataItem.DataItem()
            wl_data, pw_data, di_data = self.__gdata.send_info_data(self.__infodata)
            data_item2.set_data(wl_data)

            data_item3 = DataItem.DataItem()
            data_item3.set_data(pw_data)

            data_item4 = DataItem.DataItem()
            data_item4.set_data(di_data)

            logging.info("Generating our data..")
            self.property_changed_event.fire("stored_status")
            self.free_event.fire("all")

            # send data_item back to gain_panel, the one who has control over document_controller
            return data_item, data_item2, data_item3, data_item4
        else:
            return None

    def abt(self):
        logging.info("Abort scanning. Going back to origin...")
        self.__abort_force = True
        self.__laser.abort_control()  # abort laser thread as well.

    def acqThread(self):
        self.run_status_f = True

        self.__laser.setWL(self.__start_wav, self.__cur_wav)
        self.__abort_force = False

        # Laser thread begins
        if (self.__laser.set_scan_thread_check() and abs(
                self.__start_wav - self.__cur_wav) <= 0.001 and self.__finish_wav > self.__start_wav):
            self.__laser.set_scan(self.__cur_wav, self.__step_wav, self.__pts)
            self.sht_f = True
            self.__controlRout.pw_control_thread_on()
        else:
            logging.info("Last thread was not done || start and current wavelength differs || end wav < start wav")
            self.__abort_force = True
        self.__data = []
        self.__infodata = []
        i = 0  # e-point counter
        i_max = self.__pts
        j = 0  # each frame inside an specific e-point
        j_max = self.__avg  # dont put directly self.__avg because it will keep refreshing UI

        while (i < i_max and not self.__abort_force):  # i means our laser WL's
            self.__data.append([])
            self.__infodata.append([])
            while (j < j_max and not self.__abort_force):  # j is our averages
                self.__data[i].append(self.__camera.grab_next_to_start()[0])
                if j % 1 == 0:
                    self.combo_data_f = True
                    self.__infodata[i].append(self.combo_data_f)
                j += 1
            j = 0
            i += 1
            if (
                    self.__laser.set_scan_thread_hardware_status() == 2):  # check if laser changes have finished and thread step is over
                self.__laser.set_scan_thread_release()  # if yes, you can advance
            else:
                self.abt()  # execute our abort routine (laser and acq thread)

        self.sht_f = False
        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()  # turns off our periodic thread.
        self.__camera.stop_playing()  # stop camera
        while (
        not self.__laser.set_scan_thread_check()):  # thread MUST END for the sake of security. Better to be looped here indefinitely than fuck the hardware
            if self.__laser.set_scan_thread_locked():  # releasing everything if locked
                self.__laser.set_scan_thread_release()

        self.stored_status_f = True and not self.__abort_force  # Stored is true conditioned that loop was not aborted
        self.run_status_f = False  # acquistion is over
        self.start_wav_f=self.__start_wav


        # 0-20: laser; 21-40: power meter; 41-60: data analyses; 61-80: power supply; 81-100: servo; 101-120: control
    def sendMessageFactory(self):
        def sendMessage(message):
            if message == 1:
                logging.info("***LASER***: start WL is current WL")
                self.run_status_f=False
                self.combo_data_f = False
            if message == 2:
                logging.info("***LASER***: Current WL updated")
                self.run_status_f=False
                self.combo_data_f = False
            if message == 3:
                logging.info(
                    "***LASER***: Laser Motor is moving. You can not change wavelength while last one is still moving. Please increase camera dwell time or # of averages in order to give time to our slow hardware.")
            if message == 5:
                logging.info("***LASER***: Could not write in laser serial port. Check port.")
            if message == 6:
                logging.info("***LASER***: Could not write/read in laser serial port. Check port.")
            if message == 7:
                logging.info("***LASER***: Could not open serial port. Check if connected and port.")
            if message == 8:
                logging.info('***LASER***: Status was not 02 or 03. Problem receiving bytes from laser hardware.')
            if message == 21:
                logging.info('***Power Meter***: Cant write')
            if message == 22:
                logging.info('***Power Meter***: Cant READ a new measurement. Fetching last one instead.')
            if message == 23:
                self.property_changed_event.fire("power_f")
                self.free_event.fire("all")
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
                if self.__ctrl_type == 1:
                    s_val = int((self.__power_ref / self.__power - 1) * 90)
                    self.__servo_pos = self.__servo_pos + s_val
                    # self.__servo_pos=self.__servo_pos+1 if self.__power<self.__power_ref else self.__servo_pos-2
                    if not s_val: self.servo_f = self.__servo_pos
                    if self.__servo_pos > 180: self.__servo_pos = 180
                    if self.__servo_pos < 0: self.__servo_pos = 0
                if self.__ctrl_type == 2:
                    self.__diode = self.__diode + 2 if self.__power < self.__power_ref else self.__diode - 4
                    self.cur_d_f = self.__diode

            if message == 102:
                logging.info('***CONTROL***: Control OFF but it was never on.')

        return sendMessage

    @property
    def start_wav_f(self) -> float:
        return self.__start_wav

    @start_wav_f.setter
    def start_wav_f(self, value: float) -> None:
        self.__start_wav = float(value)
        self.busy_event.fire("all")
        #if not self.__status and abs(self.cur_wav_f-self.__start_wav)>0.001:
        if not self.__status:
            self.run_status_f=True
            self.__laser.setWL(self.__start_wav, self.__cur_wav)


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
    def dwell_f(self) -> int:
        return self.__dwell

    @dwell_f.setter
    def dwell_f(self, value: float) -> None:
        self.__dwell = float(value)
        self.__frame_parameters["exposure_ms"] = self.__dwell

    @property
    def tpts_f(self) -> int:
        self.__tpts = int(int(self.__avg) * int(self.__pts))
        return self.__tpts

    @property
    def pts_f(self) -> float:
        self.__pts = int((float(self.__finish_wav) - float(self.__start_wav)) / float(self.__step_wav) + 1)
        return self.__pts

    @property  # we dont set cur_wav using setters/getters but rather using our routines. This allow us to be more specific for our purposes
    def cur_wav_f(self) -> float:
        self.__cur_wav = self.__laser.get_hardware_wl()[0]
        self.__pwmeter.pw_set_wl(self.__cur_wav)
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
    def stored_status_f(self):
        return str(self.__stored)

    @stored_status_f.setter
    def stored_status_f(self, value):
        self.__stored = value
        self.property_changed_event.fire('stored_status_f')
        if not self.__status: self.free_event.fire('all')

    @property
    def power_f(self):
        if DEBUG_pw:
            self.__power = (self.__pwmeter.pw_read() + (self.__diode / 100.) ** 2) * (self.__servo_pos + 1) / 180
        else:
            self.__power = self.__pwmeter.pw_read()
        return round(self.__power, 4)

    @property
    def locked_power_f(self):
        self.__power_ref = self.__power
        return round(self.__power_ref, 4)

    @property
    def cur_d_f(self) -> int:
        return self.__diode

    @cur_d_f.setter
    def cur_d_f(self, value: int):
        self.__diode = int(value)
        cvalue = format(float(self.__diode / 100), '.2f')  # how to format and send to my hardware
        self.__ps.comm('C1:' + str(cvalue) + '\n')
        self.__ps.comm('C2:' + str(cvalue) + '\n')

        if not self.__status:
            self.property_changed_event.fire("power_f")
            self.property_changed_event.fire("cur_d1_f")
            self.property_changed_event.fire("cur_d2_f")
            self.property_changed_event.fire("cur_d_f")
            self.free_event.fire("all")

    @property
    def cur_d1_f(self):
        return self.__ps.query('?C1\n').decode('UTF-8').replace('\n', '')

    @property
    def cur_d2_f(self):
        return self.__ps.query('?C2\n').decode('UTF-8').replace('\n', '')

    @property
    def sht_f(self):
        return self.__ps.query('?SHT\n').decode('UTF-8').replace('\n', '')

    @sht_f.setter
    def sht_f(self, value: bool):
        if value == True:
            self.__ps.comm('SHT:1\n')
        else:
            self.__ps.comm('SHT:0\n')

        self.property_changed_event.fire('sht_f')
        if not self.__status: self.free_event.fire('all')

    @property
    def d_f(self):
        return self.__ps.query('?D\n').decode('UTF-8').replace('\n', '')

    @d_f.setter
    def d_f(self, value: bool):
        if value == True:
            self.__ps.comm('D:1\n')
        else:
            self.__ps.comm('D:0\n')

        self.property_changed_event.fire('d_f')  # kill GUI and updates fast OFF response
        threading.Timer(3, self.property_changed_event.fire, args=('d_f',)).start()  # update in case of slow response
        threading.Timer(3.1, self.free_event.fire, args=('all',)).start()  # retake GUI

    @property
    def q_f(self):
        return self.__ps.query('?G\n').decode('UTF-8').replace('\n', '')

    @q_f.setter
    def q_f(self, value: bool):
        if value == True:
            self.__ps.comm('G:1\n')
        else:
            self.__ps.comm('G:0\n')
        self.property_changed_event.fire('q_f')
        self.free_event.fire("all")

    @property
    def ascii_f(self):
        return '-'
        # if self.__ps.query('?SHT\n').decode('UTF-8').replace('\n', '')=='OPEN':
        # return '\n-------o-------\n'
        # else:
        #    return '\n-------x-------\n'

    @property
    def servo_f(self):
        if not self.__status:
            return int(self.__servo.get_pos().decode('UTF-8'))
        else:
            return self.__servo_pos

    @servo_f.setter
    def servo_f(self, value: int):
        self.__servo_pos = value
        self.__servo.set_pos(self.__servo_pos)
        if not self.__status:
            self.property_changed_event.fire("power_f")
            self.free_event.fire('all')

    @property
    def pw_ctrl_type_f(self):
        return self.__ctrl_type

    @pw_ctrl_type_f.setter
    def pw_ctrl_type_f(self, value):
        self.__ctrl_type = value

    @property
    def combo_data_f(self):
        return [self.__cur_wav, self.__power, self.__servo_pos]

    @combo_data_f.setter
    def combo_data_f(self, value):
        self.property_changed_event.fire("cur_wav_f")
        self.property_changed_event.fire("cur_d_f")
        self.property_changed_event.fire("servo_f")
        if not value and not self.__status: self.free_event.fire('all')
