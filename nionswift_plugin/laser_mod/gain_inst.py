# standard libraries
from nion.utils import Event
from nion.utils import Observable
from nion.swift.model import HardwareSource

import logging
import threading
import os
import json
import time

from . import gain_data as gdata

abs_path = os.path.abspath(os.path.join((__file__+"/../"), "global_settings.json"))
with open(abs_path) as savfile:
    settings = json.load(savfile)

DEBUG_pw = settings["PW"]["DEBUG"]
DEBUG_laser = settings["LASER"]["DEBUG"]
DEBUG_ps = settings["PS"]["DEBUG"]
DEBUG_servo = settings["SERVO"]["DEBUG"]
CAMERA = settings["CAMERA"]["WHICH"]
MAX_CURRENT = settings["PS"]["MAX_CURRENT"]
PW_AVG = settings["PW"]["AVG"]

DEBUG = DEBUG_pw and DEBUG_laser and DEBUG_ps and DEBUG_servo

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

        self.call_data=Event.Event()
        self.append_data=Event.Event()
        self.end_data=Event.Event()

        self.__start_wav = 575.0
        self.__finish_wav = 600.0
        self.__step_wav = 0.5
        self.__cur_wav = self.__start_wav
        self.__pts = int((self.__finish_wav - self.__start_wav) / self.__step_wav + 1)
        self.__avg = 5
        self.__tpts = int(self.__avg * self.__pts)
        self.__power = 0.
        self.__power_ref = 0.
        self.__diode = 0.10
        self.__servo_pos = 0
        self.__servo_wobbler = False
        self.__ctrl_type = 0
        self.__delay=1800 * 1e-9
        self.__width=50 * 1e-9
        self.__fb_status=False
        self.__counts = 0
        self.__frequency = 10000
        self.__acq_number = 0 #this is a strange variable. This mesures how many gain acquire you did in order to create new displays every new acquisition
        self.__powermeter_avg = PW_AVG
        self.__servo_step = 2

        self.__camera = None
        self.__data = None

        self.__thread = None
        self.__status = False
        self.__abort_force = False
        self.__power_ramp=False

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

        self.__OrsayScanInstrument = None
        self.__camera=None


    def init(self):

        for hards in HardwareSource.HardwareSourceManager().hardware_sources:  # finding eels camera. If you dont find, use usim eels
            if hasattr(hards, 'hardware_source_id'):
                if hards.hardware_source_id == CAMERA:
                    self.__camera = hards

        if self.__camera == None:
            for hards in HardwareSource.HardwareSourceManager().hardware_sources:  # finding eels camera. If you dont find, use usim eels
                if hasattr(hards, 'hardware_source_id'):
                    if hards.hardware_source_id == 'usim_eels_camera':
                        self.__camera = hards

        if not self.__camera:
            logging.info('***LASER***: No camera was found.')
        else:
            logging.info('***LASER***: Camera properly loaded. EELS/EEGS acquistion is good to go.')
            logging.info(self.__camera.hardware_source_id)


        self.__OrsayScanInstrument = HardwareSource.HardwareSourceManager().get_hardware_source_for_hardware_source_id("orsay_scan_device")
        if not self.__OrsayScanInstrument:
            logging.info('***LASER***: Could not find SCAN module. Check for issues')
        else:
            fast_blanker_status_f = False
            logging.info('***LASER***: SCAN module properly loaded. Fast blanker is good to go.')

    def sht(self):
        if self.sht_f == 'CLOSED':
            self.sht_f = True
        else:
            self.sht_f = False

    def lock(self):
        self.property_changed_event.fire("locked_power_f")
        self.free_event.fire("all")

    def hard_reset(self):
        self.__pwmeter.pw_reset()

    def diode(self, val):
        self.d_f = val

    def q(self, val):
        self.q_f = val

    def upt(self):

        self.property_changed_event.fire("cur_wav_f")
        self.property_changed_event.fire("power_f")
        if not self.__status:
            self.free_event.fire("all")

    def acq(self):
        self.__thread = threading.Thread(target=self.acqThread)
        self.__thread.start()

    def abt(self):
        logging.info("Abort scanning. Going back to origin...")
        self.__abort_force = True
        self.__laser.abort_control()  # abort laser thread as well.

    def acq_pr(self):
        self.__thread = threading.Thread(target=self.acq_prThread)
        self.__thread.start()

    def acq_prThread(self):
        self.run_status_f =  self.__power_ramp = self.sht_f = True
        self.__abort_force=False
        i_max = int(self.__servo_pos/self.__servo_step)
        j_max = self.__avg
        self.call_data.fire(self.__acq_number, i_max+1, j_max, self.__start_wav, self.__start_wav, 0.0, 1)
        self.__acq_number+=1
        self.__controlRout.pw_control_thread_on()
        i=0
        j=0
        while (i < i_max and not self.__abort_force):
            while (j < j_max and not self.__abort_force):
                last_cam_acq = self.__camera.grab_next_to_finish()[0]
                self.combo_data_f = True
                self.append_data.fire(self.combo_data_f, i, j, last_cam_acq)
                j+=1
            self.servo_f = self.servo_f - self.__servo_step
            j=0
            i+=1
        self.sht_f = False
        logging.info("***ACQUISITION***: Finishing laser measurement. Acquiring conventional EELS for reference.")
        while(j < j_max and not self.__abort_force):
            last_cam_acq = self.__camera.grab_next_to_finish()[0]
            self.combo_data_f = True
            self.append_data.fire(self.combo_data_f, i, j, last_cam_acq)
            j+=1

        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()  # turns off our periodic thread.
        self.__power_ramp = False
        self.end_data.fire()
        self.run_status_f=False

    def acqThread(self):
        self.run_status_f = True
        self.__abort_force = False

        # Laser thread begins
        if (self.__laser.set_scan_thread_check() and abs(
                self.__start_wav - self.__cur_wav) <= 0.001 and self.__finish_wav > self.__start_wav):

            self.call_data.fire(self.__acq_number, self.pts_f+1, self.avg_f, self.__start_wav, self.__finish_wav, self.__step_wav, self.__ctrl_type)
            self.__acq_number+=1


            self.__laser.set_scan(self.__cur_wav, self.__step_wav, self.__pts)
            self.sht_f = True
            self.__controlRout.pw_control_thread_on()
        else:
            logging.info("***LASER***: Last thread was not done || start and current wavelength differs || end wav < start wav")
            self.__abort_force = True

        i = 0  # e-point counter
        i_max = self.__pts
        j = 0  # each frame inside an specific e-point
        j_max = self.__avg  # dont put directly self.__avg because it will keep refreshing UI

        while (i < i_max and not self.__abort_force):  # i means our laser WL's
            while (j < j_max and not self.__abort_force):  # j is our averages
                last_cam_acq = self.__camera.grab_next_to_finish()[0] #get camera then check laser.
                self.combo_data_f = True #check laser now
                self.append_data.fire(self.combo_data_f, i, j, last_cam_acq)
                j += 1
            j = 0
            i += 1
            if (
                    self.__laser.set_scan_thread_hardware_status() == 2 and self.__laser.set_scan_thread_locked()):  # check if laser changes have finished and thread step is over
                self.__laser.set_scan_thread_release()  # if yes, you can advance
                logging.info('***LASER***: Moving to next wavelength...')
            else:
                self.abt()  # execute our abort routine (laser and acq thread)

        self.sht_f = False
        logging.info("***ACQUISITION***: Finishing laser measurement. Acquiring conventional EELS for reference.")
        while (j < j_max and not self.__abort_force):
            last_cam_acq = self.__camera.grab_next_to_finish()[0] 
            self.combo_data_f = True
            self.append_data.fire(self.combo_data_f, i, j, last_cam_acq)
            j += 1

        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()  # turns off our periodic thread.
        self.__camera.stop_playing()  # stop camera
        while (
        not self.__laser.set_scan_thread_check()):  # thread MUST END for the sake of security. Better to be looped here indefinitely than fuck the hardware
            if self.__laser.set_scan_thread_locked():  # releasing everything if locked
                self.__laser.set_scan_thread_release()

        self.run_status_f = False  # acquistion is over
        self.start_wav_f=self.__start_wav
        self.end_data.fire()

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
                    "***LASER***: Laser Motor is moving. You can not change wavelength while last one is still "
                    "moving. Please increase camera dwell time or # of averages in order to give time to our slow "
                    "hardware.")
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
                if self.__ctrl_type == 1:
                    self.servo_f=self.servo_f+1 if self.__power<self.__power_ref else self.servo_f-1
                    if self.__servo_pos > 180: self.__servo_pos = 180
                    if self.__servo_pos < 0: self.__servo_pos = 0
                if self.__ctrl_type == 2:
                    self.__diode = self.__diode + 0.02 if self.__power < self.__power_ref else self.__diode - 0.02
                    self.cur_d_f = self.__diode

            if message == 102:
                logging.info('***CONTROL***: Control OFF but it was never on.')

        return sendMessage

    def Laser_stop_all(self):
        self.sht_f=False
        self.fast_blanker_status_f=False
        self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(0, -1, self.__width, True, 0, self.__delay)

    @property
    def start_wav_f(self) -> float:
        return self.__start_wav

    @start_wav_f.setter
    def start_wav_f(self, value: float) -> None:
        self.__start_wav = float(value)
        self.busy_event.fire("all")
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
    def power_f(self):
        if DEBUG_pw:
            self.__power = (self.__pwmeter.pw_read() + (self.__diode) ** 2) * (self.__servo_pos + 1) / 180 if self.sht_f=='OPEN' else self.__pwmeter.pw_read()
        else:
            self.__power = self.__pwmeter.pw_read()
        return format(self.__power, '.2f')


    @property
    def locked_power_f(self):
        self.__power_ref = self.__power
        return format(self.__power_ref, '.2f')


    @property
    def cur_d_f(self) -> int:
        return int(self.__diode*100)

    @cur_d_f.setter
    def cur_d_f(self, value: int):
        self.__diode = value/100
        cvalue = format(float(self.__diode), '.2f')  # how to format and send to my hardware
        if self.__diode < MAX_CURRENT:
            self.__ps.comm('C1:' + str(cvalue) + '\n')
            self.__ps.comm('C2:' + str(cvalue) + '\n')
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
        self.__diode=float(value)

        if not self.__status:
            self.property_changed_event.fire("power_f")
            self.property_changed_event.fire("cur_d1_f")
            self.property_changed_event.fire("cur_d2_f")
            self.property_changed_event.fire("cur_d_f") #He will call slider setter so no need to actually update value
            self.property_changed_event.fire("cur_d_edit_f")
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
            self.servo_f=self.__servo_pos
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
            self.property_changed_event.fire("power_f")
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
        self.__fb_status=value
        if value:
            self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(4, -1, beamontime=self.__width, delay=self.__delay)
            self.__OrsayScanInstrument.scan_device.orsayscan.SetLaser(self.__frequency, 5000000, False, -1)
            self.__OrsayScanInstrument.scan_device.orsayscan.StartLaser(7)
        else:
            self.__OrsayScanInstrument.scan_device.orsayscan.CancelLaser()
            self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(0, -1, self.__width, True, 0, self.__delay)
        self.property_changed_event.fire('fast_blanker_status_f')
        self.free_event.fire('all')

    @property
    def laser_delay_f(self):
        return int(self.__delay*1e9)

    @laser_delay_f.setter
    def laser_delay_f(self, value):
        self.__delay = float(value)/1e9
        if not DEBUG: self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(4, -1, beamontime=self.__width, delay=self.__delay)
        self.property_changed_event.fire('laser_delay_f')
        self.free_event.fire('all')

    @property
    def laser_width_f(self):
        return int(self.__width*1e9)

    @laser_width_f.setter
    def laser_width_f(self, value):
        self.__width=float(value)/1e9
        if not DEBUG: self.__OrsayScanInstrument.scan_device.orsayscan.SetTopBlanking(4, -1, beamontime=self.__width, delay=self.__delay)
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
            self.fast_blanker_status_f=False
            time.sleep(0.1)
            self.fast_blanker_status_f=True
        self.property_changed_event.fire('laser_frequency_f')
        self.free_event.fire('all')

    @property
    def combo_data_f(self):
        if self.__ctrl_type==1 or self.__power_ramp:
            return [self.__cur_wav, self.__power, self.__servo_pos]
        if self.__ctrl_type==2:
            return [self.__cur_wav, self.__power, self.__diode]
        else:
            return [self.__cur_wav, self.__power]

    @combo_data_f.setter
    def combo_data_f(self, value):
        self.property_changed_event.fire("cur_wav_f")
        if self.__ctrl_type==1 or self.__power_ramp: self.property_changed_event.fire("servo_f")
        if self.__ctrl_type==2: self.property_changed_event.fire("cur_d_f")
        if not value and not self.__status: self.free_event.fire('all')

    @property
    def powermeter_avg_f(self):
        return self.__powermeter_avg

    @powermeter_avg_f.setter
    def powermeter_avg_f(self, value):
        try:
            self.__powermeter_avg = int(value)
            self.__pwmeter.pw_set_avg(self.__powermeter_avg)
        except:
            logging.info("***POWERMETER***: Please enter an integer.")

