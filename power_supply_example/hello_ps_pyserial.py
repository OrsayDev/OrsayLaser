import serial
import time
import numpy
		

ser = serial.Serial()
ser.baudrate=57600
ser.port='COM11'
ser.parity = serial.PARITY_NONE
ser.stopbits = serial.STOPBITS_ONE
ser.bytesize=serial.EIGHTBITS

ser.timeout=1
print(ser)
ser.open()
#print(ser.is_open)


ser.write(b'?SHT\n')
print(ser.readline())

ser.write(b'?C2\n')
print(ser.readline())

ser.close()
