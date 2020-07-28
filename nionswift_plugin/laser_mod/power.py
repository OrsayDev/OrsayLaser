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
    
    def __init__(self, sendmessage):
        self.sendmessage = sendmessage
        self.pwthread = None
        self.rm = pyvisa.ResourceManager()
        try:
            self.tl = self.rm.open_resource('USB0::4883::32882::1907040::0::INSTR')
            self.tl.timeout=50
            self.tl.write('SENS:POW:RANG:AUTO 1')
            self.tl.write('CONF:POW')
            self.tl.write('SENS:AVERAGE:COUNT '+str(AVG))
        except:
            self.sendmessage(24)

    
    def pw_set_wl(self, cur_WL):
        string='SENS:CORR:WAV '+str(cur_WL)
        try:
            self.tl.write(string)
        except:
            self.sendmessage(21)


    def pw_read(self):
        try:
            return (float(self.tl.query('READ?'))*1e6)
        except:
            self.sendmessage(22)
            return (float(self.tl.query('FETCH?'))*1e6)

    def pw_reset(self):
        try:
            self.tl.close()
            time.sleep(0.01)
            self.tl = self.rm.open_resource('USB0::4883::32882::1907040::0::INSTR')
            self.tl.write('SENS:POW:RANG:AUTO 1')
            self.tl.write('CONF:POW')
            self.tl.write('SENS:AVERAGE:COUNT '+str(AVG))
            self.sendmessage(25)
        except:
            self.sendmessage(26)

    def pw_set_avg(self, value):
        try:
            self.tl.write('SENS:AVERAGE:COUNT '+str(value))
            print(self.tl.query("SENS:AVERAGE:COUNT?"))
            self.sendmessage(27)
        except:
            self.sendmessage(28)

