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

DEBUG_pw = 0
DEBUG_laser = 0
DEBUG_ps = 0

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


class gainDevice(Observable.Observable):

    def __init__(self):
        self.property_changed_event = Event.Event()
        self.free_event = Event.Event()
        self.communicating_event = Event.Event()
        #self.property_changed_event_listener = self.property_changed_event.listen(self.computeCalibration)
        self.busy_event=Event.Event()
        
        self.__start_wav = 575.0
        self.__finish_wav = 590.0
        self.__step_wav = 1.0
        self.__cur_wav = self.__start_wav
        self.__pts=int((self.__finish_wav-self.__start_wav)/self.__step_wav+1)
        self.__avg = 10
        self.__tpts = int(self.__avg * self.__pts)
        self.__dwell = 10
        self.__power=0.
        self.__diode=0.
        self.__ctrl_cur=False

        self.__camera=None

        for hards in HardwareSource.HardwareSourceManager().hardware_sources: #finding eels camera. If you dont find, use usim eels
            if hasattr(hards, 'hardware_source_id'):
                if hards.hardware_source_id=='orsay_camera_eire':
                    self.__camera=hards

        if self.__camera==None:
            for hards in HardwareSource.HardwareSourceManager().hardware_sources: #finding eels camera. If you dont find, use usim eels
                if hasattr(hards, 'hardware_source_id'):
                    if hards.hardware_source_id=='usim_eels_camera':
                        self.__camera=hards
            

        #self.__camera = HardwareSource.HardwareSourceManager().hardware_sources[1]
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
		
        self.__ps_sendmessage = ps.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__ps = ps.SpectraPhysics(self.__ps_sendmessage)

        self.__data_sendmessage = gdata.SENDMYMESSAGEFUNC(self.sendMessageFactory())
        self.__gdata = gdata.gainData(self.__data_sendmessage)

    def init(self):
        logging.info("init...")

    def sht(self):
        if self.sht_f=='CLOSED':
            self.__ps.comm('SHT:1\n')
        else:
            self.__ps.comm('SHT:0\n')
        self.property_changed_event.fire("sht_f")
        self.free_event.fire("all")

    def diode(self, val):
        if val==True:
            self.__ps.comm('D:1\n')
            time.sleep(3)
        else:
            self.__ps.comm('D:0\n')

        self.property_changed_event.fire('d_f')
        self.free_event.fire("all")

		
    
    def q(self, val):
        if val==True:
            self.__ps.comm('G:1\n')
        else:
            self.__ps.comm('G:0\n')
        self.property_changed_event.fire('q_f')
        self.free_event.fire("all")
    
    def ctrl_cur(self, val):
        self.__ctrl_cur=val
   
    def upt(self):   

        self.property_changed_event.fire("run_status")
        self.property_changed_event.fire("stored_status")
        self.property_changed_event.fire("power_f")
        self.property_changed_event.fire("cur_wav_f")
        if not self.__status:
            self.property_changed_event.fire("pts_f")
            self.property_changed_event.fire("tpts_f") 
            self.property_changed_event.fire('d_f')
            time.sleep(0.005)
            self.property_changed_event.fire('q_f')
            time.sleep(0.005)
            self.property_changed_event.fire("cur_d1_f")
            time.sleep(0.005)
            self.property_changed_event.fire("cur_d2_f")
            time.sleep(0.005)
            self.property_changed_event.fire("sht_f")
            self.free_event.fire("all")		

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

            data_item2 = DataItem.DataItem()
            wl_data, pw_data, di_data = self.__gdata.send_info_data(self.__infodata)
            data_item2.set_data(wl_data)
            
            data_item3 = DataItem.DataItem()
            data_item3.set_data(pw_data)

            data_item4 = DataItem.DataItem()
            data_item4.set_data(di_data)           

            logging.info("Generating our data..")
            self.property_changed_event.fire("stored_status")
            self.free_event.fire("all")

            #send data_item back to gain_panel, the one who has control over document_controller
            return data_item, data_item2, data_item3, data_item4
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
        if (self.__laser.set_scan_thread_check() and abs(self.__start_wav-self.__cur_wav)<=0.001 and self.__finish_wav>self.__start_wav):
            self.__laser.set_scan(self.__cur_wav, self.__step_wav, self.__pts)
            self.__ps.comm('SHT:1\n')
            self.__ps.pw_control_receive(self.__diode)
            self.__ps.pw_control_thread_on()
            self.__power_ref = self.__power #reference in power
        else:
            logging.info("Last thread was not done || start and current wavelength differs || end wav < start wav")
            self.__abort_force = True
        self.__data = []
        self.__infodata = []
        i=0 #e-point counter
        i_max=self.__pts
        j=0 #each frame inside an specific e-point
        j_max=self.__avg #dont put directly self.__avg because it will keep refreshing UI
        
        while( i<i_max and not self.__abort_force): #i means our laser WL's
            self.__data.append([])
            self.__infodata.append([])
            while( j<j_max  and not self.__abort_force): #j is our averages
                self.__data[i].append(self.__camera.grab_next_to_start()[0])
                if j%1==0:
                    self.upt()
                    self.__infodata[i].append([self.__cur_wav, self.__power, self.__diode])
                j+=1
            j=0
            i+=1
            if (self.__laser.set_scan_thread_hardware_status()==2): #check if laser changes have finished and thread step is over
                self.__laser.set_scan_thread_release() #if yes, you can advance
            else:
                self.abt() #execute our abort routine (laser and acq thread)
           
        if self.__ps.pw_control_thread_check():
            self.__ps.pw_control_thread_off() #turns off our periodic thread. See message 79.
        self.__camera.stop_playing() #stop camera  
        self.__ps.comm('SHT:0\n') #closes shutter  
        while (not self.__laser.set_scan_thread_check()): #thread MUST END for the sake of security. Better to be looped here indefinitely than fuck the hardware
            if self.__laser.set_scan_thread_locked(): #releasing everything if locked
                self.__laser.set_scan_thread_release()
        self.upt()
        self.__laser.setWL(self.__start_wav, self.__cur_wav) #puts laser back to start wavelength
        time.sleep(4.9) #wait laser almost go back to show GUI
        self.__stored = True and not self.__abort_force #Stored is true conditioned that loop was not aborted
        self.__status = False #acquistion is over
        logging.info("Acquistion is over") 
        self.upt() #here you going to update panel only until setWL is over. This is because this specific thread has a join() at the end.

    #0-20: laser; 21-40: power meter; 41-60: data analyses; 61-80: power supply
    def sendMessageFactory(self):
        def sendMessage(message):
            if message==1:
                logging.info("***LASER***: start WL is current WL")
                self.upt()
            if message==2:
                logging.info("***LASER***: Current WL updated")
                self.upt()
            if message==3:
                logging.info("***LASER***: Laser Motor is moving. You can not change wavelength while last one is still moving. Please increase camera dwell time or # of averages in order to give time to our slow hardware.")
            if message==5:
                logging.info("***LASER***: Could not write in laser serial port. Check port.")
            if message==6:
                logging.info("***LASER***: Could not write/read in laser serial port. Check port.")
            if message==7:
                logging.info("***LASER***: Could not open serial port. Check if connected and port.")
            if message==8:
                logging.info('***LASER***: Status was not 02 or 03. Problem receiving bytes from laser hardware.')
            if message==21:
                logging.info('***Power Meter***: Cant write')
            if message==22:
                logging.info('***Power Meter***: Cant READ a new measurement. Fetching last one instead.')
            if message==61:
                logging.info('***LASER PS***: Could not open serial port. Check if connected and port')
            if message==62:
                logging.info('***LASER PS***: Could not query properly')
            if message==63:
                logging.info('***LASER PS***: Could not send command properly')
            if message==79 and self.__ctrl_cur:
                if self.__power < self.__power_ref:
                    self.__diode+=0.05
                if self.__power > self.__power_ref:
                    self.__diode-=0.05
                self.property_changed_event.fire("cur_d1_f")
                self.property_changed_event.fire("cur_d2_f")
                self.__ps.pw_control_receive(self.__diode)
        return sendMessage

    @property
    def start_wav_f(self) -> float:
        return self.__start_wav

    @start_wav_f.setter
    def start_wav_f(self, value: float) -> None:
        self.__start_wav = float(value)
        self.busy_event.fire("all")
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
        temp_wav = self.__laser.get_hardware_wl()[0]
        if (temp_wav==None):
            return 'Error'
        else:
            self.__cur_wav = temp_wav
            self.__pwmeter.pw_set_wl(self.__cur_wav)
            return format(self.__cur_wav, '.4f')
    
    @property
    def run_status(self):
        return str(self.__status)
    
    @property
    def stored_status(self):
        return str(self.__stored)
    
    @property
    def power_f(self):
        if DEBUG_pw:
            self.__power = self.__pwmeter.pw_read()+self.__diode**2
        else:
            self.__power = self.__pwmeter.pw_read()
        return round(self.__power, 4)
		
    @property
    def cur_d1_f(self):
        try:
            temp=float(self.__ps.query('?C1\n').decode('UTF-8').replace('\n', ''))
            self.__diode=temp
        #try:
            #self.__diode = float(self.__ps.query('?C1\n').decode('UTF-8').replace('\n', ''))
            #return self.__diode
        except ValueError:
            self.__ps.flush()
        return self.__diode

    @cur_d1_f.setter
    def cur_d1_f(self, value):
        cvalue = format(float(value), '.2f')
        if float(cvalue) < 35 and float(cvalue) > 0.:
            self.__ps.comm('C1:'+str(cvalue)+'\n')
            self.__ps.comm('C2:'+str(cvalue)+'\n')
        time.sleep(1.0)
        self.property_changed_event.fire("cur_d1_f")
        self.property_changed_event.fire("cur_d2_f")
        self.property_changed_event.fire("power_f")
        self.free_event.fire("all")

    @property
    def cur_d2_f(self):
        return self.__ps.query('?C2\n').decode('UTF-8').replace('\n', '')

    @property
    def sht_f(self):
        return self.__ps.query('?SHT\n').decode('UTF-8').replace('\n', '')

    @property
    def d_f(self):
        return self.__ps.query('?D\n').decode('UTF-8').replace('\n', '')
    
    @property
    def q_f(self):
        return self.__ps.query('?G\n').decode('UTF-8').replace('\n', '')

    @property
    def ascii_f(self):
        return '-'
        #if self.__ps.query('?SHT\n').decode('UTF-8').replace('\n', '')=='OPEN':
            #return '\n-------o-------\n'
        #else:
        #    return '\n-------x-------\n'
