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

    def init(self):
        logging.info("init...")
   
    def upt(self):
        self.property_changed_event.fire("pts_f") ##THIS FUNC CALLS THE ASYNC ONE AT PANEL BUT ULTIMATELY CALLS THE @PROPERTY (get not setter)
        
    def acq(self):
        logging.info("ACQ BUTTON")
        
    def gen(self):
        logging.info("GENERATE BUTTON")

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
    def pts_f(self) -> float:
        logging.info("getting pts...")
        self.__pts=int((float(self.__finish_wav)-float(self.__start_wav))/float(self.__step_wav)+1)
        return self.__pts
    
