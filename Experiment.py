from Machine import Machine
from States import State, EnterBathState

machine = Machine()
machine.state = EnterBathState(machine.wb, machine)
try:
    while True:
        machine.processQueue()
        machine.on_event('')
        machine.updatePlot()
        #print(machine.state)
except KeyboardInterrupt:
    machine.wb.__del__()
    raise("Ctrl- C, Terminating")