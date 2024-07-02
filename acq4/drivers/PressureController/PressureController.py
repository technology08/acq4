import serial
import math
from pymodbus.client import ModbusSerialClient
from pymodbus.framer import *
import time

class PressureController:

    #pressure_ports = ['COM8', 'COM9', 'COM10', 'COM11']
    pressure_clients = {}

    monitoraddress = 40049
    commandaddress = 40050
    baudrate = 115200
    parity = 'E'
    bytesize = 8
    timeout = 0.1
    serverID = 247
    
    def __init__(self, channelIDs, ports):
        self.defaultConfigure()
        self.switch = serial.Serial("COM7", 115200)

        for i in range(len(channelIDs)):
            client = ModbusSerialClient(
                    port=ports[i],
                    baudrate=self.baudrate,
                    bytesize=self.bytesize,
                    parity=self.parity,
                    timeout=self.timeout
                    )   # Create client object
            client.connect()
            self.pressure_clients[int(channelIDs[i])] = client

        print(self.switch.readline())
        
    def writeMessageSwitch(self, msg):
        # Send character 'S' to start the program
        self.switch.write(msg) #b'pressure 4\n')
        return self.switch.readline()
    
    def setPressure(self, pressure, idx):
        register_value = self.convert_pressure_to_register_value(pressure, self.cal_slope[idx], self.cal_intercept[idx])
        print('Pressure Command: ', register_value)
        self.pressure_clients[idx].write_registers(address=self.convert_address(self.commandaddress), 
                                                   values=register_value, slave=self.serverID)        # set information in device
        
        time.sleep(0.1)
        print(self.measurePressure(idx))
        
    def measurePressure(self, idx):
        result = self.pressure_clients[idx].read_holding_registers(address=self.convert_address(self.monitoraddress), 
                                                                   count=1, slave=self.serverID)  # get information from device

        if hasattr(result, 'registers'):
            pressure = self.convert_register_to_pressure(result.registers[0], self.cal_slope[idx], self.cal_intercept[idx])
            return pressure
        

    def defaultConfigure(self):
        self.cal_slope = {1: 38.62, 2: 38.49, 3: 38.68, 4: 38.77}
        self.cal_intercept = {1: 27434, 2: 29667, 3: 27587, 4: 27303}

    def convert_address(self, input_address):
        output_address = input_address-40000-1
        return output_address

    def coerce_to_range(self, n, minn, maxn):
        return max(min(maxn, n), minn)

    def convert_register_to_pressure(self, input_register, cal_slope, cal_intercept):
        pressure_mbar = (float(input_register) - cal_intercept) / cal_slope
        return pressure_mbar

    def convert_pressure_to_register_value(self, pressure_mbar, cal_slope, cal_intercept):
        register_value = int(math.floor(cal_slope*pressure_mbar + cal_intercept))

        # coerce values to 0-65535
        return self.coerce_to_range(register_value, 0, 65535)
    
    def __del__(self):
        self.switch.close()
        for client in self.pressure_clients.values():
            client.close()

    def calibrate(self):
        # Calibration Procedure (linear regression on pressure (x) vs command value (y))
        for client in self.pressure_clients.values():
            for command in range(0, 65537, 2048):
                client.write_registers(address=self.convert_address(self.commandaddress, values=command, slave=self.serverID))       # set information in device
                pressure_response = input('Current Pressure (mbar): ')
                print(command, pressure_response)