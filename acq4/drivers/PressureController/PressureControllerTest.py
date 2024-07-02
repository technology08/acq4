from PressureController import PressureController
import time

IDs = [1]# , 2, 3, 4]
pc = PressureController(IDs, ['COM8', 'COM9', 'COM10', 'COM11'])

for idx in IDs:

    print("High Pressure 200mbar")
    pc.setPressure(200, idx)
    time.sleep(3)

    print("Pressure Mode on Channel ", idx)
    pc.writeMessageSwitch(bytes(('pressure ' + str(idx) +'\n'), 'utf-8'))
    time.sleep(3)

    print("Low Pressure 15mbar")
    pc.setPressure(15, idx)
    time.sleep(3)
    
    print("Low Suction, 30mbar")
    pc.setPressure(-30, idx)
    time.sleep(3)

    print("Atmosphere")
    pc.writeMessageSwitch(bytes(('atm ' + str(idx) + '\n'), 'utf-8'))
    time.sleep(3)

    print("Apply high suction")
    pc.setPressure(-600, idx)
    time.sleep(3)

    print("Break in for 300ms")
    pc.writeMessageSwitch(bytes(('breakin ' + str(idx) + ' 300\n'), 'utf-8'))
    time.sleep(3)

    pc.setPressure(0, idx)