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
        self.__start_wav = 580
        self.__finish_wav = 600

    def init(self):
        logging.info("init...")
   
    def upt(self):
        logging.info("UPT BUTTON")
        logging.info(self.__start_wav)
        
    def acq(self):
        logging.info("ACQ BUTTON")
        
    def gen(self):
        logging.info("GENERATE BUTTON")
    
    @property
    def start_wav(self) -> float:
        return self.__start_wav

    @start_wav.setter
    def start_wav(self, value: float) -> None:
        self.__start_wav = value
