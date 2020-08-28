import sys
import enum
import pyvisa
from pyvisa import constants, ResourceManager
import time
#sys.path.insert(0, "/home/yvesauad/.local/lib/python2.7/site-packages")
#print(sys.path)
#pyvisa.ResourceManager()
#pyvisa.log_to_screen()
rm = pyvisa.ResourceManager()
print(rm.list_resources())
ps = rm.open_resource('ASRL11::INSTR')
ps.baud_rate=57600
print(ps.baud_rate)
print(ps.parity)
print(ps.stop_bits)
print(ps.data_bits)
#ps.flow_control = constants.VI_ASRL_FLOW_RTS_CTS
#ps.flow_control = constants.VI_ASRL_FLOW_NONE
ps.timeout = 1000

ps.write_termination = '\n'
ps.read_termination = '\n'


ps.write('?SHT')
print(ps.read())



