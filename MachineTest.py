from Machine import Machine
from OldStates import State, EnterBathState

machine = Machine()
try:
    while True:
        machine.processQueue()
        print(machine.wb.patchAmplifier.getState())
        machine.updatePlot()
except KeyboardInterrupt:
    machine.wb.__del__()
    raise("Ctrl- C, Terminating")