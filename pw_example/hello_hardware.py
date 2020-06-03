import sys
import enum
import pyvisa
#sys.path.insert(0, "/home/yvesauad/.local/lib/python2.7/site-packages")
#print(sys.path)
#pyvisa.ResourceManager()
rm = pyvisa.ResourceManager()
print(rm.list_resources())
tl = rm.open_resource('USB0::4883::32882::1907040::0::INSTR')
print(tl.query('*IDN?'))
#tl.write('*IDN?')
#print(tl.read())

#tl.write('SENS:CORR:COLL:ZERO:INIT') #perform zero adjustment
tl.write('CONF:POW') # set meas as power
print(tl.query('SENS:POW:RANG:AUTO?'))

print(tl.query('READ?')) #get measurement

tl.write('SENS:CORR:WAV  540') #set wl
print(tl.query('SENS:CORR:WAV?')) #see WL


