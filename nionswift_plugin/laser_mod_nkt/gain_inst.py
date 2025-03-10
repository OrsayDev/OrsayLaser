# standard libraries
from nion.utils import Event
from nion.utils import Observable
from nion.utils import Registry
from nion.swift.model import HardwareSource

import logging
import threading
import time

from . import control_routine as ctrlRout
from SirahCredoServer import power
from . import NKTModules

class LaserWrapperDebug:
    def __init__(self, connectionId: str = 'COM5'):
        self.__lowerWL = 580
        self.__upperWL = 600
        self.__intensity = 10
        self.__emission = False
        self.__delay = 0
        self.__start_time = None

    def check(self):
        return True

    def check_status(self):
        if self.__start_time is None:
            return True
        elapsed_time = time.time() - self.__start_time
        return elapsed_time > 0.1

    def setWL(self, wl: float):
        bd = self.__upperWL - self.__upperWL
        self.__upperWL = wl + bd / 2
        self.__lowerWL = wl - bd / 2
        self.__start_time = time.time()

    def getWL(self):
        return (self.__lowerWL + self.__upperWL) / 2

    def abort_control(self):
        pass

    def setBandwidth(self, bandwidth: int):
        wl = self.getWL()
        self.__upperWL = wl + bandwidth / 2
        self.__lowerWL = wl - bandwidth / 2

    def getBandwidth(self):
        return (self.__upperWL - self.__lowerWL)

    def setEmission(self, value: bool):
        self.__emission = value

    def getEmission(self):
        return self.__emission

    def setDelay(self, value: int):
        self.__delay = value

    def getDelay(self):
        return self.__delay

    def getPower(self):
        return self.__intensity

    def setPower(self, value: int):
        self.__intensity = value


class LaserWrapper:
    def __init__(self, connectionId: str = 'COM5'):
        handler = NKTModules.ConnectionHandler(connectionId)
        self.__Laser = NKTModules.SuperFianium(handler)
        self.__Varia = NKTModules.Varia(handler)
        self.__RF = NKTModules.RFDriver(handler)

        # Checking if the RF driver is present. It is either the Varia or the RF + Select
        self.__isRF = False
        if self.__RF.ping() != 'None':
            self.__isRF = True

        # Initial conditions for the experiment
        if not self.__isRF:
            self.__Varia.filter_setpoint1 = 100 #Starting with maximum neutral-density value

        self.__bandwidth = None
        self.__centralWL = None

    def ping_all(self):
        self.__Laser.ping()
        self.__Varia.ping()
        self.__RF.ping()

    def check(self):
        return True

    def check_status(self):
        if not self.__isRF:
            return not self.__Varia.filter_moving()
        return True # Currently always True if the RF driver is present

    def setWL(self, wl: float):
        if not self.__isRF:
            self.__centralWL = wl
            self.__Varia.filter_setpoint2 = wl + self.__bandwidth / 2
            self.__Varia.filter_setpoint3 = wl - self.__bandwidth / 2
        else:
            self.setRFWavelength(0, wl)

    def getWL(self):
        if not self.__isRF:
            self.__centralWL = (self.__Varia.filter_setpoint2 + self.__Varia.filter_setpoint3) / 2
            return self.__centralWL
        else:
            return self.getRFWavelength(0)

    def abort_control(self):
        pass

    def setBandwidth(self, bandwidth: int):
        if not self.__isRF:
            self.__bandwidth = bandwidth
            self.__Varia.filter_setpoint2 = self.__centralWL + bandwidth / 2
            self.__Varia.filter_setpoint3 = self.__centralWL - bandwidth / 2

    def getBandwidth(self):
        if not self.__isRF:
            self.__bandwidth = self.__Varia.filter_setpoint2 - self.__Varia.filter_setpoint3
            return self.__bandwidth
        else:
            return 1.0 #This is the bandwidth for the cavity

    def setEmission(self, value: bool):
        self.__Laser.emission = 3 if value else 0

    def getEmission(self):
        return self.__Laser.emission == 3

    def setDelay(self, value: int):
        self.__Laser.nim_delay = value

    def getDelay(self):
        return self.__Laser.nim_delay

    def getPower(self):
        return self.__Laser.power

    def setPower(self, value: int):
        self.__Laser.power = value

    def setRFWavelength(self, channel: int, value: int):
        self.__RF.set_wavelength_by_channel(channel, value)

    def getRFWavelength(self, channel: int):
        return self.__RF.get_wavelength_by_channel(channel)

    def setRFAmplitude(self, channel: int, value: int):
        self.__RF.set_amplitude_by_channel(channel, value)

    def getRFAmplitude(self, channel: int):
        return self.__RF.get_amplitude_by_channel(channel)

    def setRFModulation(self, channel: int, value: int):
        self.__RF.set_modulation_by_channel(channel, value)

    def getRFModulation(self, channel: int):
        return self.__RF.get_modulation_by_channel(channel)

    def getRFPower(self):
        return self.__RF.rf_power

    def setRFPower(self, value: bool):
        self.__RF.rf_power = value


class gainDevice(Observable.Observable):

    def __init__(self):
        self.property_changed_event = Event.Event()
        self.free_event = Event.Event()
        self.communicating_event = Event.Event()

        self.call_monitor = Event.Event()
        self.call_data = Event.Event()
        self.append_monitor_data = Event.Event()
        self.append_data = Event.Event()
        self.end_data_monitor = Event.Event()
        self.end_data = Event.Event()

        self.__lastWav = -1 #Used to control the start wav that calls twice in the GUI
        self.__finish_wav = 595.0
        self.__step_wav = 1.0
        self.__avg = 10
        self.__power = 0.
        self.__powermeter_avg = 10
        self.__acq_number = 0

        self.__camera = None
        self.__data = None

        self.__thread = None
        self.__status = True #we start it true because before init everything must be blocked. We free after a succesfull init
        self.__abort_force = False

        self.__Laser = None
        self.__PM = None
        self.__camera = None
        self.__DEBUG = False

        #Control routine
        self.__controlRout = ctrlRout.controlRoutine(self.power_callback)

        #Initial status of the Microscope
        self.__defocus_check = False
        main_controller = Registry.get_component("stem_controller")
        ok, value = main_controller.TryGetVal("C10")
        if ok:
            self.__defocus = value

    def power_callback(self):
        pass
        #self.property_changed_event.fire("power_f")

    def server_instrument_ping(self):
        self.__Laser.ping()

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

        #self.__Laser = LaserWrapper('EthernetConnection1')
        self.__Laser = LaserWrapper('COM5')
        self.__Laser.ping_all()
        #self.__PM = power.TLPowerMeter('USB0::0x1313::0x8072::1908893::INSTR')
        self.__PM = power.TLPowerMeter('USB0::0x1313::0x8072::1907040::INSTR')

        self.upt()
        self.run_status_f = False
        return True

    def hard_reset(self):
        self.__PM.pw_reset('0')

    def upt(self):
        self.property_changed_event.fire("start_wav_f")
        self.property_changed_event.fire("bandwidth_wav_f")
        self.property_changed_event.fire("emission_f")
        self.property_changed_event.fire("delay_f")
        self.property_changed_event.fire("pts_f")
        self.property_changed_event.fire("tpts_f")
        self.property_changed_event.fire("power_f")
        self.property_changed_event.fire("laser_intensity_f")

        self.property_changed_event.fire("rf_power_f")
        self.property_changed_event.fire("wav0_f")
        self.property_changed_event.fire("amp0_f")
        self.property_changed_event.fire("wav1_f")
        self.property_changed_event.fire("amp1_f")
        self.property_changed_event.fire("wav2_f")
        self.property_changed_event.fire("amp2_f")
        self.property_changed_event.fire("wav3_f")
        self.property_changed_event.fire("amp3_f")
        self.property_changed_event.fire("wav4_f")
        self.property_changed_event.fire("amp4_f")
        self.property_changed_event.fire("wav5_f")
        self.property_changed_event.fire("amp5_f")
        self.property_changed_event.fire("wav6_f")
        self.property_changed_event.fire("amp6_f")
        self.property_changed_event.fire("wav7_f")
        self.property_changed_event.fire("amp7_f")

        if not self.__status:
            self.free_event.fire("all")

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

    def acqThread(self):
        self.run_status_f = True
        self.__abort_force = False

        # Laser thread begins
        p = "acquistion_mode" in self.__camera.get_current_frame_parameters().as_dict()
        q = self.__camera.get_current_frame_parameters().as_dict()['acquisition_mode'] == 'Focus' if p else True
        if self.__Laser.check() and self.__finish_wav > self.__lastWav and q:
            self.__acq_number += 1
            self.__camera.start_playing()
            self.__controlRout.pw_control_thread_on(self.__powermeter_avg * 0.003 * 4.0)
            last_cam_acq = self.__camera.grab_next_to_finish()[0]  # get camera then check laser.

            self.call_data.fire(self.__acq_number, self.pts_f + 1, self.avg_f, self.__lastWav, self.__finish_wav,
                                self.__step_wav, last_cam_acq, ctrl=0,
                                delay=self.delay_f, width=0, diode=0,
                                transmission=0,
                                camera=last_cam_acq.metadata)
        else:
            logging.info(
                "***LASER***: Last thread was not done || start and current wavelength differs || end wav < start wav || Not Focus mode.")
            self.run_status_f = False  # acquisition is over
            return

        i = 0  # e-point counter
        i_max = self.pts_f
        j = 0  # each frame inside an specific e-point
        j_max = self.__avg  # dont put directly self.__avg because it will keep refreshing UI
        self.emission_f = True

        while i < i_max and not self.__abort_force:  # i means our laser WL's
            while j < j_max and not self.__abort_force:  # j is our averages
                last_cam_acq = self.__camera.grab_next_to_finish()[0]  # get camera then check laser.
                self.append_data.fire(self.__power, i, j, last_cam_acq, j==j_max-1 and i%2==0)
                j += 1
            j = 0
            i += 1
            while not self.__Laser.check_status() and not self.__abort_force:# check if laser changes have finished and thread step is over
                time.sleep(0.05)
            logging.info("***LASER***: Moving to next wavelength...")
            self.start_wav_f += self.step_wav_f

        logging.info("***LASER***: Finishing laser measurement. Acquiring conventional EELS for reference.")
        self.emission_f = False
        if self.__controlRout.pw_control_thread_check():
            self.__controlRout.pw_control_thread_off()

        while j < j_max and not self.__abort_force:
            last_cam_acq = self.__camera.grab_next_to_finish()[0]
            self.append_data.fire(self.__power, i, j, last_cam_acq, j==j_max-1)
            j += 1

        self.end_data.fire()
        self.run_status_f = False  # acquisition is over


    @property
    def start_wav_f(self) -> float:
        try:
            return self.__Laser.getWL()
        except AttributeError:
            return 999

    @start_wav_f.setter
    def start_wav_f(self, value: str) -> None:
        if self.__lastWav != float(value):
            self.__lastWav = float(value)
            self.__Laser.setWL(float(value))
            self.property_changed_event.fire("start_wav_f")
            if not self.__status:
                self.property_changed_event.fire("pts_f")
                self.property_changed_event.fire("tpts_f")
                self.free_event.fire("all")


    @property
    def finish_wav_f(self) -> float:
        return self.__finish_wav

    @finish_wav_f.setter
    def finish_wav_f(self, value: str) -> None:
        self.__finish_wav = float(value)
        self.property_changed_event.fire("pts_f")
        self.property_changed_event.fire("tpts_f")
        self.free_event.fire("all")

    @property
    def bandwidth_wav_f(self) -> float:
        try:
            return self.__Laser.getBandwidth()
        except AttributeError:
            return 'None'

    @bandwidth_wav_f.setter
    def bandwidth_wav_f(self, value: float) -> None:
        self.__Laser.setBandwidth(float(value))
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
    def laser_intensity_f(self) -> float:
        try:
            return self.__Laser.getPower()
        except AttributeError:
            return 'None'

    @laser_intensity_f.setter
    def laser_intensity_f(self, value: float) -> None:
        self.__Laser.setPower(float(value))

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
        return int(int(self.__avg) * int(self.pts_f))

    @property
    def pts_f(self) -> int:
        return int((float(self.__finish_wav) - float(self.__lastWav)) / float(self.__step_wav) + 1)

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
            self.__power = self.__PM.pw_read(self.__lastWav)
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
    def emission_f(self):
        try:
            return self.__Laser.getEmission()
        except AttributeError:
            return False

    @emission_f.setter
    def emission_f(self, value):
        self.__Laser.setEmission(value)
        time.sleep(1.0) #Emission takes time to be accounted
        self.property_changed_event.fire('emission_f')
        if not self.__status:
            self.free_event.fire('all')

    @property
    def delay_f(self):
        try:
            return self.__Laser.getDelay()
        except AttributeError:
            return 'None'

    @delay_f.setter
    def delay_f(self, value):
        self.__Laser.setDelay(value)

    @property
    def powermeter_avg_f(self):
        return self.__powermeter_avg

    @powermeter_avg_f.setter
    def powermeter_avg_f(self, value):
        self.__powermeter_avg = int(value)
        self.__PM.pw_set_avg(self.__powermeter_avg, '0')

    #RF Driver values
    @property
    def rf_power_f(self):
        try:
            return self.__Laser.getRFPower()
        except AttributeError:
            return False

    @rf_power_f.setter
    def rf_power_f(self, value):
        self.__Laser.setRFPower(value)
        time.sleep(1.0) #Emission takes time to be accounted
        self.property_changed_event.fire('rf_power_f')
        if not self.__status:
            self.free_event.fire('all')

    @property
    def wav0_f(self) -> float:
        try:
            return self.__Laser.getRFWavelength(0)
        except AttributeError:
            return 'None'

    @wav0_f.setter
    def wav0_f(self, value: float) -> None:
        current_wav = self.wav0_f
        if current_wav != float(value):
            self.__Laser.setRFWavelength(0, float(value))
            if not self.__status:
                self.free_event.fire('all')

    @property
    def wav1_f(self) -> float:
        try:
            return self.__Laser.getRFWavelength(1)
        except AttributeError:
            return 'None'

    @wav1_f.setter
    def wav1_f(self, value: float) -> None:
        current_wav = self.wav1_f
        if current_wav != float(value):
            self.__Laser.setRFWavelength(1, float(value))
            if not self.__status:
                self.free_event.fire('all')

    @property
    def wav2_f(self) -> float:
        try:
            return self.__Laser.getRFWavelength(2)
        except AttributeError:
            return 'None'

    @wav2_f.setter
    def wav2_f(self, value: float) -> None:
        current_wav = self.wav2_f
        if current_wav != float(value):
            self.__Laser.setRFWavelength(2, float(value))
            if not self.__status:
                self.free_event.fire('all')

    @property
    def wav3_f(self) -> float:
        try:
            return self.__Laser.getRFWavelength(3)
        except AttributeError:
            return 'None'

    @wav3_f.setter
    def wav3_f(self, value: float) -> None:
        current_wav = self.wav3_f
        if current_wav != float(value):
            self.__Laser.setRFWavelength(3, float(value))
            if not self.__status:
                self.free_event.fire('all')

    @property
    def wav4_f(self) -> float:
        try:
            return self.__Laser.getRFWavelength(4)
        except AttributeError:
            return 'None'

    @wav4_f.setter
    def wav4_f(self, value: float) -> None:
        current_wav = self.wav4_f
        if current_wav != float(value):
            self.__Laser.setRFWavelength(4, float(value))
            if not self.__status:
                self.free_event.fire('all')

    @property
    def wav5_f(self) -> float:
        try:
            return self.__Laser.getRFWavelength(5)
        except AttributeError:
            return 'None'

    @wav5_f.setter
    def wav5_f(self, value: float) -> None:
        current_wav = self.wav5_f
        if current_wav != float(value):
            self.__Laser.setRFWavelength(5, float(value))
            if not self.__status:
                self.free_event.fire('all')

    @property
    def wav6_f(self) -> float:
        try:
            return self.__Laser.getRFWavelength(6)
        except AttributeError:
            return 'None'

    @wav6_f.setter
    def wav6_f(self, value: float) -> None:
        current_wav = self.wav6_f
        if current_wav != float(value):
            self.__Laser.setRFWavelength(6, float(value))
            if not self.__status:
                self.free_event.fire('all')

    @property
    def wav7_f(self) -> float:
        try:
            return self.__Laser.getRFWavelength(7)
        except AttributeError:
            return 'None'

    @wav7_f.setter
    def wav7_f(self, value: float) -> None:
        current_wav = self.wav7_f
        if current_wav != float(value):
            self.__Laser.setRFWavelength(7, float(value))
            if not self.__status:
                self.free_event.fire('all')

    @property
    def amp0_f(self) -> float:
        try:
            return self.__Laser.getRFAmplitude(0)
        except AttributeError:
            return 'None'

    @amp0_f.setter
    def amp0_f(self, value: float) -> None:
        self.__Laser.setRFAmplitude(0, float(value))
        self.free_event.fire("all")

    @property
    def amp1_f(self) -> float:
        try:
            return self.__Laser.getRFAmplitude(1)
        except AttributeError:
            return 'None'

    @amp1_f.setter
    def amp1_f(self, value: float) -> None:
        self.__Laser.setRFAmplitude(1, float(value))
        self.free_event.fire("all")

    @property
    def amp2_f(self) -> float:
        try:
            return self.__Laser.getRFAmplitude(2)
        except AttributeError:
            return 'None'

    @amp2_f.setter
    def amp2_f(self, value: float) -> None:
        self.__Laser.setRFAmplitude(2, float(value))
        self.free_event.fire("all")

    @property
    def amp3_f(self) -> float:
        try:
            return self.__Laser.getRFAmplitude(3)
        except AttributeError:
            return 'None'

    @amp3_f.setter
    def amp3_f(self, value: float) -> None:
        self.__Laser.setRFAmplitude(3, float(value))
        self.free_event.fire("all")

    @property
    def amp4_f(self) -> float:
        try:
            return self.__Laser.getRFAmplitude(4)
        except AttributeError:
            return 'None'

    @amp4_f.setter
    def amp4_f(self, value: float) -> None:
        self.__Laser.setRFAmplitude(4, float(value))
        self.free_event.fire("all")

    @property
    def amp5_f(self) -> float:
        try:
            return self.__Laser.getRFAmplitude(5)
        except AttributeError:
            return 'None'

    @amp5_f.setter
    def amp5_f(self, value: float) -> None:
        self.__Laser.setRFAmplitude(5, float(value))
        self.free_event.fire("all")

    @property
    def amp6_f(self) -> float:
        try:
            return self.__Laser.getRFAmplitude(6)
        except AttributeError:
            return 'None'

    @amp6_f.setter
    def amp6_f(self, value: float) -> None:
        self.__Laser.setRFAmplitude(6, float(value))
        self.free_event.fire("all")

    @property
    def amp7_f(self) -> float:
        try:
            return self.__Laser.getRFAmplitude(7)
        except AttributeError:
            return 'None'

    @amp7_f.setter
    def amp7_f(self, value: float) -> None:
        self.__Laser.setRFAmplitude(7, float(value))
        self.free_event.fire("all")
