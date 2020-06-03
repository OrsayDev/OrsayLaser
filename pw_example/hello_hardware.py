import sys
import enum
sys.path.insert(0, "/home/yvesauad/.local/lib/python2.7/site-packages")
#print(sys.path)
import pyvisa
pyvisa.ResourceManager()
rm = pyvisa.ResourceManager()
tl = rm.open_resource('USB0::4883::32882::1907040::0::INSTR')
#print(rm.list_resources())
#print(tl.query('*IDN?'))
tl.write('*IDN?')
print(tl.read())

#tl.write('CONF:POW')
#tl.write('INIT')
#print(tl.query('FETCH?'))
#print(tl.query('CONFIGURE?'))
#print(tl.query('SENS:CORR:WAV?'))

