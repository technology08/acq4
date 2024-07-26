from Machine import Machine
from States import *

machine = Machine()
machine.state = ManipulatorTestState(machine.wb, machine)#BlankState(machine.wb, machine) #ManipulatorTestState(machine.wb, machine)
try:
    while True:
        machine.processQueue()
        machine.on_event('')
        machine.updatePlot()
        #print(machine.state)
except KeyboardInterrupt:
    machine.wb.__del__()
    exit()
    raise("Ctrl- C, Terminating")