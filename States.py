from Workbench import Workbench
from Machine import Machine
import time


class State(object):
    """
    We define a state object which provides some utility functions for the
    individual states within the state machine.
    """
    wb : Workbench
    machine : Machine

    def __init__(self, wb, machine):
        self.wb = wb
        self.machine = machine
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
        
        if time.perf_counter() - self.init_time > 500:
            cleared = input("Has capture pipette acquired a cell? (y/n) ")
            
            if cleared == 'y':
                return HuntState(self.wb, self.machine)
            elif cleared == 'n':
                return CleanState(self.wb, self.machine)
            
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
        resistances = self.machine.resistanceHistory

        if self.baselineResistance is None or self.counter < 10: 
            self.baselineResistance = sum(resistances[-10:-1]) / len(resistances[-10:-1])  
            self.counter += 1    
        else:
            self.wb.moveManipulatorOnAxis(2, -2, 1, True)
            self.totalZMovement += 2
            newResistance = resistances[-1]
            print(newResistance)
            
            if newResistance < 0.01 * self.baselineResistance:
                print("Abort!")
                return AbortState(self.wb, self.machine)
            elif newResistance > 1.3 * self.baselineResistance:
                print("Seal")
                raise ValueError("something")
                return SealState(self.wb, self.machine)
            elif self.totalZMovement > 100:
                raise ValueError("End!")
                return CleanState(self.wb, self.machine)

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
        
        resistances = self.machine.resistanceHistory
        
        if time.perf_counter() - self.init_time > 2:
            if not self.suction:
                #self.wb.pressureController.setPressure(-15, 1)
                #self.wb.pressureController.writeMessageSwitch("pressure 1")
                self.suction = True
                self.init_time = time.perf_counter() # restart timer

                return self
            else: 
                newResistance = resistances[-1]
                if newResistance > 1e3: 
                    return BreakInState(self.wb, self.machine)
                elif time.perf_counter() - self.init_time > 20:
                    return CleanState(self.wb, self.machine)

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
            #newResistance = self.wb.measureResistance(60)
            
            #transient_present = self.wb.measureTransient(60)

            newResistance = self.machine.resistanceHistory[-1]
            transient_present = self.machine.transientHistory[-1]

            # Measure transient!
            if transient_present:
                return WholeCellState(self.wb, self.machine)
            elif self.attempts > 10:
                return CleanState(self.wb, self.machine)
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
            return CaptureState(self.wb, self.machine)

        return self
    
class AbortState(State):
    def on_event(self, event):
        self.wb.__del__()

        return None