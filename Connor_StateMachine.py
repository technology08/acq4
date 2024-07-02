from Workbench import Workbench
import time

class State(object):
    """
    We define a state object which provides some utility functions for the
    individual states within the state machine.
    """
    wb : Workbench

    def __init__(self, wb):
        self.wb = wb
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
        
        #print(self.configured)
        if self.init_time is None:
            self.init_time = time.perf_counter()
        #print(time.perf_counter() - self.init_time > 3)
        if not self.configured: 
            #self.wb.pressureController.setPressure(15, 2)
            #self.wb.pressureController.writeMessageSwitch("pressure 2")
            self.configured = True

            return self
        
        if time.perf_counter() - self.init_time > 3:
            if not self.suction:
                #self.wb.pressureController.setPressure(-15, 2)
                self.suction = True

                return self
        
        if time.perf_counter() - self.init_time > 5:
            cleared = input("Has capture pipette acquired a cell? (y/n) ")
            
            if cleared == 'y':
                return HuntState(self.wb)
            elif cleared == 'n':
                return CleanState(self.wb)
        
        
        return self
    

class HuntState(State):
    baselineResistance = None
    totalZMovement = 0 # ,

    def on_event(self, event):
        if self.baselineResistance is None: 
            resistances = self.wb.measureResistance(frequency=60)  
            self.baselineResistance = sum(resistances) / len(resistances)      
        else:
            self.wb.moveManipulatorOnAxis(2, -2, 1, True)
            self.totalZMovement += 2
            newResistance = self.wb.measureResistance(60)
            
            if newResistance < 0.01 * self.baselineResistance:
                print("Abort!")
                return AbortState(self.wb)
            elif newResistance > 1.1 * self.baselineResistance:
                print("Seal")
                return SealState(self.wb)
            elif self.totalZMovement > 100:
                raise ValueError("End!")
                return CleanState(self.wb)

        return self
    
class SealState(State):
    def on_event(self, event):
        if event == 'pin_entered':
            return CleanState()

        return self
    
class BreakInState(State):
    def on_event(self, event):
        if event == 'pin_entered':
            return CleanState()

        # define our loop here
        return self
    
class WholeCellState(State):
    def on_event(self, event):
        if event == 'pin_entered':
            return CleanState()

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
        self.on_event('configure_capture')

    def on_event(self, event):
        """
        This is the bread and butter of the state machine. Incoming events are
        delegated to the given states which then handle the event. The result is
        then assigned as the new state.
        """

        # The next state will be the result of the on_event function.
        self.state = self.state.on_event(event)

machine = SimpleDevice()

while True:
    machine.on_event('')
    print(machine.state)
    
# Every state returns the next state
# While loop runs outside state machine
# Has resistance increased by 10% Pull bath test out, will cause resistance to increase and call transition.