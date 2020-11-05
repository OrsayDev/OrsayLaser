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
        self.last = None
        self.wl = 585.
        self.avg = 10
        self.lock = threading.Lock()

        try:
            self.tl = self.rm.open_resource(which)
            self.tl.timeout=200
            self.tl.write('SENS:POW:RANG:AUTO 1')
            self.tl.write('CONF:POW')
            self.successful = True
        except:
            sensor = self.tl.query('*IDN?')
            print(f'***POWERMETER***: Could not open serial port in {sensor}')
            self.successful = False

    
    def pw_set_wl(self, cur_WL):
        string='SENS:CORR:WAV '+str(cur_WL)
        try:
            self.tl.write(string)
        except:
            sensor = self.tl.query('*IDN?')
            print(f'Problem 02 in {sensor}')


    def pw_read(self, wl):
        with self.lock:
            try:
                #Put good WL
                if abs(wl - self.wl) > 0.1:
                    self.wl = wl
                    self.pw_set_wl(wl)
                #Do power measurement
                self.last = float(self.tl.query('READ?'))*1e6
                return self.last
            except:
                sensor = self.tl.query('*IDN?')
                print(f'Problem 03 in {sensor}')
                return (float(self.tl.query('FETCH?'))*1e6)

    def pw_reset(self):
        try:
            self.tl.close()
            self.tl = self.rm.open_resource(self.id)
            self.tl.write('SENS:POW:RANG:AUTO 1')
            self.tl.write('CONF:POW')
            self.tl.write('SENS:AVERAGE:COUNT '+str(self.avg))
            print(self.tl.query('*IDN?'))
        except:
            sensor = self.tl.query('*IDN?')
            print(f'Problem 04 in {sensor}')

    def pw_set_avg(self, value):
        try:
            self.avg = int(value)
            self.tl.write('SENS:AVERAGE:COUNT '+str(value))
        except:
            sensor = self.tl.query('*IDN?')
            print(f'Problem 05 in {sensor}')

