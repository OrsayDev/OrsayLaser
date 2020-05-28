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


import logging
import time

from . import laser_vi as laser



class gainDevice(Observable.Observable):

    def __init__(self):
        self.property_changed_event = Event.Event()
        self.communicating_event = Event.Event()
        #self.property_changed_event_listener = self.property_changed_event.listen(self.computeCalibration)
        self.busy_event=Event.Event()
        
        self.__start_wav = 580.
        self.__finish_wav = 600.
        self.__step_wav = 1
        self.__cur_wav = self.__start_wav
        self.__pts=int((self.__finish_wav-self.__start_wav)/self.__step_wav)
        self.__avg = 1
        self.__tpts = int(self.__avg * self.__pts)
        self.__dwell = 100

        self.__camera = HardwareSource.HardwareSourceManager().hardware_sources[1]
        self.__frame_parameters=self.__camera.get_current_frame_parameters()
        self.__frame_parameters["integration_count"]=int(self.__avg)
        self.__frame_parameters["exposure_ms"]=int(self.__dwell)


        self.__thread = None
        self.__status = False
        self.__stored = False

        self.__sendmessage = laser.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__laser = laser.SirahCredoLaser(self.__sendmessage)


    def init(self):
        logging.info("init...")
   
    def upt(self):
        self.__camera.set_current_frame_parameters(self.__frame_parameters)

        self.property_changed_event.fire("pts_f") #i dont know what makes pts_f be executed here. I thought this func was simple based on able/disable of my widgets. See async def on
        self.property_changed_event.fire("tpts_f")
        self.property_changed_event.fire("cur_wav_f")
        if (self.__status): #if its running you disable UI after updating our variables
            self.busy_event.fire("all")

        
    def acq(self):
        self.upt()
        self.__thread = threading.Thread(target=self.acqThread)
        self.__thread.start()
        
    def gen(self):
        self.__stored = False
        self.property_changed_event.fire("stored_status")

    def abt(self):
        #still thinking how to implement an functional Abort button
        self.__abort_force = True
        self.property_changed_event.fire("all")


    def acqThread(self):
        self.__cur_wav = self.__start_wav
        self.__abort_force = False
        data = []
        self.__status = True #started
        self.property_changed_event.fire("run_status")
        self.busy_event.fire("all")
        self.__laser.set_scan(self.__cur_wav, self.__step_wav, self.__pts) #THIS IS A THREAD. Start and bye

        i=0
        while(self.__cur_wav != self.__finish_wav and not self.__abort_force):
            self.upt()
            data.append([])
            data[i] = self.__camera.grab_next_to_start()[0]
            i+=1

        #for i in range(self.__pts):
        #    data.append([])
        #    self.upt()
        #    data[i] = self.__camera.grab_next_to_start()[0]
        self.__camera.stop_playing()
        logging.info(len(data))
        self.__status = False #its over
        self.__stored = True
        self.property_changed_event.fire("run_status")
        self.property_changed_event.fire("stored_status")

    def sendMessageFactory(self):
        def sendMessage(message):
            if message==1:
                logging.info("start WL is current WL")
                self.property_changed_event.fire("start_wav_f")
            if message==2:
                logging.info("WL updated")
                self.__cur_wav = self.__start_wav
                self.property_changed_event.fire("pts_f")
                self.property_changed_event.fire("tpts_f")
                self.property_changed_event.fire("cur_wav_f")
            if message==3:
                #do not update property because this should be called together with self.upt()
                self.__cur_wav = float(self.__cur_wav) + float(self.__step_wav)
        return sendMessage

    @property
    def start_wav_f(self) -> float:
        return self.__start_wav

    @start_wav_f.setter
    def start_wav_f(self, value: float) -> None:
        self.busy_event.fire("all")
        self.__laser.setWL(value, self.__cur_wav)
        self.__start_wav = float(value)
    
    @property
    def finish_wav_f(self) -> float:
        return self.__finish_wav

    @finish_wav_f.setter
    def finish_wav_f(self, value: float) -> None:
        self.__finish_wav = value
        self.property_changed_event.fire("pts_f") 
        self.property_changed_event.fire("tpts_f") 
    
    @property
    def step_wav_f(self) -> float:
        return self.__step_wav

    @step_wav_f.setter
    def step_wav_f(self, value: float) -> None:
        self.__step_wav = value
        self.property_changed_event.fire("pts_f") #yves: not sure if this is the best way to do. Note i am calling a property inside another property. It works, however
        self.property_changed_event.fire("tpts_f")
    
    @property
    def cur_wav_f(self) -> float:
        return format(self.__cur_wav, '.3f')
    
    @property
    def avg_f(self) -> int:
        return self.__avg

    @avg_f.setter
    def avg_f(self, value: int) -> None:
        self.__avg = value
        self.__frame_parameters["integration_count"]=int(self.__avg)
        self.property_changed_event.fire("tpts_f")

    @property
    def dwell_f(self) -> int:
        return self.__dwell

    @dwell_f.setter
    def dwell_f(self, value: int) -> None:
        self.__dwell = value
        self.__frame_parameters["exposure_ms"]=int(self.__dwell)

    @property
    def tpts_f(self) -> int:
        self.__tpts = int(int(self.__avg) * int(self.__pts))
        return self.__tpts
    
    @property
    def pts_f(self) -> float:
        self.__pts=int((float(self.__finish_wav)-float(self.__start_wav))/float(self.__step_wav))
        return self.__pts
    
    @property
    def run_status(self):
        if (self.__status == False):
            return "False"
        if (self.__status == True):
            #return str(self.__thread.is_alive())
            return "True"
    
    @property
    def stored_status(self):
        return str(self.__stored)
