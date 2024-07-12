from Workbench import Workbench, arrayAverage
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

class EnterBathState(State):
    ambientResistance = None 

    def on_event(self, event):
        if self.ambientResistance is None:
            self.ambientResistance = arrayAverage(self.machine.resistanceHistory[-20:-1])
            self.wb.moveManipulatorOnAxis(2, -12000, 1000, False)
            return self 

        newResistance = arrayAverage(self.machine.resistanceHistory[-6:-1])
        print(newResistance)
        if (newResistance < 0.01 * self.ambientResistance) or newResistance < 100:
            self.wb.ps.stop()
            print("Enter bath!, Stopping pipette!")
            return CaptureState(self.wb, self.machine)
        
        if self.wb.ps.getPos()[2] < -5000:
            print("Abort")
            raise ValueError("Abort")
        elif self.wb.ps.getPos()[2] < 0:
            self.wb.ps.setSpeed(500)
        
        if self.machine.resistanceHistory[-1] < 50: 
            print("one value!")
            time.sleep(4)
        
        return self

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
            return HuntState(self.wb, self.machine) # TODO: Remove once user interaction wanted
        
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
        time.sleep(2)
        return CleanState(self.wb, self.machine)
        resistances = self.machine.resistanceHistory

        if self.baselineResistance is None or self.counter < 10: 
            self.baselineResistance = sum(resistances[-10:-1]) / len(resistances[-10:-1])  
            self.counter += 1    
        else:
            self.wb.moveManipulatorOnAxis(2, -2, 10000, False)
            self.totalZMovement += 2
            newResistance = resistances[-1]
            print(newResistance)
            
            if newResistance < 0.01 * self.baselineResistance:
                self.wb.ps.stop()
                print("Abort!")
                #return AbortState(self.wb, self.machine)
            elif newResistance > 1.3 * self.baselineResistance:
                self.wb.ps.stop()
                print("Seal")
                raise ValueError("Cell found, Seal")
                return SealState(self.wb, self.machine)
            elif self.totalZMovement > 10: # TODO: Made easier to trigger for testing
                self.wb.ps.stop()
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
    ps1Raised = False 
    ps1PulledBack = False
    ps1Hovering = False
    ps1Lowering = False 
    cleaned = False
    clean_start_time = None
    period_start_time = None
    cycles = 0
    pressure1_set = False
    pressure2_set = False

    def on_event(self, event):
        if not self.ps1Raised:
            self.wb.moveManipulatorOnAxis(2, 10000, 15000, False)
            self.ps1Raised = True
        elif not self.ps1PulledBack: 
            if not self.wb.ps.isMoving():
                self.wb.moveManipulatorOnAxis(0, 20000, 20000, False)
                self.ps1PulledBack = True
        elif not self.cleaned: 
            if not self.wb.ps.isMoving():
                # Run clean step
                current_time = time.perf_counter()

                if self.clean_start_time is None:
                    self.clean_start_time = current_time
                    self.period_start_time = current_time
                    self.wb.pressureController.writeMessageSwitch(b"atm 1")
                    self.wb.pressureController.setPressure(500, 1)
                    self.wb.pressureController.writeMessageSwitch(b"pressure 1")
                elif self.cycles > 5:
                    self.cleaned = True
                    self.wb.pressureController.writeMessageSwitch(b'atm 1')
                    self.wb.pressureController.setPressure(0, 1)
                    return self
                # Clean the pipette
                
                # Pos pressure for 2 sec , negative for 1 sec, at +500mbar -500mbar
                if current_time - self.period_start_time >= 3:
                    if self.pressure2_set == False:
                        self.wb.pressureController.setPressure(500, 1)
                        self.period_start_time = current_time
                        self.cycles += 1
                        self.pressure2_set = True
                        self.pressure1_set = False
                elif current_time - self.period_start_time >= 2:
                    if self.pressure1_set == False:
                        self.wb.pressureController.setPressure(-500, 1)
                        self.pressure1_set = True
                        self.pressure2_set = False
        elif not self.ps1Hovering:
            self.wb.moveManipulatorOnAxis(0, -20000, 20000, False)
            self.ps1Hovering = True
        elif not self.ps1Lowering:
            if not self.wb.ps.isMoving():
                self.wb.moveManipulatorOnAxis(2, -10000, 10000, False)
                self.ps1Lowering = True
        elif self.ps1Lowering and (not self.wb.ps.isMoving() or arrayAverage(self.machine.resistanceHistory[-5:-1]) < 50):
            # Returned, move back to CaptureState
            if self.wb.ps.isMoving():
                self.wb.ps.stop() 
            return CaptureState(self.wb, self.machine)

        return self
    
class AbortState(State):
    def on_event(self, event):
        self.wb.__del__()

        return None
    
class PressureTestState(State):
    clean_start_time = None
    period_start_time = None
    cycles = 0
    pressure1_set = False
    pressure2_set = False

    def on_event(self, event):
                # Run clean step
        current_time = time.perf_counter()

        if self.clean_start_time is None:
            self.clean_start_time = current_time
            self.period_start_time = current_time
            self.wb.pressureController.writeMessageSwitch(b"atm 2")
            self.wb.pressureController.setPressure(500, 2)
            self.wb.pressureController.writeMessageSwitch(b"pressure 2")
        elif self.cycles > 20:
            self.wb.pressureController.writeMessageSwitch(b'atm 2')
            self.wb.pressureController.setPressure(0, 2)
            return None
        # Clean the pipette
        
        # Pos pressure for 2 sec , negative for 1 sec, at +500mbar -500mbar
        if current_time - self.period_start_time >= 3:
            if self.pressure2_set == False:
                self.wb.pressureController.setPressure(500, 2)
                self.period_start_time = current_time
                self.cycles += 1
                self.pressure2_set = True
                self.pressure1_set = False
        elif current_time - self.period_start_time >= 2:
            if self.pressure1_set == False:
                self.wb.pressureController.setPressure(-500, 2)
                self.pressure1_set = True
                self.pressure2_set = False

        return self