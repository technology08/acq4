from Workbench import Workbench, arrayAverage
import time
import datetime

class State(object):
    """
    We define a state object which provides some utility functions for the
    individual states within the state machine.
    """
    wb : Workbench

    def __init__(self, wb):
        self.wb = wb
        self.file = open('resistance.txt', 'a')
        print('Processing current state:', str(self))

    def on_event(self, event):
        """
        Handle events that are delegated to this State.
        """
        pass

    def __repr__(self):
        """
        Leverages the __str__ method to describe the State.
        """
        return self.__str__()

    def __str__(self):
        """
        Returns the name of the State.
        """
        return self.__class__.__name__
    
class CaptureState(State):
    configured = False
    suction = False
    init_time = None

    def on_event(self, event):
        
        if self.init_time is None:
            self.init_time = time.perf_counter()

        if not self.configured: 
            #self.wb.pressureController.setPressure(15, 2)
            #self.wb.pressureController.writeMessageSwitch("pressure 2")
            self.configured = True

            return self
        
        if time.perf_counter() - self.init_time > 5:
            cleared = input("Has capture pipette acquired a cell? (y/n) ")
            
            if cleared == 'y':
                return HuntState(self.wb)
            elif cleared == 'n':
                return CleanState(self.wb)
            
        elif time.perf_counter() - self.init_time > 3:
            if not self.suction:
                #self.wb.pressureController.setPressure(-15, 2)
                self.suction = True

                return self
          
        return self
    

class HuntState(State):
    baselineResistance = None
    counter = 0
    totalZMovement = 0 # ,

    def on_event(self, event):
        if self.baselineResistance is None or self.counter < 10: 
            resistances = self.wb.measureResistance(frequency=60)  
            self.file.write(datetime.datetime.now().isoformat(' ') + ' ' + str(round(arrayAverage(resistances), 2)) + '\n')
            self.baselineResistance = sum(resistances) / len(resistances)  
            self.counter += 1    
        else:
            self.wb.moveManipulatorOnAxis(2, -2, 1, True)
            self.totalZMovement += 2
            newResistance = self.wb.measureResistance(60)
            print(newResistance[0])
            self.file.write(datetime.datetime.now().isoformat(' ') + ' ' + str(round(arrayAverage(newResistance), 2)) + '\n')
            
            if newResistance[0] < 0.01 * self.baselineResistance:
                print("Abort!")
                self.file.close()
                return AbortState(self.wb)
            elif newResistance[0] > 1.3 * self.baselineResistance:
                print("Seal")
                self.file.close()
                raise ValueError("something")
                return SealState(self.wb)
            elif self.totalZMovement > 100:
                self.file.close()
                raise ValueError("End!")

        return self
    
class SealState(State):
    init_time = None
    configured = False
    suction = False

    def on_event(self, event):
        if self.init_time is None:
            self.init_time = time.perf_counter()

        if not self.configured: 
            #self.wb.pressureController.writeMessageSwitch("atmosphere 1")
            self.configured = True

            return self
        
        if time.perf_counter() - self.init_time > 2:
            if not self.suction:
                #self.wb.pressureController.setPressure(-15, 1)
                #self.wb.pressureController.writeMessageSwitch("pressure 1")
                self.suction = True
                self.init_time = time.perf_counter() # restart timer

                return self
            else: 
                newResistance = self.wb.measureResistance(60)
                self.file.write(datetime.datetime.now().isoformat(' ') + ' ' + str(round(arrayAverage(newResistance), 2)) + '\n')
                if newResistance > 1e3: 
                    return BreakInState(self.wb)
                elif time.perf_counter() - self.init_time > 20:
                    return CleanState(self.wb)

        return self
    
class BreakInState(State):
    
    configured = False
    pressureSet = False
    init_time = None
    attempts = 0

    def on_event(self, event):
        if self.configured == False:
            self.init_time = time.perf_counter()
            #self.wb.pressureController.writeMessageSwitch("atmosphere 1")
            self.configured = True

            return self

        if time.perf_counter - self.init_time > 1:
            if not self.pressureSet:
                #self.wb.pressureController.setPressure(-600, 1)
                self.pressureSet = True
                return self
            
            #self.wb.pressureController.writeMessageSwitch('breakin 1 300')
            newResistance = self.wb.measureResistance(60)
            
            transient_present = self.wb.measureTransient(60)

            # Measure transient!
            if transient_present:
                return WholeCellState(self.wb)
            elif self.attempts > 10:
                return CleanState(self.wb)
            else: 
                attempts += 1

        return self
    
class WholeCellState(State):

    counter = 0
    measuredBaseResistance = False

    def on_event(self, event):
        if not self.measuredBaseResistance: 
            self.wb.currentClamp()

        return self

class CleanState(State):
    def on_event(self, event):
        if event == 'device_locked':
            return CaptureState()

        return self
    
class AbortState(State):
    def on_event(self, event):
        self.wb.__del__()

        return None
    
class SimpleDevice(object):
    """ 
    A simple state machine that mimics the functionality of a device from a 
    high level.
    """

    def __init__(self):
        """ Initialize the components. """
        self.wb = Workbench()

        # Start with a default state.
        self.state = CaptureState(self.wb)
        self.initVoltClamp()
        self.on_event('configure_capture')

    def initVoltClamp(self):
        self.wb.voltageClamp()
        self.wb.clamp.setParam('PrimarySignal', 'SIGNAL_VC_MEMBCURRENT')
        self.wb.clamp.setParam('SecondarySignal', 'SIGNAL_VC_MEMBPOTENTIAL')

    #def acquireResistance(self, stop_recording):
    #    while not stop_recording.is_set():
    #        self.resistance = self.wb.measureResistance(60)
    #        self.file.write(datetime.datetime.now().isoformat(' ') + ' ' + self.state.__str__ + str(round(arrayAverage(self.resistance), 2)) + '\n')

    def on_event(self, event):
        """
        This is the bread and butter of the state machine. Incoming events are
        delegated to the given states which then handle the event. The result is
        then assigned as the new state.
        """

        # The next state will be the result of the on_event function.
        self.state = self.state.on_event(event)#self.resistance)

machine = SimpleDevice()

try:
    while True:
        machine.on_event('')
        print(machine.state)
except KeyboardInterrupt:
    machine.wb.__del__()
    raise("Ctrl- C, Terminating")
# Every state returns the next state
# While loop runs outside state machine
# Has resistance increased by 10% Pull bath test out, will cause resistance to increase and call transition.