import time
import threading
import numpy
import enum
import pyvisa
import logging

__author__ = "Yves Auad"

def SENDMYMESSAGEFUNC(sendmessagefunc):
    return sendmessagefunc



class TLPowerMeter:
    
    def __init__(self, sendmessage):
        self.sendmessage = sendmessage
        self.pwthread = None
        rm = pyvisa.ResourceManager()
        try:
            self.tl = rm.open_resource('USB0::4883::32882::1907040::0::INSTR')
            logging.info(self.tl.query('*IDN?'))
            #self.tl.write('SENS:CORR:COLL:ZERO:INIT')
            self.tl.write('SENS:POW:RANG:AUTO 1')
            self.tl.write('CONF:POW')
        except:
            logging.info("No device was found") #not working

    
    def pw_set_wl(self, cur_WL):
        string='SENS:CORR:WAV '+str(cur_WL)
        self.tl.write(string)
        #logging.info(self.tl.query('SENS:CORR:WAV?'))


    def pw_read(self):
        return (float(self.tl.query('READ?'))*1e6)
