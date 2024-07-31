from Workbench import Workbench, arrayAverage
from Machine import Machine
from States import State
import time

class CaptureTestState(State):
    configured = False
    suction = False
    init_time = None

    def on_event(self, event):
        self.machine.saveImage = True

        if self.init_time is None:
            self.init_time = time.perf_counter()

        if not self.configured: 
            #self.wb.pressureController.writeMessageSwitch(b"atm 1")
            self.wb.pressureController.setPressure(400, 1)
            self.wb.pressureController.writeMessageSwitch(b"pressure 1")
            self.configured = True

            return self
        
        if time.perf_counter() - self.init_time > 12:
            return MoveCapturedState(self.wb, self.machine)
            
        elif time.perf_counter() - self.init_time > 5:
            if not self.suction:
                self.wb.pressureController.setPressure(-30, 1)
                self.suction = True

                return self
            else:
                print("Resistance Average at Time ",  str(round(time.perf_counter() - self.init_time)), ":", arrayAverage(self.machine.resistance2History[-10:-1]))
        
        else:
            print("Resistance Average at Time ",  str(round(time.perf_counter() - self.init_time)), ":", arrayAverage(self.machine.resistance2History[-10:-1]))
          
        return self
    
class MoveCapturedState(State):
    ps1Raised = False 
    ps1PulledBack = False
    ps1Hovering = False
    ps1Lowering = False 
    ps1Returning = False
    initialPos1 = []
    initialPos2 = []

    def on_event(self, event):
        self.machine.saveImage = True
        
        if len(self.initialPos1) < 1:
            self.initialPos1 = self.wb.ps.getPos()
            self.newPos11 = [self.initialPos1[0] + 100, self.initialPos1[1] + 100, self.initialPos1[2]]
            self.newPos12 = [self.initialPos1[0], self.initialPos1[1] + 100, self.initialPos1[2]]
            self.newPos13 = [self.initialPos1[0] - 100, self.initialPos1[1], self.initialPos1[2]]
        if len(self.initialPos2) < 1:
            self.initialPos2 = self.wb.ps2.getPos()
            self.newPos21 = [self.initialPos2[0] + 100, self.initialPos2[1] + 100, self.initialPos2[2]]
            self.newPos22 = [self.initialPos2[0], self.initialPos2[1] + 100, self.initialPos2[2]]
            self.newPos23 = [self.initialPos2[0] - 100, self.initialPos2[1], self.initialPos2[2]]
        
        if not self.ps1Raised:
            if not self.wb.ps2.isMoving():
                self.wb.ps2.moveTo(self.newPos21, 10)
                self.ps1Raised = True
        elif not self.ps1PulledBack: 
            if not self.wb.ps2.isMoving():
                self.wb.ps2.moveTo(self.newPos22, 10)
                self.ps1PulledBack = True
        elif not self.ps1Hovering:
            if not self.wb.ps2.isMoving():
                self.wb.ps2.moveTo(self.newPos23, 10)
                self.ps1Hovering = True
        elif not self.ps1Lowering:
            if not self.wb.ps2.isMoving():
                self.ps1Lowering = True
        elif not self.ps1Returning:
            if not self.wb.ps2.isMoving():
                self.wb.ps2.moveTo(self.initialPos2, 10)
                self.ps1Returning = True
        elif self.ps1Returning and (not self.wb.ps.isMoving() and not self.wb.ps2.isMoving()):
            # Returned, move back to CaptureState
            return ReleaseState(self.wb, self.machine)
        return self
    
class ReleaseState(State):

    start_time = None

    def on_event(self, event):
        if self.start_time is None:
            self.start_time = time.perf_counter()
            
            self.wb.pressureController.writeMessageSwitch(b'atm 2')
            self.wb.pressureController.setPressure(300, 2)
            self.wb.pressureController.writeMessageSwitch(b'pressure 2')

        if time.perf_counter() - self.start_time > 5:
            self.wb.pressureController.writeMessageSwitch(b'atm 2')
            self.wb.pressureController.setPressure(0, 2)

            return CleanBothState(self.wb, self.machine)
        else:
            return self
    
class CleanBothState(State):
    ps1Raised = False 
    ps1PulledBack = False
    ps1Dropped = False
    ps1Hovering = False
    ps1MovingOver = False
    ps1Lowering = False 
    ps1Returning = False

    cleaned = False
    clean_start_time = None
    period_start_time = None
    cycles = 0

    pressure1_set = False
    pressure2_set = False

    initialPos1 = []
    initialPos2 = []

    # TODO: CALIBRATE LOCATIONS FOR CLEAN WITH THESE CONSTANTS:
    # LOCATIONS CAN BE FOUND IN LINLAB

    PS1_TOP_Z = 6000
    PS2_TOP_Z = 8000
    PS1_BATH_Z = -5500
    PS2_BATH_Z = -1500 
    PS1_CENTER_X = None # determined by get pos, -2372.0
    PS2_CENTER_X = None # determined by get pos, -5086.7
    PS1_CLEAN_X = 18000
    PS2_CLEAN_X = 11500

    def on_event(self, event):
        if len(self.initialPos1) < 1:
            print('fire')
            self.initialPos1 = self.wb.ps.getPos()
            self.PS1_CENTER_X = self.initialPos1[0]
        if len(self.initialPos2) < 1:
            self.initialPos2 = self.wb.ps2.getPos()
            self.PS2_CENTER_X = self.initialPos2[0]

        print(self.initialPos1)
        print(self.initialPos2)

        if not self.ps1Raised:
            self.wb.ps.moveTo([None, None, self.PS1_TOP_Z], 10000)
            self.wb.ps2.moveTo([None, None, self.PS2_TOP_Z], 10000)
            self.ps1Raised = True
        elif not self.ps1PulledBack: 
            if not self.wb.ps.isMoving() and not self.wb.ps2.isMoving():
                self.wb.ps.moveTo([self.PS1_CLEAN_X, None, None], 15000)
                self.wb.ps2.moveTo([self.PS2_CLEAN_X, None, None], 15000)
                self.ps1PulledBack = True
        elif not self.ps1Dropped:
            if not self.wb.ps.isMoving() and not self.wb.ps2.isMoving():    
                self.wb.ps.moveTo([None, None, self.PS1_BATH_Z], 10000)
                self.wb.ps2.moveTo([None, None, self.PS2_BATH_Z], 10000)
                self.ps1Dropped = True
        elif not self.cleaned: 
            if not self.wb.ps.isMoving() and not self.wb.ps2.isMoving():
                # Run clean step
                current_time = time.perf_counter()

                if self.clean_start_time is None:
                    self.clean_start_time = current_time
                    self.period_start_time = current_time
                    self.wb.pressureController.writeMessageSwitch(b"atm 1")
                    self.wb.pressureController.writeMessageSwitch(b"atm 2")
                    self.wb.pressureController.setPressure(500, 1)
                    self.wb.pressureController.setPressure(500, 2)
                    self.wb.pressureController.writeMessageSwitch(b"pressure 1")
                    self.wb.pressureController.writeMessageSwitch(b"pressure 2")
                elif self.cycles > 5:
                    self.cleaned = True
                    self.wb.pressureController.setPressure(200, 1)
                    self.wb.pressureController.setPressure(200, 2)
                    return self
                # Clean the pipette
                
                    # Pos pressure for 2 sec , negative for 1 sec, at +500mbar -500mbar
                if current_time - self.period_start_time >= 3:
                    if self.pressure2_set == False:
                        self.wb.pressureController.setPressure(500, 1)
                        self.wb.pressureController.setPressure(500, 2)
                        self.period_start_time = current_time
                        self.cycles += 1
                        self.pressure2_set = True
                        self.pressure1_set = False
                elif current_time - self.period_start_time >= 2:
                    if self.pressure1_set == False:
                        self.wb.pressureController.setPressure(-500, 1)
                        self.wb.pressureController.setPressure(-500, 2)
                        self.pressure1_set = True
                        self.pressure2_set = False
        elif not self.ps1Hovering:
            if not self.wb.ps.isMoving() and not self.wb.ps2.isMoving():
                self.wb.ps.moveTo([None, None, self.PS1_TOP_Z], 10000)
                self.wb.ps2.moveTo([None, None, self.PS2_TOP_Z], 10000)
                self.ps1Hovering = True
        elif not self.ps1MovingOver:
            if not self.wb.ps.isMoving() and not self.wb.ps2.isMoving():
                self.wb.ps.moveTo([self.PS1_CENTER_X, None, None], 15000)
                self.wb.ps2.moveTo([self.PS2_CENTER_X, None, None], 15000)
                self.ps1MovingOver = True
        elif not self.ps1Lowering:
            if not self.wb.ps.isMoving() and not self.wb.ps2.isMoving():
                self.wb.ps.moveTo(self.initialPos1, 5000)
                self.wb.ps2.moveTo(self.initialPos2, 5000)
                self.ps1Lowering = True
        elif not self.ps1Returning and (not self.wb.ps.isMoving() and not self.wb.ps2.isMoving()):
            return CaptureTestState(self.wb, self.machine)
        return self