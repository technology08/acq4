from Machine import Machine
from States import *

machine = Machine()
machine.state = CaptureState(machine.wb, machine)
try:
    while True:
        machine.processQueue()
        machine.on_event('')
        machine.updatePlot()
        #print(machine.state)
except KeyboardInterrupt:
    machine.wb.__del__()
    raise("Ctrl- C, Terminating")