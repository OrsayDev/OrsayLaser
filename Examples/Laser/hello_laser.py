import serial
import time
import numpy

def hex_to_pos(s):
	dec_val = 0
	for i in range(len(s)):
		dec_val+=256**i * s[i]
	return dec_val
	
def pos_to_bytes(pos):
	rem = pos
	val = numpy.zeros(4, dtype=int)
	for j in range(4):
		val[j] = rem % 256
		rem = rem - val[j]
		rem = rem / 256
	return val

def pos_to_wl(pos):
	wl = -5.26094211e-17 * pos**3 + 8.28867083e-11 * pos**2 -4.28775800e-4 * pos + 1.10796664e3
	return wl

def wl_to_pos(wl):
	pos = -1.42336972e-4 * wl**3 - 8.58549626e-1 * wl**2 -9.54738134e2 * wl +2.16000371e6
	return int(pos)
	
def set_wl(wl):
	pos = wl_to_pos(wl)
	bytes = pos_to_bytes(pos)
	checksum = bytes.sum() + 60 + 7 + 1
	if (checksum > 255):
		checksum -= 256
	send_mes = [60, 7, 1, bytes[0], bytes[1], bytes[2], bytes[3], 0, 0, 0, 0, checksum, 62]
	ba_send_mes = bytearray(send_mes)
	if (wl>500 and wl<800):
		ser.write(ba_send_mes)
	else:
		print("Care with WL!")
		
def check_wl_status():
	mes = [60, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 62]
	bs = bytearray(mes)
	ser.write(bs)
	ser.read(1)
	error = ser.read(1)
	ser.read(1)
	status = ser.read(1)
	abs1 = ser.read(4)
	ser.read(6) #clear buffer
	pos = hex_to_pos(abs1)
	cur_wl = pos_to_wl(pos)
	print(cur_wl, status[0])
		

ser = serial.Serial()
ser.baudrate=19200
ser.port='COM12'
ser.timeout=1

ser.open()

set_wl(499.70)
print()
check_wl_status()
time.sleep(3)
check_wl_status()
time.sleep(3)
check_wl_status()
time.sleep(3)
check_wl_status()
time.sleep(3)
check_wl_status()

ser.close()