# standard libraries
from nion.utils import Event
from nion.utils import Observable
from nion.utils import Registry
from nion.swift.model import HardwareSource

import logging
import threading
import time
import numpy

from . import NKTModules

class LaserWrapper:
    def __init__(self):
        #NKTModules.init_ethernet_connection()
        self.__Laser = NKTModules.SuperFianium('COM5')
        self.__Varia = NKTModules.Varia('COM5')
        self.__bandwidth = 10.0

    def check(self):
        return True

    def setWL(self, wl: int, cur_wl: int):
        self.__Varia.filter_setpoint1 = 100
        self.__Varia.filter_setpoint2 = wl + self.__bandwidth
        self.__Varia.filter_setpoint3 = wl
        return 1

    def getWL(self):
        return (self.__Varia.filter_setpoint2 + self.__Varia.filter_setpoint3) / 2

    def abort_control(self):
        pass





from . import control_routine as ctrlRout

def SENDMYMESSAGEFUNC(sendmessagefunc):
    return sendmessagefunc


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
        self.__cur_wav = 575.0
        self.__step_wav = 1.0
        self.__pts = int((self.__finish_wav - self.__start_wav) / self.__step_wav + 1)
        self.__avg = 10
        self.__tpts = int(self.__avg * self.__pts)
        self.__power = 0.
        self.__powermeter_avg = 10

        self.__camera = None
        self.__data = None

        self.__thread = None
        self.__status = True #we start it true because before init everything must be blocked. We free after a succesfull init
        self.__abort_force = False
        self.__power_ramp = False
        self.__bothPM = False

        self.__Laser = None
        self.__PM = None
        self.__camera = None
        self.__DEBUG = False

        #Initial status of the Microscope
        self.__defocus_check = False
        main_controller = Registry.get_component("stem_controller")
        ok, value = main_controller.TryGetVal("C10")
        if ok:
            self.__defocus = value

    def server_instrument_ping(self):
        self.__Laser.check()

    def server_instrument_shutdown(self):
        for server in [self.__Laser, self.__PM]:
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

        self.__Laser = LaserWrapper()
        self.run_status_f = False
        return True

    def sht(self):
        if self.sht_f == 'CLOSED':
            self.sht_f = True
        else:
            self.sht_f = False

    def lock(self):
        self.property_changed_event.fire("locked_power_f")
        self.free_event.fire("all")

    def hard_reset(self):
        self.__PM.pw_reset('0')

    def upt(self):
        # self.property_changed_event.fire("cur_wav_f")
        # self.property_changed_event.fire("power_f")
        # self.property_changed_event.fire("power02_f")
        # self.property_changed_event.fire("power_transmission_f")
        # self.property_changed_event.fire('t_d1_f')
        # self.property_changed_event.fire('t_d2_f')
        # self.property_changed_event.fire('cur_d1_f')
        # self.property_changed_event.fire('cur_d2_f')
        # self.property_changed_event.fire('servo_f')

        if not self.__status:
            self.free_event.fire("all")

    # def grab_det(self, mode, index, npic, show):
    #     logging.info("***LASER***: Scanning Full Image.")
    #     # this gets frame parameters
    #     det_frame_parameters = self.__OrsayScanInstrument.get_current_frame_parameters()
    #     # this multiplies pixels(x) * pixels(y) * pixel_time
    #     frame_time = self.__OrsayScanInstrument.calculate_frame_time(det_frame_parameters)
    #     self.__OrsayScanInstrument.start_playing()
    #     time.sleep(frame_time * 1.2)  # 20% more of the time for a single frame
    #     det_di = self.__OrsayScanInstrument.grab_next_to_start()
    #
    #     self.__OrsayScanInstrument.abort_playing()
    #     self.det_acq.fire(det_di, mode, index, npic, show)

    def abt(self):
        logging.info('***LASER***: Abort Measurement.')
        if not self.__abort_force:
            self.__abort_force = True
            self.__Laser.abort_control()  # abort laser thread as well.
        try:
            self.__thread.join()
        except AttributeError:
            pass

        logging.info(f'***LASER***: Number of Threads current alive is {threading.active_count()}')
        self.run_status_f = False  # force free GUI

    def acq_mon(self):
        if self.__Laser.check():
            self.__thread = threading.Thread(target=self.acq_monThread)
            self.__thread.start()

    def acq_pwsustain(self):
        if self.__Laser.check():
            self.__thread = threading.Thread(target=self.acq_pwsustainThread)
            self.__thread.start()

    """
    def acq_trans(self):
        self.__acq_number += 1
        if self.__serverLaser.check():
            self.__thread = threading.Thread(target=self.acq_transThread)
            self.__thread.start()
    """

    def acq_raster(self):
        if self.__Laser.check():
            self.__thread = threading.Thread(target=self.acq_rasterThread)
            self.__thread.start()

    def acq_pr(self):
        if self.__Laser.check():
            self.__thread = threading.Thread(target=self.acq_prThread)
            self.__thread.start()

    def acq(self):
        if self.__Laser.check():
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
        self.__controlRout.pw_control_thread_on(self.__powermeter_avg * 0.003 * 4.0)
        while not self.__abort_force:
            self.append_monitor_data.fire((self.__power, self.__power02), loop_index)
            loop_index += 1
            if loop_index == 200: loop_index=0
        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()

        self.end_data_monitor.fire()
        self.__bothPM = self.__power_ramp = False
        self.run_status_f = False

    def acq_pwsustainThread(self):
        '''
        Power sustain thread. This blocks GUI and is control the servo in order to lock the current power.

        '''
        self.run_status_f = self.__bothPM = True
        self.__abort_force = False
        loop_index = 0
        self.__controlRout.pw_control_thread_on(self.__powermeter_avg * 0.003 * 4.0)
        while not self.__abort_force:
            self.combo_data_f = True  # check laser and servo now
        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()

        self.__bothPM = False
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

    def acq_rasterThread(self):
        """"
        Rastering thread. This loops the wavelength of the laser up and down until
        abort is clicked.
        """
        self.run_status_f = True
        self.__abort_force = False
        self.__servo_pos_initial = self.__servo_pos

        # Laser thread begins

        if (self.__Laser.set_scan_thread_check() and abs(
                self.__start_wav - self.__cur_wav) <= 0.001 and self.__finish_wav > self.__start_wav):
            self.sht_f = True
            self.__controlRout.pw_control_thread_on(self.__powermeter_avg * 0.003 * 4.0)
        else:
            logging.info(
                "***LASER***: Last thread was not done || start and current wavelength differs || end wav < start wav || Not Focus mode.")
            self.run_status_f = False  # acquisition is over
            return
            # self.__abort_force = True

        def run_function():
            if self.__abort_force: return True
            _response = self.__Laser.setWL(self.__start_wav + i * step, self.__cur_wav)
            for _ in range(10):
                self.combo_data_f = True
                time.sleep(1.0)
                if self.__abort_force: return True
            return False

        i = 0  # e-point counter
        n = self.__pts #Number of points
        step = self.__step_wav
        while not self.__abort_force:
            for i in range(n):
                if run_function(): break
            for i in range(n-2, -1, -1):
                if run_function(): break

        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()
        self.run_status_f = False
        self.combo_data_f = True

    def acq_prThread(self):
        self.run_status_f = self.__power_ramp = True
        self.__abort_force = False
        self.__servo_pos_initial = self.__servo_pos

        # Laser power resolved thread begins
        p = "acquistion_mode" in self.__camera.get_current_frame_parameters().as_dict()
        q = self.__camera.get_current_frame_parameters().as_dict()['acquisition_mode'] == 'Focus' if p else True
        if (self.__Laser.set_scan_thread_check() and abs(
                self.__start_wav - self.__cur_wav) <= 0.001 and self.__finish_wav > self.__start_wav and q):
            self.__acq_number += 1
            self.__camera.start_playing()
            last_cam_acq = self.__camera.grab_next_to_finish()[0]  # get camera then check laser.
            self.call_data.fire(self.__acq_number, self.servo_pts_f + 1, self.avg_f, self.__start_wav, self.__finish_wav,
                                self.__step_wav, last_cam_acq, ctrl=self.__ctrl_type,
                                delay=self.__delay, width=self.__width, diode=self.__diode,
                                transmission=self.__power_transmission,
                                camera=last_cam_acq.metadata)
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
        p = "acquistion_mode" in self.__camera.get_current_frame_parameters().as_dict()
        q =  self.__camera.get_current_frame_parameters().as_dict()['acquisition_mode'] == 'Focus' if p else True
        if (self.__Laser.set_scan_thread_check() and abs(
                self.__start_wav - self.__cur_wav) <= 0.001 and self.__finish_wav > self.__start_wav and q):

            self.__acq_number += 1
            self.__camera.start_playing()
            last_cam_acq = self.__camera.grab_next_to_finish()[0]  # get camera then check laser.

            self.call_data.fire(self.__acq_number, self.pts_f + 1, self.avg_f, self.__start_wav, self.__finish_wav,
                                self.__step_wav, last_cam_acq, ctrl=self.__ctrl_type,
                                delay=self.__delay, width=self.__width, diode=self.__diode,
                                transmission=self.__power_transmission,
                                camera=last_cam_acq.metadata)
            #self.grab_det("init", self.__acq_number, 0, True)  # after call_data.fire
            pics_array = numpy.linspace(0, self.__pts, min(self.__nper_pic + 2, self.__pts + 1), dtype=int)
            pics_array = pics_array[1:]  # exclude zero
            self.__Laser.set_scan(self.__cur_wav, self.__step_wav, self.__pts)
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
                    self.__Laser.set_scan_thread_hardware_status() == 2 and self.__Laser.set_scan_thread_locked()):
                # check if laser changes have finished and thread step is over
                self.__Laser.set_scan_thread_release()  # if yes, you can advance
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
                not self.__Laser.set_scan_thread_check()):  # thread MUST END for the sake of security. Better to be
            # looped here indefinitely than fuck the hardware
            if self.__Laser.set_scan_thread_locked():  # releasing everything if locked
                self.__Laser.set_scan_thread_release()
        #self.grab_det("end", self.__acq_number, 0, True)
        #self.start_wav_f = self.__start_wav
        self.end_data.fire()
        self.run_status_f = False  # acquisition is over


    def wavelength_ready(self):
        if not abs(self.__start_wav - self.__cur_wav) <= 0.005:
            self.property_changed_event.fire("cur_wav_f")  # don't need a thread.
            time.sleep(0.25)
            self.wavelength_ready()
        else:
            self.power_wav_f = self.__cur_wav
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
            response = self.__Laser.setWL(self.__start_wav, self.__cur_wav)
            if response == 1:
                logging.info("***LASER***: start WL is current WL")
                self.property_changed_event.fire("cur_wav_f")
                self.run_status_f = False
                #self.combo_data_f = False #when false, GUI is fre-ed by status
            elif response == 2:
                logging.info("***LASER***: Current WL being updated...")
                self.property_changed_event.fire("cur_wav_f")
                self.run_status_f = True
                #self.combo_data_f = False #when false, GUI is fre-ed by status
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
    def pts_f(self) -> int:
        self.__pts = int((float(self.__finish_wav) - float(self.__start_wav)) / float(self.__step_wav) + 1)
        return self.__pts

    @property
    def cur_point_lazy_f(self) -> int:
        return int((float(self.__cur_wav) - float(self.__start_wav)) / float(self.__step_wav) + 1)

    @property  # we dont set cur_wav but rather start wav.
    def cur_wav_f(self) -> str:
        if not self.__Laser:
            return 'None'
        else:
            self.__cur_wav = self.__Laser.getWL()
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
            self.__power = self.__PM.pw_read('0', self.__cur_wav)
            return format(self.__power, '.3f')
        except AttributeError:
            return 'None'




    @property
    def defocus_value_f(self):
        return int(self.__defocus * 1e9)

    @defocus_value_f.setter
    def defocus_value_f(self, value):
        self.__defocus = int(value) / 1e9
        self.property_changed_event.fire('defocus_f')
        self.free_event.fire('all')

    @property
    def defocus_check_f(self):
        return self.__defocus_check

    @defocus_check_f.setter
    def defocus_check_f(self, value):
        self.__defocus_check = value
        main_controller = Registry.get_component("stem_controller")
        scan_controller = main_controller.scan_controller
        if value:
            if 0 < self.__defocus <= 0.0001:
                main_controller.SetVal("C10", self.__defocus)
                scan_controller.stop_playing()
        else:
            main_controller.SetVal("C10", 0)
            scan_controller.start_playing()
        self.property_changed_event.fire('defocus_check_f')
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
