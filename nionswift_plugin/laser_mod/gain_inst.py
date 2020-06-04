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
from . import laser_vi as laser

DEBUG_pw = 1

if DEBUG_pw:
    from . import power_vi as power
else:
    from . import power as power



class gainDevice(Observable.Observable):

    def __init__(self):
        self.property_changed_event = Event.Event()
        self.property_changed_power_event = Event.Event()
        self.communicating_event = Event.Event()
        #self.property_changed_event_listener = self.property_changed_event.listen(self.computeCalibration)
        self.busy_event=Event.Event()
        
        self.__start_wav = 580.0
        self.__finish_wav = 600.0
        self.__step_wav = 5.0
        self.__cur_wav = self.__start_wav
        self.__pts=int((self.__finish_wav-self.__start_wav)/self.__step_wav+1)
        self.__avg = 1
        self.__tpts = int(self.__avg * self.__pts)
        self.__dwell = 100
        self.__power=numpy.random.randn(1)[0]

        self.__camera = HardwareSource.HardwareSourceManager().hardware_sources[1]
        self.__frame_parameters=self.__camera.get_current_frame_parameters()
        self.__frame_parameters["integration_count"]=int(self.__avg)
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
            #As we are going to create a DataItem from scrach, we first pick up this parameter here. We will modify later on
            intensity_calibration = self.__data[0][0].intensity_calibration
            dimensional_calibrations = self.__data[0][0].dimensional_calibrations
            # This aligns and returns the data that will be appended in the data_item
            sum_data, max_index = self.__gdata.send_raw_MetaData(self.__data) #this aligned and returns data to be appended in a data_item
            #Creating Data Item
            data_item = DataItem.DataItem(large_format=True)
            #Setting data
            data_item.set_data(sum_data)
            #Modifying and setting intensity calibration and dimensional calibration. Check gain_data.py for info on how this is done
            int_cal, dim_cal = self.__gdata.data_item_calibration(intensity_calibration, dimensional_calibrations, self.__start_wav, self.__step_wav, 0.013, max_index)
            data_item.set_intensity_calibration(int_cal)
            data_item.set_dimensional_calibrations(dim_cal)

            #send data_item back to gain_panel, the one who has control over document_controller. This allows us to display our acquired data in nionswift panel
            return data_item
        else:
            return None
        self.property_changed_event.fire("stored_status")

    def abt(self):
        logging.info("Abort scanning. Going back to origin...")
        self.__abort_force = True
        self.__laser.abort_control()

    def acqThread(self):
        self.__status = True
        self.upt()

        self.__laser.setWL(self.__start_wav, self.__cur_wav)
        self.__abort_force = False
        #Laser thread begins
        self.__laser.set_scan(self.__cur_wav, self.__step_wav, self.__pts)
        self.__data = []
        i=0
        #first while means that camera is running while laser thread is on and abort is off
        while(not self.__laser.setWL_thread_check() and not self.__abort_force):
            self.__data.append([])
            #Second while means that camera is running and picking the maximum of frames possible given the parameters. This means that if laser is super slow we are still capturing frames. thread_locked() checks if laser step is done. In short, camera is grabbing frames while laser thread is running, abort is False and laser is not locked (moving, for example). Ideally, you should put camera way slower than laser latency so most of the frame comes from a stationary WL. In this case, you will have a single frame for each wavelength. This can largely be improved
            while(  ( not self.__laser.setWL_thread_locked() and not self.__laser.setWL_thread_check())    and not self.__abort_force):
                self.__data[i].append(self.__camera.grab_next_to_start()[0])
            i+=1
            if (self.__laser.setWL_thread_locked()): #check if laser changes have finished and thread step is over
                self.__laser.setWL_thread_release() #if yes, you can advance
                self.__cur_wav += self.__step_wav #update wavelength
                self.__pwmeter.pw_set_WL(self.__cur_wav) #set wavelength on powermeter
            self.upt() #updating mainly current wavelength
        self.__camera.stop_playing() #stop camera
        self.__laser.setWL(self.__start_wav, self.__cur_wav) #puts laser back to start wavelength
        self.__stored = True and not self.__abort_force #Stored is true conditioned that loop was not aborted
        self.__status = False #acquistion is over
        logging.info("Acquistion is over") 


        self.upt() #here you going to update panel only until setWL is over. This is because this specific thread has a join() at the end.

    #this is our callback functions. Messages with 1 digit comes from laser. Messages with 2 digits comes from power meter. Messages with 3 digits comes from data analyses package
    def sendMessageFactory(self):
        def sendMessage(message):
            if message==1:
                logging.info("start WL is current WL")
                self.upt()
            if message==2:
                logging.info("Current WL updated")
                self.__cur_wav = self.__start_wav
                self.__pwmeter.pw_set_WL(self.__cur_wav)
                self.upt()
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
        self.__frame_parameters["integration_count"]=self.__avg
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
        return format(self.__cur_wav, '.3f')
    
    @property
    def run_status(self):
        if (self.__status == False):
            return "False"
        if (self.__status == True):
            return "True"
    
    @property
    def stored_status(self):
        return str(self.__stored)
    
    @property
    def power_f(self):
        return round(self.__power, 3)
