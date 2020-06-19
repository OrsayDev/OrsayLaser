import serial
import time
import numpy
import random
		

ser = serial.Serial()
ser.baudrate=9600
ser.port='COM15'
ser.parity = serial.PARITY_NONE
ser.stopbits = serial.STOPBITS_ONE
ser.bytesize=serial.EIGHTBITS

ser.timeout=2
print(ser)
ser.open()
print(ser.is_open)

print(ser.readline())


value=0
signal=1
while True:
	ser.write(('POS:'+str(value)+'\n').encode())
	time.sleep(0.02)
	if random.uniform(0, 1)>0.9:
		ser.write(b'?POS\n')
		print(ser.readline())
	value=value+signal*5
	if value==180:
		signal=-1
	if value==0:
		signal=1





ser.close()

print(ser.is_open)
