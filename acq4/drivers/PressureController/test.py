import serial
import time

ser = serial.Serial("COM7", 115200)

print(ser.readline())
   
# Send character 'S' to start the program
ser.write(b'pressure 4\n')
print(ser.readline())

ser.close()