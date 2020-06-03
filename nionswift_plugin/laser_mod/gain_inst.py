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


import logging
import time

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
        self.__step_wav = 1.0
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

        self.__thread = None
        self.__status = False
        self.__stored = False
        self.__abort_force = False

        self.__sendmessage = laser.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__laser = laser.SirahCredoLaser(self.__sendmessage)

        self.__power_sendmessage = power.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__pwmeter = power.TLPowerMeter(self.__power_sendmessage)
        self.__pwmeter.pw_random_periodic() #THIS IS RESPONSIBLE FOR A MESSAGE ERROR AT THE END

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
        self.__stored = False
        self.displayData()
        self.property_changed_event.fire("stored_status")

    def abt(self):
        logging.info("Abort scanning. Going back to origin...")
        self.__abort_force = True
        self.__laser.abort_control()

    def acqThread(self):
        self.__status = True #started
        self.upt()

        self.__laser.setWL(self.__start_wav, self.__cur_wav)
        self.__abort_force = False
        self.__laser.set_scan(self.__cur_wav, self.__step_wav, self.__pts) #THIS IS A THREAD. Start and bye
        data = []
        i=0
        while(not self.__laser.setWL_thread_check() and not self.__abort_force):
            data.append([])
            while(  ( not self.__laser.setWL_thread_locked() and not self.__laser.setWL_thread_check())    and not self.__abort_force):
                data[i].append(self.__camera.grab_next_to_finish()[0])
            i+=1
            if (self.__laser.setWL_thread_locked()):
                self.__laser.setWL_thread_release() #if you dont release thread does not advance. 
                self.__cur_wav += self.__step_wav
                self.__pwmeter.pw_set_WL(self.__cur_wav)
            self.upt()
        self.__camera.stop_playing()
        self.__laser.setWL(self.__start_wav, self.__cur_wav)
        self.__stored = True and not self.__abort_force
        self.__status = False #its over

        self.upt()

    def displayData(self):
        #datax = numpy.random.randn(100, 1024)
        #data_element["data"]=datax
        #data_element["title"]="olaolaola"
        #sum_data_item = ImportExportManager.create_data_item_from_data_element(data_element)
        #logging.info(document_controller)
        logging.info("plotting...")

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
            #if message==3:
            #    logging.info("Step over")
            #if message==4:
                #logging.info("msg 4")
            if message==100:
                #self.__power = numpy.random.randn(1)[0]
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
