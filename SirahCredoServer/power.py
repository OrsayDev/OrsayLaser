import pyvisa
import time
import os
import json
import threading

__author__ = "Yves Auad"

class TLPowerMeter:
    
    def __init__(self, which):
        self.pwthread = None
        self.rm = pyvisa.ResourceManager()
        self.id = which
        self.lock = threading.Lock()

        try:
            self.tl = self.rm.open_resource(which)
            self.tl.timeout=200
            self.tl.write('SENS:POW:RANG:AUTO 1')
            self.tl.write('CONF:POW')
        except:
            print(self.tl.query('*IDN?'))

    
    def pw_set_wl(self, cur_WL):
        string='SENS:CORR:WAV '+str(cur_WL)
        with self.lock:
            try:
                self.tl.write(string)
            except:
                print(self.tl.query('*IDN?'))


    def pw_read(self):
        with self.lock:
            try:
                a = self.tl.query('READ?')
                return (float(a)*1e6)
            except:
                print(self.tl.query('*IDN?'))
                return (float(self.tl.query('FETCH?'))*1e6)

    def pw_reset(self):
        try:
            self.tl.close()
            time.sleep(0.01)
            self.tl = self.rm.open_resource(self.id)
            self.tl.write('SENS:POW:RANG:AUTO 1')
            self.tl.write('CONF:POW')
            self.tl.write('SENS:AVERAGE:COUNT '+str(AVG))
            print(self.tl.query('*IDN?'))
        except:
            print(self.tl.query('*IDN?'))

    def pw_set_avg(self, value):
        try:
            self.tl.write('SENS:AVERAGE:COUNT '+str(value))
            print(self.tl.query("SENS:AVERAGE:COUNT?"))
            print(self.tl.query('*IDN?'))
        except:
            print(self.tl.query('*IDN?'))

