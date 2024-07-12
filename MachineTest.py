from Machine import Machine
from States import State, EnterBathState

machine = Machine()
try:
    while True:
        machine.processQueue()
        machine.updatePlot()
except KeyboardInterrupt:
    machine.wb.__del__()
    raise("Ctrl- C, Terminating")