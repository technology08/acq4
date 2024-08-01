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
            self.ambientResistance = arrayAverage(self.machine.resistancePatchHistory[-20:-1])
            self.wb.moveManipulatorOnAxis(2, -12000, 1000, False)
            return self 

        newResistance = arrayAverage(self.machine.resistancePatchHistory[-6:-1])
        print(newResistance)
        if (newResistance < 0.01 * self.ambientResistance) or newResistance < 100:
            self.wb.patchManipulator.stop()
            print("Enter bath!, Stopping pipette!")
            return EnterBathStateManipulator2(self.wb, self.machine)
        
        if self.wb.patchManipulator.getPos()[2] < -5000:
            print("Abort")
            raise ValueError("Abort")
        elif self.wb.patchManipulator.getPos()[2] < 0:
            self.wb.patchManipulator.setSpeed(500)
        
        if self.machine.resistancePatchHistory[-1] < 50: 
            print("one value!")
            time.sleep(1)
        
        return self
    
class EnterBathStateManipulator2(State):
    ambientResistance = None 

    def on_event(self, event):
        if self.ambientResistance is None:
            self.ambientResistance = arrayAverage(self.machine.resistanceCaptureHistory[-20:-1])
            self.wb.moveManipulator2OnAxis(2, -12000, 1000, False)
            return self 

        newResistance = arrayAverage(self.machine.resistanceCaptureHistory[-6:-1])
        print(newResistance)
        if (newResistance < 0.01 * self.ambientResistance) or newResistance < 100:
            self.wb.captureManipulator.stop()
            print("Enter bath!, Stopping pipette!")
            return CaptureState(self.wb, self.machine)
        
        if self.wb.captureManipulator.getPos()[2] < -5000:
            print("Abort")
            raise ValueError("Abort")
        elif self.wb.captureManipulator.getPos()[2] < 0:
            self.wb.captureManipulator.setSpeed(500)
        
        if self.machine.resistanceCaptureHistory[-1] < 50: 
            print("one value!")
            time.sleep(1)
        
        return self

class CaptureState(State):
    configured = False
    suction = False
    init_time = None

    def on_event(self, event):
        
        if self.init_time is None:
            self.init_time = time.perf_counter()

        if not self.configured: 
            self.wb.pressureController.writeMessageSwitch(b"atm 1")
            self.wb.pressureController.setPressure(200, 1)
            self.wb.pressureController.writeMessageSwitch(b"pressure 1")
            self.configured = True

            return self
        
        if time.perf_counter() - self.init_time > 30:
        #    return HuntState(self.wb, self.machine) # TODO: Remove once user interaction wanted
        #
            #self.wb.pressureController.writeMessageSwitch(b"atm 1")
            #self.wb.pressureController.setPressure(0, 1)
           # return BlankState(self.wb, self.machine)

            return SealState(self.wb, self.machine)
            
        elif time.perf_counter() - self.init_time > 2:
            if not self.suction:
                self.wb.pressureController.setPressure(-15, 1)
                self.suction = True

                return self
            else:
                print("Resistance Average at Time ",  str(round(time.perf_counter() - self.init_time)), ":", arrayAverage(self.machine.resistanceCaptureHistory[-10:-1]))
        else:
            print("Resistance Average at Time ",  str(round(time.perf_counter() - self.init_time)), ":", arrayAverage(self.machine.resistanceCaptureHistory[-10:-1]))
          
        return self
    

class HuntState(State):
    baselineResistance = None
    counter = 0
    totalZMovement = 0 # ,

    def on_event(self, event):
        time.sleep(2)
        return CleanState(self.wb, self.machine)
        resistances = self.machine.resistancePatchHistory

        if self.baselineResistance is None or self.counter < 10: 
            self.baselineResistance = sum(resistances[-10:-1]) / len(resistances[-10:-1])  
            self.counter += 1    
        else:
            self.wb.moveManipulatorOnAxis(2, -2, 10000, False)
            self.totalZMovement += 2
            newResistance = resistances[-1]
            print(newResistance)
            
            if newResistance < 0.01 * self.baselineResistance:
                self.wb.patchManipulator.stop()
                print("Abort!")
                #return AbortState(self.wb, self.machine)
            elif newResistance > 1.3 * self.baselineResistance:
                self.wb.patchManipulator.stop()
                print("Seal")
                raise ValueError("Cell found, Seal")
                return SealState(self.wb, self.machine)
            elif self.totalZMovement > 10: # TODO: Made easier to trigger for testing
                self.wb.patchManipulator.stop()
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
            self.wb.pressureController.writeMessageSwitch(b"atmosphere 2")
            self.wb.pressureController.setPressure(15, 2)
            self.wb.pressureController.writeMessageSwitch(b"pressure 2")
            self.configured = True

            return self
        
        resistances = self.machine.resistancePatchHistory

        print("Resistance Average at Time ",  str(round(time.perf_counter() - self.init_time)), ":", arrayAverage(resistances[-10:-1]))
        
        if time.perf_counter() - self.init_time > 5:
            if not self.suction:
                self.wb.pressureController.setPressure(-20, 2)
                self.wb.pressureController.writeMessageSwitch(b"pressure 2")
                self.suction = True
                self.init_time = time.perf_counter() # restart timer

                return self
            
        
        elif time.perf_counter() - self.init_time > 180:
            
            self.wb.pressureController.writeMessageSwitch(b"atm 2")
            self.wb.pressureController.setPressure(0, 2)
            self.wb.pressureController.writeMessageSwitch(b"atm 1")
            self.wb.pressureController.setPressure(0, 1)
            return BlankState(self.wb, self.machine)
            #else: 
            #    newResistance = resistances[-1]
            #    if newResistance > 1e3: 
            #        return BreakInState(self.wb, self.machine)
            #    elif time.perf_counter() - self.init_time > 20:
            #        return CleanState(self.wb, self.machine)

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

            newResistance = self.machine.resistancePatchHistory[-1]
            transient_present = self.machine.transientPatchHistory[-1]

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
    ps1Returning = False
    cleaned = False
    clean_start_time = None
    period_start_time = None
    cycles = 0
    pressure1_set = False
    pressure2_set = False
    runs = 0
    initialPos1 = []
    initialPos2 = []

    def on_event(self, event):
        if len(self.initialPos1) < 1:
            print('fire')
            self.initialPos1 = self.wb.patchManipulator.getPos()
        if len(self.initialPos2) < 1:
            self.initialPos2 = self.wb.captureManipulator.getPos()

        print(self.initialPos1)
        print(self.initialPos2)

        if not self.ps1Raised:
            dist_to_top = self.wb.patchManipulator.getLimits()[2][1] - self.wb.patchManipulator.getPos()[2]
            dist_to_top_2 = self.wb.captureManipulator.getLimits()[2][1] - self.wb.captureManipulator.getPos()[2]
            self.wb.moveManipulatorOnAxis(2, dist_to_top, 1500, False)
            self.wb.moveManipulator2OnAxis(2, dist_to_top_2, 1500, False)
            self.ps1Raised = True
        elif not self.ps1PulledBack: 
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                dist_to_back = self.wb.patchManipulator.getLimits()[0][1] - self.wb.patchManipulator.getPos()[0]
                dist_to_back_2 = self.wb.captureManipulator.getLimits()[0][1] - self.wb.captureManipulator.getPos()[0]
                self.wb.moveManipulatorOnAxis(0, dist_to_back, 2000, False)
                self.wb.moveManipulator2OnAxis(0, dist_to_back_2, 2000, False)
                self.ps1PulledBack = True
        elif not self.cleaned: 
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                # Run clean step
                current_time = time.perf_counter()

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
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                self.wb.patchManipulator.moveTo(self.initialPos1, 2000)
                self.wb.captureManipulator.moveTo(self.initialPos2, 2000)
                self.ps1Hovering = True
        elif self.ps1Hovering and (not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving()):
            # Returned, move back to CaptureState
            if self.runs >= 500:
                self.machine.__del__()
                
                return None
            else:
                self.machine.saveImage = True
                self.ps1Raised = False 
                self.ps1PulledBack = False
                self.ps1Hovering = False
                self.ps1Lowering = False 
                self.cleaned = False
                self.clean_start_time = None
                self.period_start_time = None
                self.cycles = 0
                self.pressure1_set = False
                self.pressure2_set = False
                self.runs += 1
        return self

class CleanTestState(State):
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
            if not self.wb.patchManipulator.isMoving():
                self.wb.moveManipulatorOnAxis(0, 20000, 20000, False)
                self.ps1PulledBack = True
        elif not self.cleaned: 
            if not self.wb.patchManipulator.isMoving():
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
            if not self.wb.patchManipulator.isMoving():
                self.wb.moveManipulatorOnAxis(2, -10000, 10000, False)
                self.ps1Lowering = True
        elif self.ps1Lowering and (not self.wb.patchManipulator.isMoving() or arrayAverage(self.machine.resistancePatchHistory[-5:-1]) < 50):
            # Returned, move back to CaptureState
            if self.wb.patchManipulator.isMoving():
                self.wb.patchManipulator.stop() 
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
        
        print(self.wb.measurePressure(2))
        # Pos pressure for 2 sec , negative for 1 sec, at +500mbar -500mbar
        if current_time - self.period_start_time >= 3:
            print("hallo")
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

class LightsTestState(State):

    def on_event(self, event):
        self.wb.lightsOn()
        time.sleep(2)
        self.wb.lightsOff()
        time.sleep(2)

        return self
    
class BlankState(State):
    def on_event(self, event):
        
        return self
    
class ManipulatorTestState(State):
    ps1Raised = False 
    ps1PulledBack = False
    ps1Hovering = False
    ps1Lowering = False 
    ps1Returning = False
    cleaned = False
    clean_start_time = None
    period_start_time = None
    cycles = 0
    pressure1_set = False
    pressure2_set = False
    runs = 0
    initialPos1 = []
    initialPos2 = []

    def on_event(self, event):
        if len(self.initialPos1) < 1:
            self.initialPos1 = self.wb.patchManipulator.getPos()
            self.newPos11 = [self.initialPos1[0] + 2000, self.initialPos1[1], self.initialPos1[2] + 1000]
            self.newPos12 = [self.initialPos1[0], self.initialPos1[1] + 2000, self.initialPos1[2]]
            self.newPos13 = [self.initialPos1[0] - 50, self.initialPos1[1] + 2000, self.initialPos1[2] + 50]
        if len(self.initialPos2) < 1:
            self.initialPos2 = self.wb.captureManipulator.getPos()
            self.newPos21 = [self.initialPos2[0] + 2000, self.initialPos2[1], self.initialPos2[2] + 1000]
            self.newPos22 = [self.initialPos2[0], self.initialPos2[1] + 2000, self.initialPos2[2]]
            self.newPos23 = [self.initialPos2[0] - 50, self.initialPos2[1] + 2000, self.initialPos2[2] + 50]

        
        if not self.ps1Raised:
            self.wb.patchManipulator.moveTo(self.newPos11, 1000)
            self.wb.captureManipulator.moveTo(self.newPos21, 1000)

            self.ps1Raised = True
        elif not self.ps1PulledBack: 
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                self.wb.patchManipulator.moveTo(self.newPos12, 1000)
                self.wb.captureManipulator.moveTo(self.newPos22, 1000)
                self.ps1PulledBack = True
        elif not self.cleaned: 
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                self.wb.moveManipulatorOnAxis(1, -10, 1000, False)
                self.wb.moveManipulator2OnAxis(1, -10, 1000, False)
                
                if self.cycles > 10:
                    self.cleaned = True
                    return self
                self.cycles += 1
        elif not self.ps1Hovering:
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                self.wb.patchManipulator.moveTo(self.newPos13, 1000)
                self.wb.captureManipulator.moveTo(self.newPos23, 1000)
                self.ps1Hovering = True
        elif not self.ps1Lowering:
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                self.ps1Lowering = True
        elif not self.ps1Returning:
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                self.wb.patchManipulator.moveTo(self.initialPos1)
                self.wb.captureManipulator.moveTo(self.initialPos2)
                self.ps1Returning = True
        elif self.ps1Returning and (not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving()):
            # Returned, move back to CaptureState
            if self.runs >= 1000:
                self.machine.__del__()
                
                return None
            else:
                self.machine.saveImage = True
                self.ps1Raised = False 
                self.ps1PulledBack = False
                self.ps1Hovering = False
                self.ps1Lowering = False 
                self.cleaned = False
                self.clean_start_time = None
                self.period_start_time = None
                self.cycles = 0
                self.pressure1_set = False
                self.pressure2_set = False
                self.runs += 1
        return self
    
class ManipulatorAbsoluteTestState(State):
    ps1Raised = False 
    ps1PulledBack = False
    ps1Hovering = False
    ps1Lowering = False 
    ps1Returning = False
    cleaned = False
    clean_start_time = None
    period_start_time = None
    cycles = 0
    pressure1_set = False
    pressure2_set = False
    runs = 0
    initialPos1 = []
    initialPos2 = []

    def on_event(self, event):
        if len(self.initialPos1) < 1:
            print('fire')
            self.initialPos1 = self.wb.patchManipulator.getPos()
        if len(self.initialPos2) < 1:
            self.initialPos2 = self.wb.captureManipulator.getPos()

        print(self.initialPos1)
        print(self.initialPos2)

        if not self.ps1Raised:
            self.wb.moveManipulatorOnAxis(2, 1000, 1500, False)
            self.wb.moveManipulator2OnAxis(2, 1000, 1500, False)
            self.ps1Raised = True
        elif not self.ps1PulledBack: 
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                self.wb.moveManipulatorOnAxis(0, 2000, 2000, False)
                self.wb.moveManipulator2OnAxis(0, 2000, 2000, False)
                self.ps1PulledBack = True
        elif not self.cleaned: 
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                # Run clean step
                current_time = time.perf_counter()

                if self.clean_start_time is None:
                    self.clean_start_time = current_time
                    self.period_start_time = current_time

                    self.wb.moveManipulatorOnAxis(1, 1000, 2000, False)
                    self.wb.moveManipulator2OnAxis(1, -1000, 2000, False)
                elif self.cycles > 10:
                    self.cleaned = True
                    return self
                self.cycles += 1
        elif not self.ps1Hovering:
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                self.wb.patchManipulator.moveTo(self.initialPos1, 2000)
                self.wb.captureManipulator.moveTo(self.initialPos2, 2000)
                self.ps1Hovering = True
        elif self.ps1Hovering and (not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving()):
            # Returned, move back to CaptureState
            if self.runs >= 500:
                self.machine.__del__()
                
                return None
            else:
                self.machine.saveImage = True
                self.ps1Raised = False 
                self.ps1PulledBack = False
                self.ps1Hovering = False
                self.ps1Lowering = False 
                self.cleaned = False
                self.clean_start_time = None
                self.period_start_time = None
                self.cycles = 0
                self.pressure1_set = False
                self.pressure2_set = False
                self.runs += 1
        return self
    
#Move [5502.3, -5465.0, 2509.4] => [None, None, 3009.4]
#Move [10468.0, -1411.0, 3102.1] => [None, None, 3602.1]

#Move [5016.6, -8516.4, -4252.2] => [None, None, -3752.2]
#Move [11986.6, 1767.4, -3517.1] => [None, None, -3017.1]