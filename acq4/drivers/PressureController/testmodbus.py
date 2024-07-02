from pymodbus.client import ModbusSerialClient
from pymodbus.framer import *
import math

# COM8, 9, 10, 11
port = 'COM11'
serverID = 247
monitoraddress = 40049
commandaddress = 40050
baudrate = 115200
parity = 'E'
bytesize = 8
timeout = 0.1

# channel 4 (COM11)
cal_slope = 38.77
cal_intercept = 27303

# channel 3 (COM10)
cal_slope = 38.68
cal_intercept = 27587 

# channel 2 (COM9)
cal_slope = 38.49
cal_intercept = 29667

# channel 1 (COM8)
cal_slope = 38.62
cal_intercept = 27434

pressure_value = -600 # mbar

def convert_address(input_address):
    output_address = input_address-40000-1
    return output_address

def coerce_to_range(n, minn, maxn):
    return max(min(maxn, n), minn)

def convert_register_to_pressure(input_register, cal_slope, cal_intercept):
    pressure_mbar = (float(input_register) - cal_intercept) / cal_slope
    return pressure_mbar

def convert_pressure_to_register_value(pressure_mbar, cal_slope, cal_intercept):
    register_value = int(math.floor(cal_slope*pressure_mbar + cal_intercept))

    # coerce values to 0-65535
    return coerce_to_range(register_value, 0, 65535)

client = ModbusSerialClient(
    port=port,
    baudrate=baudrate,
    bytesize=bytesize,
    parity=parity,
    timeout=timeout
    )   # Create client object

client.connect()                           # connect to device, reconnect automatically
register_value = convert_pressure_to_register_value(pressure_value, cal_slope, cal_intercept)
print('Pressure Command: ', register_value)
client.write_registers(address=convert_address(commandaddress), values=register_value, slave=serverID)        # set information in device

result = client.read_holding_registers(address=convert_address(monitoraddress), count=1, slave=serverID)  # get information from device

if hasattr(result, 'registers'):
    print(convert_register_to_pressure(result.registers[0], cal_slope, cal_intercept))


result = client.read_holding_registers(address=convert_address(40018), count=4, slave=serverID)  # get information from device
print(result.registers)

# Calibration Procedure (linear regression on pressure (x) vs command value (y))
should_calibrate = False
if should_calibrate:
    for command in range(0, 65537, 2048):
        client.write_registers(address=convert_address(commandaddress), values=command, slave=serverID)        # set information in device
        pressure_response = input('Current Pressure (mbar): ')
        print(command, pressure_response)

client.close()                             # Disconnect device