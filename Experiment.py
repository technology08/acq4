from Machine import Machine
from TestStates import *
from time import sleep

runs = 0
registerNewRun = False

machine = Machine()
sleep(2)
machine.state = CaptureTestState(machine.wb, machine)
try:
    while runs < 100:
        machine.processQueue()
        machine.on_event('')
        if machine.state.__str__ == "CaptureTestState":
            registerNewRun = True
        elif machine.state.__str__ == "MoveCapturedState" and registerNewRun:
            runs += 1
            registerNewRun = False
        machine.updatePlot()
        #print(machine.state)
except KeyboardInterrupt:
    machine.wb.__del__()
    raise("Ctrl- C, Terminating")