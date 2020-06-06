# standard libraries
import math
import numpy
import os
import random
import scipy.ndimage.interpolation
import scipy.stats
import threading
import typing
import time
from nion.data import Calibration
from nion.data import DataAndMetadata
import asyncio
#from pydevd import settrace
import logging


from nion.utils import Registry
from nion.utils import Event
from nion.utils import Geometry
from nion.utils import Model
from nion.utils import Observable
from nion.swift.model import HardwareSource
from nion.swift.model import ImportExportManager
from nion.swift.model import DataItem


import logging
import time

from . import gain_data as gdata

DEBUG_pw = 1
DEBUG_laser = 0

if DEBUG_pw:
    from . import power_vi as power
else:
    from . import power as power

if DEBUG_laser:
    from . import laser_vi as laser
else:
    from . import laser as laser


class gainDevice(Observable.Observable):

    def __init__(self):
        self.property_changed_event = Event.Event()
        self.property_changed_power_event = Event.Event()
        self.communicating_event = Event.Event()
        #self.property_changed_event_listener = self.property_changed_event.listen(self.computeCalibration)
        self.busy_event=Event.Event()
        
        self.__start_wav = 575.0
        self.__finish_wav = 600.0
        self.__step_wav = 5.0
        self.__cur_wav = self.__start_wav
        self.__pts=int((self.__finish_wav-self.__start_wav)/self.__step_wav+1)
        self.__avg = 10
        self.__tpts = int(self.__avg * self.__pts)
        self.__dwell = 100
        self.__power=numpy.random.randn(1)[0]

        self.__camera = HardwareSource.HardwareSourceManager().hardware_sources[1]
        self.__frame_parameters=self.__camera.get_current_frame_parameters()
        self.__frame_parameters["exposure_ms"]=float(self.__dwell)
        self.__camera.set_current_frame_parameters(self.__frame_parameters)
        self.__data=None

        self.__thread = None
        self.__status = False
        self.__stored = False
        self.__abort_force = False

        self.__sendmessage = laser.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__laser = laser.SirahCredoLaser(self.__sendmessage)

        self.__power_sendmessage = power.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__pwmeter = power.TLPowerMeter(self.__power_sendmessage)
        #self.__pwmeter.pw_random_periodic() #THIS IS RESPONSIBLE FOR A MESSAGE ERROR AT THE END

        self.__data_sendmessage = gdata.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__gdata = gdata.gainData(self.__data_sendmessage)

    def init(self):
        logging.info("init...")
   
    def upt(self):
        self.property_changed_event.fire("pts_f")
        self.property_changed_event.fire("tpts_f")
        self.property_changed_event.fire("cur_wav_f")
        self.property_changed_event.fire("run_status")
        self.property_changed_event.fire("stored_status")
        self.property_changed_event.fire("power_f")
        if (self.__status):
            self.busy_event.fire("all")

    def acq(self):
        self.__camera.set_current_frame_parameters(self.__frame_parameters)
        self.__thread = threading.Thread(target=self.acqThread)
        self.__thread.start()
        
    def gen(self):
        if self.__stored:
            self.__stored = False
            intensity_calibration = self.__data[0][0].intensity_calibration # we first pick up this parameter here and modify later on
            dimensional_calibrations = self.__data[0][0].dimensional_calibrations
            sum_data, max_index = self.__gdata.send_raw_MetaData(self.__data) #this aligned and returns data to be appended in a data_item
            data_item = DataItem.DataItem(large_format=True) #Creating Data Item
            data_item.set_data(sum_data) #Setting data
            int_cal, dim_cal = self.__gdata.data_item_calibration(intensity_calibration, dimensional_calibrations, self.__start_wav, self.__step_wav, 0.013, max_index) #Modifying and setting int/dimensional calib. Check gain_data.py for info on how this is done
            data_item.set_intensity_calibration(int_cal)
            data_item.set_dimensional_calibrations(dim_cal)

            logging.info("Generating our data..")
            self.property_changed_event.fire("stored_status")

            #send data_item back to gain_panel, the one who has control over document_controller
            return data_item
        else:
            return None

    def abt(self):
        logging.info("Abort scanning. Going back to origin...")
        self.__abort_force = True
        self.__laser.abort_control() #abort laser thread as well.

    def acqThread(self):
        self.__status = True
        self.upt()

        self.__laser.setWL(self.__start_wav, self.__cur_wav)
        self.__abort_force = False
        
        #Laser thread begins
        if self.__laser.set_scan_thread_check():
            self.__laser.set_scan(self.__cur_wav, self.__step_wav, self.__pts)
        else:
            logging.info("Last thread was not done. Some error happened")
        self.__data = []
        i=0 #e-point counter
        i_max=self.__pts
        j=0 #each frame inside an specific e-point
        j_max=self.__avg #dont put directly self.__avg because it will keep refreshing UI
        
        while( i<i_max and not self.__abort_force): #i means our laser WL's
            self.__data.append([])
            while( j<j_max  and not self.__abort_force): #j is our averages
                self.__data[i].append(self.__camera.grab_next_to_start()[0])
                j+=1
                #logging.info(self.__laser.set_scan_thread_hardware_cur_wl()) #this tell us real laser WL. When updated it?
            j=0
            i+=1
            if (self.__laser.set_scan_thread_hardware_status()==2): #check if laser changes have finished and thread step is over
                self.__laser.set_scan_thread_release() #if yes, you can advance
            else:
                self.abt() #execute our abort routine (laser and acq thread)
            self.upt() #updating mainly current wavelength
    
        time.sleep(1) #wait 1 second until all hardward tasks are done after a release fail
        if self.__laser.set_scan_thread_locked(): #releasing everything if locked
            self.__laser.set_scan_thread_release()
        self.__camera.stop_playing() #stop camera
        self.__laser.setWL(self.__start_wav, self.__cur_wav) #puts laser back to start wavelength
        self.__stored = True and not self.__abort_force #Stored is true conditioned that loop was not aborted
        self.__status = False #acquistion is over
        logging.info("Acquistion is over") 
        self.upt() #here you going to update panel only until setWL is over. This is because this specific thread has a join() at the end.

    #x: laser; xx: power meter; xxx: data analyses
    def sendMessageFactory(self):
        def sendMessage(message):
            if message==1:
                logging.info("***LASER***: start WL is current WL")
                self.upt()
            if message==2:
                logging.info("***LASER***: Current WL updated")
                self.__cur_wav = self.__start_wav
                self.__pwmeter.pw_set_WL(self.__cur_wav)
                self.upt()
            if message==3:
                logging.info("***LASER***: Laser Motor is moving. You can not change wavelength while last one is still moving. Please increase camera dwell time or # of averages in order to give time to our slow hardware.")
            if message==5:
                logging.info("***LASER***: Could not write in laser serial port. Check port.")
            if message==6:
                logging.info("***LASER***: Could not write/read in laser serial port. Check port.")
            if message==7:
                logging.info("***LASER***: Could not open serial port. Check if connected and port.")
            if message==100:
                self.__power = self.__pwmeter.pw_read()
                self.upt()
        return sendMessage

    @property
    def start_wav_f(self) -> float:
        return self.__start_wav

    @start_wav_f.setter
    def start_wav_f(self, value: float) -> None:
        self.busy_event.fire("all")
        self.__start_wav = float(value)
        self.__laser.setWL(self.__start_wav, self.__cur_wav)
    
    @property
    def finish_wav_f(self) -> float:
        return self.__finish_wav

    @finish_wav_f.setter
    def finish_wav_f(self, value: float) -> None:
        self.__finish_wav = float(value)
        self.property_changed_event.fire("pts_f") 
        self.property_changed_event.fire("tpts_f") 
    
    @property
    def step_wav_f(self) -> float:
        return self.__step_wav

    @step_wav_f.setter
    def step_wav_f(self, value: float) -> None:
        self.__step_wav = float(value)
        self.property_changed_event.fire("pts_f")
        self.property_changed_event.fire("tpts_f")
    
    @property
    def avg_f(self) -> int:
        return self.__avg

    @avg_f.setter
    def avg_f(self, value: int) -> None:
        self.__avg = int(value)
        self.property_changed_event.fire("tpts_f")

    @property
    def dwell_f(self) -> int:
        return self.__dwell

    @dwell_f.setter
    def dwell_f(self, value: float) -> None:
        self.__dwell = float(value)
        self.__frame_parameters["exposure_ms"]=self.__dwell

    @property
    def tpts_f(self) -> int:
        self.__tpts = int(int(self.__avg) * int(self.__pts))
        return self.__tpts
    
    @property
    def pts_f(self) -> float:
        self.__pts=int((float(self.__finish_wav)-float(self.__start_wav))/float(self.__step_wav)+1)
        return self.__pts
    
    @property
    def cur_wav_f(self) -> float:
        self.__cur_wav = self.__laser.get_hardware_wl()[0]
        if (self.__cur_wav==None):
            return 'Error'
        else:
            self.__pwmeter.pw_set_WL(self.__cur_wav)
            return format(self.__cur_wav, '.3f')
    
    @property
    def run_status(self):
        return str(self.__status)
    
    @property
    def stored_status(self):
        return str(self.__stored)
    
    @property
    def power_f(self):
        return round(self.__power, 3)
