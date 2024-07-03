from __future__ import print_function
import sys, os, time, logging

#logging.basicConfig(level=logging.DEBUG)

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from acq4.drivers.Scientifica import Scientifica
from acq4.devices.NiDAQ import NiDAQ
from acq4.drivers.nidaq.nidaq import NIDAQ as n
from acq4.devices.MultiClamp import MultiClamp
from acq4.devices.MicroManagerCamera import MicroManagerCamera
from acq4.devices.MicroManagerStage import MicroManagerStage
from acq4.drivers.PressureController.PressureController import PressureController

import acq4.util.ptime as ptime
from matplotlib import pyplot as plt
import numpy as np

class Workbench: 

    def __init__(self):
        # MANIPULATOR
        baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else None
        devname = "COM4"
        if devname.lower().startswith('com') or devname.startswith('/dev/'):
            self.ps = Scientifica(port=devname, baudrate=baudrate, ctrl_version=None)
            print(self.ps.getPort())
        else:
            self.ps = Scientifica(name=devname, baudrate=baudrate, ctrl_version=None)

        
        devname = "COM3"
        if devname.lower().startswith('com') or devname.startswith('/dev/'):
            print(devname)
            self.ps2 = Scientifica(port=devname, baudrate=baudrate, ctrl_version=None)
            print(self.ps2.getPort())
        else:
            self.ps2 = Scientifica(name=devname, baudrate=baudrate, ctrl_version=None)
        

        def printManipulatorSettings():
            print("Device type:  %s  Description:  %s" % (self.ps.getType(), self.ps.getDescription()))
            print("Firmware version: %r" % self.ps.getFirmwareVersion())
            print("Position: %r" % self.ps.getPos())
            print("Max speed: %r um/sec" % self.ps.getSpeed())
            if self.ps._version < 3:
                print("Min speed: %r um/sec" % (self.ps.getParam('minSpeed') / (2. * self.ps.getAxisScale(0))))
                print("Acceleration: %r um^2/sec" % (self.ps.getParam('accel') * 250. / self.ps.getAxisScale(0)))
            else:
                print("Min speed: %r um/sec" % self.ps.getParam('minSpeed'))
                print("Acceleration: %r um^2/sec" % self.ps.getParam('accel'))
        print("Configured PatchStar")

        # NATIONAL INSTRUMENTS DAQ
        self.daq = NiDAQ(None, 
                    {'defaultAIMode': 'NRSE', 'defaultAIRange': [-10, 10], 'defaultAORange': [-10, 10]}, 
                    "DAQ")

        def printDAQSettings():
            print("Assert num devs > 0:")
            assert len(n.listDevices()) > 0
            print("  OK")
            print("devices: %s" % n.listDevices())
            dev = n.listDevices()[0]

            print("\nAnalog Channels:")
            print("  AI: ", n.listAIChannels(dev))
            print("  AO: ", n.listAOChannels(dev))

            print("\nDigital ports:")
            print("  DI: ", n.listDIPorts(dev))
            print("  DO: ", n.listDOPorts(dev))

            print("\nDigital lines:")
            print("  DI: ", n.listDILines(dev))
            print("  DO: ", n.listDOLines(dev))

        # MULTICLAMP
        self.clamp = MultiClamp(None, {'channelID': 'model:MC700B,sn:00836613,chan:1',
            'commandChannel': {
                'device': 'DAQ',
                'channel': '/Dev1/ao0',
                'type': 'ao'},
            'primaryChannel': {
                'device': 'DAQ',
                'chsannel': '/Dev1/ai10',
                'mode': 'NRSE',
                'type': 'ai'},
            'secondaryChannel': {
                'device': 'DAQ',
                'channel': '/Dev1/ai9',
                'mode': 'NRSE',
                'type': 'ai'},
            #vcHolding: -65e-3
            'vcHolding': 0.0,
            'icHolding': 0.0}, 'Clamp1', self.daq)

        def printClampstateOptions():
            print("Clamp State Options: ", self.clamp.getState())

        printClampstateOptions()

        # HAMAMATSU ORCA CAMERA
        self.camera = MicroManagerCamera(None, {'mmAdapterName': 'HamamatsuHam',
            'mmDeviceName': 'HamamatsuHam_DCAM'}, 'Camera')

        print("Created Camera with sensor size ", self.camera.sensorSize)

        # PRIOR Z STAGE
        self.stage = MicroManagerStage(None, {
            'scale': [-1e-6, -1e-6, 1e-6],
                    
            'zStage':
                {'mmAdapterName': 'Prior',
                'mmDeviceName': 'ZStage',
                'serial':
                    {'port': 'COM6',
                    'baud': 9600}}
        }, 'Stage')

        print("Configured Stage")

        self.pressureController = PressureController([1, 2, 3, 4], ['COM8', 'COM9', 'COM10', 'COM11'])

        print("Created Pressure Controller")

    # All devices Configured
    def __del__(self):
        self.clamp.release()
        self.daq.release()
        self.camera.release()
        self.stage.release()
        self.ps.release()

    # Camera Functions 
    def displayFrames(frames, title=""):
        for frame in frames:
            plt.imshow(frame, interpolation='nearest')
            plt.title(title)
            plt.show()

    # Move Manipulator
    def moveManipulatorOnAxis(self, axis, val, speed, displayResults=False):
        pos1 = self.ps.getPos()
        pos2 = [None, None, None]
        pos2[axis] = pos1[axis] + val
        print("Move %s => %s" % (pos1, pos2))
        self.ps.moveTo(pos2, speed=speed)
        #i = 0
        if displayResults:
            while self.ps.isMoving():
                pos = self.ps.getPos()
                print("time: %s position: %s" % (time.time(), pos))
                time.sleep(0.01)
            #i += 1

    # Move Manipulator
    def moveManipulator2OnAxis(self, axis, val, speed, displayResults=False):
        pos1 = self.ps2.getPos()
        pos2 = [None, None, None]
        pos2[axis] = pos1[axis] + val
        print("Move %s => %s" % (pos1, pos2))
        self.ps2.moveTo(pos2, speed=speed)
        #i = 0
        if displayResults:
            while self.ps2.isMoving():
                pos = self.ps2.getPos()
                print("time: %s position: %s" % (time.time(), pos))
                time.sleep(0.01)
            #i += 1

    # Z Stage 
    def moveStage(self, microns, speed=None):
        METERS_TO_MICRONS = 1e-6
        currentStagePos = self.stage.getPosition()
        newStagePos = currentStagePos
        newStagePos[2] += microns * METERS_TO_MICRONS
        self.stage.move(newStagePos)

    # DAQ It, Precursor
    def finiteDAQReadTest():
        print("::::::::::::::::::  Analog Input Test  :::::::::::::::::::::")
        task = n.createTask()
        task.CreateAIVoltageChan("/Dev1/ai10", "", n.Val_RSE, -10.0, 10.0, n.Val_Volts, None)
        task.CreateAIVoltageChan("/Dev1/ai9", "", n.Val_Cfg_Default, -10.0, 10.0, n.Val_Volts, None)

        task.CfgSampClkTiming(None, 10000.0, n.Val_Rising, n.Val_FiniteSamps, 1000)
        task.start()
        data = task.read()
        task.stop()

        return data

    def contDAQReadTest():
        print("::::::::::::::::::  Continuous Read Test  :::::::::::::::::::::")
        task = n.createTask()
        task.CreateAIVoltageChan("/Dev1/ai10", "", n.Val_RSE, -10.0, 10.0, n.Val_Volts, None)
        #task.CreateAIVoltageChan("/Dev1/ai9", "", n.Val_Cfg_Default, -10.0, 10.0, n.Val_Volts, None)
        task.CfgSampClkTiming(None, 10000.0, n.Val_Rising, n.Val_ContSamps, 4000)
        task.start()
        t = ptime.time()
        for i in range(0, 10):
            data, size = task.read(1000)
            print("Cont read %d - %d samples, %fsec" % (i, size, ptime.time() - t))
            t = ptime.time()
        task.stop()

        return data

    # DAQ it
    def voltageClamp(self):
        print("Switching to VC on MC")
        self.clamp.setMode('VC')

    def currentClamp(self):
        print("Switching to CC on MC")
        self.clamp.setMode('CC')

    def setDAQOutput(self, val, hold=0.0):
        print("Changing ao0 to ", val, "V")
        self.daq.setChannelValue('/Dev1/ao0', val)
        time.sleep(hold)

    def plotPrimarySecondary(iterationData):
        x = np.arange(0, len(iterationData[0][0]), 1)
        plt.plot(x, iterationData[0][0])
        plt.plot(x, iterationData[0][1])
        plt.title("Primary, Secondary Output")
        plt.show()
    
    #**Arguments**
    #     ================ ================================================
    #     peak             amplitude of square wave, measured peak to baseline
    #     offset           DC offset applied to all points, peak or baseline, along square wave
    #     samples          number of samples to record
    #     ================ ================================================
    
    def syncAIO(self, peak, offset, samples):
        """Read *samples* number of samples from ai10 while writing a square wave with an amplitude *peak* and an offset *offset*, simultaneously.
        Parameters
        ------------
         peak : float
            amplitude of square wave, measured peak to baseline
         offset : float
            DC offset applied to all points, peak or baseline, along square wave
         samples : int
            number of samples to record
        
         """
        print("::::::::::::::::::  Sync DAQ Analog I/O  :::::::::::::::::::::")
        print("::::::::::: Square Wave Peak ", peak, " Offset ", offset, " for ", samples, "Samples :::::::::::")
        task1 = n.createTask()
        task1.CreateAIVoltageChan("/Dev1/ai10", "", n.Val_RSE, -10.0, 10.0, n.Val_Volts, None)
        task1.CreateAIVoltageChan("/Dev1/ai9", "", n.Val_Cfg_Default, -10.0, 10.0, n.Val_Volts, None)
        task1.CfgSampClkTiming("/Dev1/ao/SampleClock", 10000.0, n.Val_Rising, n.Val_FiniteSamps, samples)

        task2 = n.createTask()
        task2.CreateAOVoltageChan("/Dev1/ao0", "", -10.0, 10.0, n.Val_Volts, None)
        task2.CfgSampClkTiming(None, 10000.0, n.Val_Rising, n.Val_FiniteSamps, samples)

        data1 = np.zeros((samples), dtype=np.float64)
        data1[int(.1*samples):int(.2*samples)] = peak
        data1[int(.3*samples):int(.4*samples)] = peak
        data1[int(.5*samples):int(.6*samples)] = peak
        data1[int(.7*samples):int(.8*samples)] = peak
        data1[int(.9*samples):int(1*samples)] = peak
        data1 += offset
        print("  Wrote ao samples:", task2.write(data1))
        task1.start()
        task2.start()

        data2 = task1.read()
        task1.stop()
        task2.stop()

        print("  Data acquired:", data2[0].shape)
        return data1, data2
    
    CYCLES_PER_SECOND = 20000.0
    
    def configureTasks(self, recording_time):
        samples = int(recording_time * self.CYCLES_PER_SECOND)

        self.readingTask = n.createTask()
        self.readingTask.CreateAIVoltageChan("/Dev1/ai10", "", n.Val_RSE, -10.0, 10.0, n.Val_Volts, None)
        self.readingTask.CreateAIVoltageChan("/Dev1/ai9", "", n.Val_Cfg_Default, -10.0, 10.0, n.Val_Volts, None)
        self.readingTask.CfgSampClkTiming("/Dev1/ao/SampleClock", self.CYCLES_PER_SECOND, n.Val_Rising, n.Val_FiniteSamps, samples)

        self.writingTask = n.createTask()
        self.writingTask.CreateAOVoltageChan("/Dev1/ao0", "", -10.0, 10.0, n.Val_Volts, None)
        self.writingTask.CfgSampClkTiming(None, self.CYCLES_PER_SECOND, n.Val_Rising, n.Val_FiniteSamps, samples)

        self.readingTask.start()
        self.writingTask.start()

    def stopTasks(self):
        self.readingTask.stop()
        self.writingTask.stop()

    def sendOnePulse(self, peak, offset, frequency):
        period = 1 / frequency
        samples = int(period * self.CYCLES_PER_SECOND)

        data1 = np.zeros((samples), dtype=np.float64)
        data1[int(samples / 2):samples] = peak
        data1 += offset
        
        self.writingTask.write(data1)
        output = self.readingTask.read()

        return output
    
    def sendPulse(self, peak, offset, period):

        samples = int(period * self.CYCLES_PER_SECOND)

        task1 = n.createTask()
        task1.CreateAIVoltageChan("/Dev1/ai10", "", n.Val_RSE, -10.0, 10.0, n.Val_Volts, None)
        task1.CreateAIVoltageChan("/Dev1/ai9", "", n.Val_Cfg_Default, -10.0, 10.0, n.Val_Volts, None)
        task1.CfgSampClkTiming("/Dev1/ao/SampleClock", self.CYCLES_PER_SECOND, n.Val_Rising, n.Val_FiniteSamps, samples)

        task2 = n.createTask()
        task2.CreateAOVoltageChan("/Dev1/ao0", "", -10.0, 10.0, n.Val_Volts, None)
        task2.CfgSampClkTiming(None, self.CYCLES_PER_SECOND, n.Val_Rising, n.Val_FiniteSamps, samples)

        data1 = np.zeros((samples), dtype=np.float64)

        data1[int(samples / 4 - 1):int(samples * 3 / 4 -1)] = peak
        data1 += offset

        task2.write(data1)
        task1.start()
        task2.start()

        data2 = task1.read()
        task1.stop()
        task2.stop()

        return data1, data2
    
    def calculateResistance(self, voltage_sent, current_read, periods_in_data):
        samples = len(current_read)
        sample_per_iter = int(samples / periods_in_data)
        resistances = []
        # Look 18% and 28% of the way thru
        for i in range(periods_in_data): # five periods, change this later
            voltage_high =  arrayAverage(voltage_sent[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.8 * sample_per_iter):int(0.9 * sample_per_iter)])
            voltage_low  =  arrayAverage(voltage_sent[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.3 * sample_per_iter):int(0.4 * sample_per_iter)])
            current_high =  arrayAverage(current_read[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.8 * sample_per_iter):int(0.9 * sample_per_iter)])
            current_low  =  arrayAverage(current_read[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.3 * sample_per_iter):int(0.4 * sample_per_iter)])

            resistance = (voltage_high - voltage_low) / (current_high - current_low)
            resistances.append(abs(resistance))
        
        return resistances
    
    def configureVoltageClamp(self):
        self.voltageClamp()
        self.clamp.setParam('PrimarySignal', 'SIGNAL_VC_MEMBCURRENT')
        self.clamp.setParam('SecondarySignal', 'SIGNAL_VC_MEMBPOTENTIAL')

    def configureCurrentClamp(self):
        self.currentClamp()
        self.clamp.setParam('PrimarySignal', 'SIGNAL_IC_MEMBCURRENT')
        self.clamp.setParam('SecondarySignal', 'SIGNAL_IC_MEMBPOTENTIAL')

    def measureResistance(self, frequency):
        period = 1 / frequency

        _, voltage_data = self.sendPulse(1, 1, period)
        
        voltage_sent = voltage_data[0][1]
        voltage_read = voltage_data[0][0]

        voltage_sent = voltage_sent * self.clamp.getState()['secondaryScaleFactor']
        current_read = voltage_read * self.clamp.getState()['primaryScaleFactor']

        resistances = self.calculateResistance(voltage_sent, current_read, 1)
    
        return [resistance / 1e6 for resistance in resistances]
        
    def measureTransient(self, frequency):
        period = 1 / frequency

        _, voltage_data = self.sendPulse(1, 1, period)
        
        voltage_sent = voltage_data[0][1]
        voltage_read = voltage_data[0][0]

        voltage_sent = voltage_sent * self.clamp.getState()['secondaryScaleFactor']
        current_read = voltage_read * self.clamp.getState()['primaryScaleFactor']

        #transient_present = self.currentTransient(current_read, 1)
        periods_in_data = 1
        samples = len(current_read)
        sample_per_iter = int(samples / periods_in_data)
        # Look 18% and 28% of the way thru
        for i in range(periods_in_data): # five periods, change this later
            current_high = arrayAverage(current_read[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.8 * sample_per_iter):int(0.9 * sample_per_iter)])
            current_low  = arrayAverage(current_read[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.3 * sample_per_iter):int(0.4 * sample_per_iter)])

            if abs((max(current_read) - min(current_read)) / (current_high - current_low)) > 2 and (max(current_read) - current_high > 1e-9):
                return True
        
        return False
        

def arrayAverage(arr):
    return sum(arr) / len(arr)