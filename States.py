from Workbench import Workbench, arrayAverage
from Machine import Machine
import time
import datetime
import os

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
        self.machine.saveImage = True

        if self.init_time is None:
            self.init_time = time.perf_counter()

        if not self.configured: 
            #self.wb.pressureController.setAtmosphereMode(1)
            self.wb.pressureController.setPressure(400, self.wb.pressureController.CAPTURE_PRESSURE_ID)
            self.wb.pressureController.setPressureMode(self.wb.pressureController.CAPTURE_PRESSURE_ID)
            self.configured = True

            return self
        
        if time.perf_counter() - self.init_time > 12:
            return MoveCapturedState(self.wb, self.machine)
            
        elif time.perf_counter() - self.init_time > 5:
            if not self.suction:
                self.wb.pressureController.setPressure(-30, self.wb.pressureController.CAPTURE_PRESSURE_ID)
                self.suction = True

                return self
            else:
                print("Resistance Average at Time ",  str(round(time.perf_counter() - self.init_time)), ":", arrayAverage(self.machine.resistanceCaptureHistory[-10:-1]))
        
        else:
            print("Resistance Average at Time ",  str(round(time.perf_counter() - self.init_time)), ":", arrayAverage(self.machine.resistanceCaptureHistory[-10:-1]))
          
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
            self.initialPos1 = self.wb.patchManipulator.getPos()
            self.newPos11 = [self.initialPos1[0] + 100, self.initialPos1[1] + 100, self.initialPos1[2]]
            self.newPos12 = [self.initialPos1[0], self.initialPos1[1] + 100, self.initialPos1[2]]
            self.newPos13 = [self.initialPos1[0] - 100, self.initialPos1[1], self.initialPos1[2]]
        if len(self.initialPos2) < 1:
            self.initialPos2 = self.wb.captureManipulator.getPos()
            self.newPos21 = [self.initialPos2[0] + 100, self.initialPos2[1] + 100, self.initialPos2[2]]
            self.newPos22 = [self.initialPos2[0], self.initialPos2[1] + 100, self.initialPos2[2]]
            self.newPos23 = [self.initialPos2[0] - 100, self.initialPos2[1], self.initialPos2[2]]
        
        if not self.ps1Raised:
            if not self.wb.captureManipulator.isMoving():
                self.wb.captureManipulator.moveTo(self.newPos21, 10)
                self.ps1Raised = True
        elif not self.ps1PulledBack: 
            if not self.wb.captureManipulator.isMoving():
                self.wb.captureManipulator.moveTo(self.newPos22, 10)
                self.ps1PulledBack = True
        elif not self.ps1Hovering:
            if not self.wb.captureManipulator.isMoving():
                self.wb.captureManipulator.moveTo(self.newPos23, 10)
                self.ps1Hovering = True
        elif not self.ps1Lowering:
            if not self.wb.captureManipulator.isMoving():
                self.ps1Lowering = True
        elif not self.ps1Returning:
            if not self.wb.captureManipulator.isMoving():
                self.wb.captureManipulator.moveTo(self.initialPos2, 10)
                self.ps1Returning = True
        elif self.ps1Returning and (not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving()):
            # Returned, move back to CaptureState
            return ReleaseState(self.wb, self.machine)
        return self
    
class HuntState(State):
    baselineResistance = None
    configured = False
    totalZMovement = 0 
    countBetweenStateRuns = 0

    def on_event(self, event):

        if not self.configured:
            self.wb.patchAmplifier.autoPipetteOffset()
            self.configured = True
            return self

        resistances = self.machine.resistancePatchHistory
        resistance = arrayAverage(resistances[-10:-1])

        if self.baselineResistance is None and self.countBetweenStateRuns > 10: 
            self.baselineResistance = resistance
        elif self.baselineResistance is not None: 
            if resistance < 0.8 * self.baselineResistance:
                self.wb.patchManipulator.stop()
                return AbortState(self.wb, self.machine)
            elif resistance > 1.1 * self.baselineResistance:
                self.wb.patchManipulator.stop()
                return SealState(self.wb, self.machine)
            elif self.totalZMovement > 50:
                self.wb.patchManipulator.stop()
                return CleanBothState(self.wb, self.machine)
            elif not self.wb.patchManipulator.isMoving() and self.countBetweenStateRuns > 10:
                self.wb.moveManipulatorOnAxis(2, -1, 100, False)
                self.totalZMovement += 1
                self.countBetweenStateRuns = 0

        print(resistance)
        self.countBetweenStateRuns += 1

        return self
    
class SealState(State):
    init_time = None
    configured = False
    suction = False

    def on_event(self, event):
        if not self.configured: 
            self.configure()

            return self
        
        resistances = self.machine.resistancePatchHistory
        resistance = arrayAverage(resistances[-10:-1])
        
        if resistance > 1000: 
            return BreakInState(self.wb, self.machine)
        
        if not self.suction and time.perf_counter() - self.init_time > 5:
            self.wb.pressureController.setPressureMode(self.wb.pressureController.PATCH_PRESSURE_ID)
            self.suction = True
            self.init_time = time.perf_counter() # restart timer

            return self
                
        if self.suction and time.perf_counter() - self.init_time > 20:
            return CleanBothState(self.wb, self.machine)

        return self
    
    def configure(self): 
        self.init_time = time.perf_counter()
        self.wb.pressureController.setAtmosphereMode(2)
        self.wb.pressureController.setPressure(-15, self.wb.pressureController.PATCH_PRESSURE_ID)
        self.wb.patchAmplifier.setHolding(None, -70e-3)
        self.wb.captureAmplifier.setHolding(None, 0)
        self.configured = True
    
class BreakInState(State):
    
    configured = False
    init_time = None
    breakin_time_ms = 50
    BREAKIN_INCREMENT = 50
    attempts = 0

    def on_event(self, event):

        if not self.configured:
            self.init_time = time.perf_counter()
            self.wb.pressureController.setAtmosphereMode(self.wb.pressureController.PATCH_PRESSURE_ID)
            self.wb.pressureController.setPressure(-600, self.wb.pressureController.PATCH_PRESSURE_ID)
            self.wb.patchAmplifier.autoCapComp()
            self.configured = True

            return self

        if time.perf_counter - self.init_time > 1:
           
            self.wb.pressureController.doBreakIn(self.wb.pressureController.PATCH_PRESSURE_ID, self.breakin_time_ms)
            self.breakin_time_ms += self.BREAKIN_INCREMENT
            self.init_time = time.perf_counter()
            
            #resistances = self.machine.resistanceHistory
            transient_present = self.machine.transientPatchHistory[-1]

            # Measure transient!
            if transient_present:
                return MeasuringRestingPotentialState(self.wb, self.machine)
            elif self.attempts > 10:
                return CleanBothState(self.wb, self.machine)
            
            self.attempts += 1

        return self
    
class MeasuringRestingPotentialState(State):

    counter = 0
    configured = False

    def on_event(self, event):
        if not self.configured:
            self.configure() 
            
            return self
                
        self.machine.saveImage = True 

        voltage_patch = self.machine.voltage_patch
        current_patch = self.machine.current_patch

        for i in range(len(voltage_patch)):
            self.voltageFile.write(str(round(voltage_patch[i] * 1e3, 4)) + ',' +  str(round(current_patch[i] * 1e12, 4)) + '\n')

        if self.counter >= 9:
            self.voltageFile.close()
            return MeasuringdFOverF(self.wb, self.machine)
        else:
            self.counter += 1

        return self
    
    def configure(self):
        patchPipetteOffset = self.wb.patchAmplifier.getParam('PipetteOffset')
        capturePipetteOffset = self.wb.captureAmplifier.getParam('PipetteOffset')
        self.machine.stopAcquiringData()

        self.wb.currentClamp(1)
        self.wb.currentClamp(2)
        self.wb.patchAmplifier.setParam('PipetteOffset', patchPipetteOffset)
        self.wb.captureAmplifier.setParam('PipetteOffset', capturePipetteOffset)

        self.machine.readCurrentPulses()

        self.wb.lightsOn()

        cellDir = self.machine.experimentDir + "Cell_" + str(len(next(os.walk('dir_name'))[1]) - 1) + "/"
        if not os.path.exists(cellDir):
            os.makedirs(cellDir)
            self.machine.wholeCellDir = cellDir
        
        voltageFilePath = cellDir + 'RestingMembranePotential.txt'
        self.voltageFile = open(voltageFilePath, 'w')

        self.configured = True

class MeasuringdFOverF(State):

    counter = 0
    configured = False
    holdingValues = [-70e-3, -70e-3, -110e-3, -70e-3, -90e-3, -70e-3, -70e-3, -50e-3, -70e-3, -30e-3, 
                     -70e-3, -10e-3, -70e-3, 0e-3, -70e-3, 10e-3, -70e-3, 30e-3, -70e-3, 50e-3, -70e-3]
    currentHoldingValueIdx = 0

    def on_event(self, event):
        if not self.configured:
            self.configure() 
            
            return self
                
        self.machine.saveImage = True

        voltage_patch = self.machine.voltage_patch
        current_patch = self.machine.current_patch

        for i in range(len(voltage_patch)):
            self.voltageFile.write(str(round(voltage_patch[i] * 1e3, 4)) + ',' +  
                                   str(round(current_patch[i] * 1e12, 4 + ',' + str(round(self.holdingValues[self.currentHoldingValueIdx]), 4))) + '\n')

        self.counter += 1

        if self.counter >= 3:
            if self.currentHoldingValueIdx == len(self.holdingValues) - 1:
                self.voltageFile.close()
                self.machine.stopAcquiringData()
                self.machine.streamVoltagePulses()
                return ReleaseState(self.wb, self.machine)
            else:
                self.currentHoldingValueIdx += 1
                self.wb.patchAmplifier.setParam('Holding', self.holdingValues[self.currentHoldingValueIdx])
                self.counter = 0
            
        return self
    
    def configure(self):
        self.machine.stopAcquiringData()
        
        self.wb.voltageClamp(1)
        self.wb.voltageClamp(2)

        self.wb.patchAmplifier.setParam('Holding', -70e-3)
        self.wb.captureAmplifier.setParam('Holding', 0)

        self.machine.readVoltagePulses()

        self.wb.lightsOn()

        cellDir = self.machine.wholeCellDir
        
        voltageFilePath = cellDir + 'dfOverFVoltageClamp.csv'
        self.voltageFile = open(voltageFilePath, 'w')

        self.configured = True

class ReleaseState(State):

    start_time = None

    def on_event(self, event):
        if self.start_time is None:
            self.start_time = time.perf_counter()
            self.wb.moveManipulator2OnAxis(0, -20, 10, False)
            self.wb.moveManipulatorOnAxis(0, -20, 10, False)
            self.wb.pressureController.setAtmosphereMode(self.wb.pressureController.CAPTURE_PRESSURE_ID)
            self.wb.pressureController.setPressure(300, self.wb.pressureController.CAPTURE_PRESSURE_ID)
            self.wb.pressureController.setPressureMode(self.wb.pressureController.CAPTURE_PRESSURE_ID)
            self.wb.pressureController.setAtmosphereMode(self.wb.pressureController.PATCH_PRESSURE_ID)
            self.wb.pressureController.setPressure(300, self.wb.pressureController.PATCH_PRESSURE_ID)
            self.wb.pressureController.setPressureMode(self.wb.pressureController.PATCH_PRESSURE_ID)

        if time.perf_counter() - self.start_time > 5:
            return CleanBothState(self.wb, self.machine)
        
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
            self.initialPos1 = self.wb.patchManipulator.getPos()
            self.PS1_CENTER_X = self.initialPos1[0]
        if len(self.initialPos2) < 1:
            self.initialPos2 = self.wb.captureManipulator.getPos()
            self.PS2_CENTER_X = self.initialPos2[0]

        print(self.initialPos1)
        print(self.initialPos2)
        # TODO: INITIAL POS IN MACHINE
        if not self.ps1Raised:
            self.wb.pressureController.setPressure(200, self.wb.pressureController.PATCH_PRESSURE_ID)
            self.wb.pressureController.setPressure(200, self.wb.pressureController.CAPTURE_PRESSURE_ID)
            self.wb.pressureController.setPressureMode(self.wb.pressureController.CAPTURE_PRESSURE_ID)
            self.wb.pressureController.setPressureMode(self.wb.pressureController.PATCH_PRESSURE_ID)

            self.wb.patchManipulator.moveTo([None, None, self.PS1_TOP_Z], 10000)
            self.wb.captureManipulator.moveTo([None, None, self.PS2_TOP_Z], 10000)
            self.ps1Raised = True
        elif not self.ps1PulledBack: 
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                self.wb.patchManipulator.moveTo([self.PS1_CLEAN_X, None, None], 15000)
                self.wb.captureManipulator.moveTo([self.PS2_CLEAN_X, None, None], 15000)
                self.ps1PulledBack = True
        elif not self.ps1Dropped:
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():    
                self.wb.patchManipulator.moveTo([None, None, self.PS1_BATH_Z], 10000)
                self.wb.captureManipulator.moveTo([None, None, self.PS2_BATH_Z], 10000)
                self.ps1Dropped = True
        elif not self.cleaned: 
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                # Run clean step
                current_time = time.perf_counter()

                if self.clean_start_time is None:
                    self.clean_start_time = current_time
                    self.period_start_time = current_time
                    self.wb.pressureController.setAtmosphereMode(self.wb.pressureController.CAPTURE_PRESSURE_ID)
                    self.wb.pressureController.setAtmosphereMode(self.wb.pressureController.PATCH_PRESSURE_ID)
                    self.wb.pressureController.setPressure(500, self.wb.pressureController.CAPTURE_PRESSURE_ID)
                    self.wb.pressureController.setPressure(500, self.wb.pressureController.PATCH_PRESSURE_ID)
                    self.wb.pressureController.setPressureMode(self.wb.pressureController.CAPTURE_PRESSURE_ID)
                    self.wb.pressureController.setPressureMode(self.wb.pressureController.PATCH_PRESSURE_ID)
                elif self.cycles > 5:
                    self.cleaned = True
                    self.wb.pressureController.setPressure(200, self.wb.pressureController.CAPTURE_PRESSURE_ID)
                    self.wb.pressureController.setPressure(200, self.wb.pressureController.PATCH_PRESSURE_ID)
                    return self
                # Clean the pipette
                
                    # Pos pressure for 2 sec , negative for 1 sec, at +500mbar -500mbar
                if current_time - self.period_start_time >= 3:
                    if self.pressure2_set == False:
                        self.wb.pressureController.setPressure(500, self.wb.pressureController.CAPTURE_PRESSURE_ID)
                        self.wb.pressureController.setPressure(500, self.wb.pressureController.PATCH_PRESSURE_ID)
                        self.period_start_time = current_time
                        self.cycles += 1
                        self.pressure2_set = True
                        self.pressure1_set = False
                elif current_time - self.period_start_time >= 2:
                    if self.pressure1_set == False:
                        self.wb.pressureController.setPressure(-500, self.wb.pressureController.CAPTURE_PRESSURE_ID)
                        self.wb.pressureController.setPressure(-500, self.wb.pressureController.PATCH_PRESSURE_ID)
                        self.pressure1_set = True
                        self.pressure2_set = False
        elif not self.ps1Hovering:
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                self.wb.patchManipulator.moveTo([None, None, self.PS1_TOP_Z], 10000)
                self.wb.captureManipulator.moveTo([None, None, self.PS2_TOP_Z], 10000)
                self.ps1Hovering = True
        elif not self.ps1MovingOver:
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                self.wb.patchManipulator.moveTo([self.PS1_CENTER_X, None, None], 15000)
                self.wb.captureManipulator.moveTo([self.PS2_CENTER_X, None, None], 15000)
                self.ps1MovingOver = True
        elif not self.ps1Lowering:
            if not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving():
                self.wb.patchManipulator.moveTo(self.initialPos1, 5000)
                self.wb.captureManipulator.moveTo(self.initialPos2, 5000)
                self.ps1Lowering = True
        elif not self.ps1Returning and (not self.wb.patchManipulator.isMoving() and not self.wb.captureManipulator.isMoving()):
            return CaptureState(self.wb, self.machine)
        return self
    
class AbortState(State):
    def on_event(self, event):
        self.machine.__del__()
        self.wb.__del__()

        return None