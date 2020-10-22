import pyvisa
import time
import os
import json

abs_path = os.path.abspath(os.path.join((__file__+"/../"), "global_settings.json"))
with open(abs_path) as savfile:
    settings = json.load(savfile)

AVG = settings["PW"]["AVG"]


__author__ = "Yves Auad"

def SENDMYMESSAGEFUNC(sendmessagefunc):
    return sendmessagefunc



class TLPowerMeter:
    
    def __init__(self, sendmessage, which):
        self.sendmessage = sendmessage
        self.pwthread = None
        self.rm = pyvisa.ResourceManager()
        self.id = which
        try:
            self.tl = self.rm.open_resource(which)
            self.tl.timeout=50
            self.tl.write('SENS:POW:RANG:AUTO 1')
            self.tl.write('CONF:POW')
            self.tl.write('SENS:AVERAGE:COUNT '+str(AVG))
        except:
            print(self.tl.query('*IDN?'))
            self.sendmessage(24)

    
    def pw_set_wl(self, cur_WL):
        string='SENS:CORR:WAV '+str(cur_WL)
        try:
            self.tl.write(string)
        except:
            print(self.tl.query('*IDN?'))
            self.sendmessage(21)


    def pw_read(self):
        try:
            a = self.tl.query('READ?')
            return (float(a)*1e6)
        except:
            print(self.tl.query('*IDN?'))
            self.sendmessage(22)
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
            self.sendmessage(25)
        except:
            print(self.tl.query('*IDN?'))
            self.sendmessage(26)

    def pw_set_avg(self, value):
        try:
            self.tl.write('SENS:AVERAGE:COUNT '+str(value))
            print(self.tl.query("SENS:AVERAGE:COUNT?"))
            print(self.tl.query('*IDN?'))
            self.sendmessage(27)
        except:
            print(self.tl.query('*IDN?'))
            self.sendmessage(28)

