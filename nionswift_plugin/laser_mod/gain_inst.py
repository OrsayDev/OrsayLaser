"""
A spectrometer device that can be bound to the UI trhough SpectroPanel
Requires a spectro low_level object
two are given in the plug_in, one is bound to a dll, the other ("virtual") essentially gives a testing object
"""
DEBUG=True
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



class gainDevice(Observable.Observable):

    def __init__(self):
        self.property_changed_event = Event.Event()
        self.communicating_event = Event.Event()
        #self.property_changed_event_listener = self.property_changed_event.listen(self.computeCalibration)
        self.busy_event=Event.Event()
        
        self.__start_wav = 580.
        self.__finish_wav = 600.
        self.__step_wav = 0.1
        self.__pts=int((self.__finish_wav-self.__start_wav)/self.__step_wav+1)
        self.__avg = 1
        self.__tpts = int(self.__avg * self.__pts)
        self.__dwell = 100

        self.__camera = HardwareSource.HardwareSourceManager().hardware_sources[1]
        self.__frame_parameters=self.__camera.get_current_frame_parameters()
        self.__frame_parameters["integration_count"]=int(self.__avg)
        self.__frame_parameters["exposure_ms"]=int(self.__dwell)

        self.__thread = None



    def init(self):
        logging.info("init...")
   
    def upt(self):
        self.__camera.set_current_frame_parameters(self.__frame_parameters)
        self.property_changed_event.fire("pts_f")
        self.property_changed_event.fire("tpts_f")
        self.property_changed_event.fire("thAcq_status")
        
    def acq(self):
        self.__thread = threading.Thread(target=self.acqThread)
        self.__thread.start()
        self.upt()
        
    def gen(self):
        logging.info("Generate button")

    def acqThread(self):
        for i in range(10):
            self.__camera.grab_next_to_start()[0]
        self.__camera.stop_playing()




    @property
    def start_wav_f(self) -> float:
        return self.__start_wav

    @start_wav_f.setter
    def start_wav_f(self, value: float) -> None:
        self.__start_wav = value
    
    @property
    def finish_wav_f(self) -> float:
        return self.__finish_wav

    @finish_wav_f.setter
    def finish_wav_f(self, value: float) -> None:
        self.__finish_wav = value
    
    @property
    def step_wav_f(self) -> float:
        return self.__step_wav

    @step_wav_f.setter
    def step_wav_f(self, value: float) -> None:
        self.__step_wav = value
    
    @property
    def avg_f(self) -> int:
        return self.__avg

    @avg_f.setter
    def avg_f(self, value: int) -> None:
        self.__avg = value
        logging.info("Average number updated")
        self.__frame_parameters["integration_count"]=int(self.__avg)

    @property
    def dwell_f(self) -> int:
        return self.__dwell

    @dwell_f.setter
    def dwell_f(self, value: int) -> None:
        self.__dwell = value
        logging.info("Exposure time updated")
        self.__frame_parameters["exposure_ms"]=int(self.__dwell)

    @property
    def tpts_f(self) -> int:
        self.__tpts = int(int(self.__avg) * int(self.__pts))
        return self.__tpts
    
    @property
    def pts_f(self) -> float:
        self.__pts=int((float(self.__finish_wav)-float(self.__start_wav))/float(self.__step_wav)+1)
        return self.__pts
    
    @property
    def thAcq_status(self):
        if (self.__thread == None):
            return "False"
        else:
            return str(self.__thread.is_alive())
