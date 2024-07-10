from Workbench import Workbench, arrayAverage
import time
import datetime
import threading
import queue
import numpy as np

from matplotlib.animation import FuncAnimation
from matplotlib import pyplot as plt

import nest_asyncio
nest_asyncio.apply()

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
        data_queue = event
        resistances = data_queue.get_nowait()[4]

        if self.baselineResistance is None or self.counter < 10: 
            #self.file.write(datetime.datetime.now().isoformat(' ') + ' ' + self.__str__() + ' ' + str(round(arrayAverage(resistances), 2)) + '\n')
            self.baselineResistance = sum(resistances[-10:-1]) / len(resistances[-10:-1])  
            self.counter += 1    
        else:
            self.wb.moveManipulatorOnAxis(2, -2, 1, True)
            self.totalZMovement += 2
            newResistance = resistances[-1]
            print(newResistance)
            
            if newResistance < 0.01 * self.baselineResistance:
                print("Abort!")
                #self.file.close()
                return AbortState(self.wb)
            elif newResistance > 1.3 * self.baselineResistance:
                print("Seal")
                #self.file.close()
                raise ValueError("something")
                return SealState(self.wb)
            elif self.totalZMovement > 100:
                #self.file.close()
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
        
        data_queue = event
        resistances = data_queue.get_nowait()[4]
        
        if time.perf_counter() - self.init_time > 2:
            if not self.suction:
                #self.wb.pressureController.setPressure(-15, 1)
                #self.wb.pressureController.writeMessageSwitch("pressure 1")
                self.suction = True
                self.init_time = time.perf_counter() # restart timer

                return self
            else: 
                newResistance = resistances[-1]
                #self.file.write(datetime.datetime.now().isoformat(' ') + ' ' + self.__str__() + ' ' + str(round(arrayAverage(newResistance), 2)) + '\n')
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
            #newResistance = self.wb.measureResistance(60)
            
            #transient_present = self.wb.measureTransient(60)
            newResistance = event[4][-1]
            transient_present = event[5][-1]

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
        self.file = open('resistance.txt', 'w')
        self.file.write('Experiment commencing at ' + datetime.datetime.now().isoformat() +'\n')
        self.file.close()
        self.data_queue = None
        self.file = open('resistance.txt', 'a')
        # Start with a default state.
       
        self.state = CaptureState(self.wb)
        self.data_queue = queue.Queue(100)
        self.streamPulses()
        self.on_event('configure_capture')

    def __del__(self):
        self.file.close()
        self.stop_event.set()
        self.acquisition_thread.join()
        #self.plot_thread.join()

    def initVoltClamp(self):
        self.wb.voltageClamp()
        self.wb.clamp.setParam('PrimarySignal', 'SIGNAL_VC_MEMBCURRENT')
        self.wb.clamp.setParam('SecondarySignal', 'SIGNAL_VC_MEMBPOTENTIAL')

    def on_event(self, event):
        """
        This is the bread and butter of the state machine. Incoming events are
        delegated to the given states which then handle the event. The result is
        then assigned as the new state.
        """

        # The next state will be the result of the on_event function.
        if self.data_queue is not None:
            self.state = self.state.on_event(self.data_queue)
        else:
            self.state = self.state.on_event(event)

    def streamPulses(self):
        frequency = 60
        period = 1 / frequency

        self.wb.voltageClamp()
        self.wb.clamp.setParam('PrimarySignal', 'SIGNAL_VC_MEMBCURRENT')
        self.wb.clamp.setParam('SecondarySignal', 'SIGNAL_VC_MEMBPOTENTIAL')

        print("Configured background recording!")

        self.stop_event = threading.Event()

        self.acquisition_thread = threading.Thread(target=self.acquireData, args=(self.data_queue, period, self.stop_event))
        self.acquisition_thread.start()

        fig, self.ax = plt.subplots(3, 1)
        x = np.zeros(1)
        self.voltage = [0 for _ in range(350)]
        self.current = [0 for _ in range(350)]
        self.resistanceHistory = [0 for _ in range(1000)]
        self.transientHistory = [0 for _ in range(1000)]
        self.dates = [0 for _ in range(1000)]

        self.line1, = self.ax[0].plot(x, np.zeros(1))
        self.line2, = self.ax[1].plot(x, np.zeros(1))
        self.line3, = self.ax[2].plot(np.zeros(1000), np.zeros(1000))
    
        self.ax[0].set_xlim([-20, 400])
        self.ax[0].set_ylim([-0.01, 0.05])
        self.ax[1].set_xlim([-20, 400])
        self.ax[1].set_ylim([-1E-9, 5e-9])
        self.ax[2].set_xlim([-10, 101])
        self.ax[2].set_ylim([-10, 3000])

        plt.show(block=False)

    # DATAQUEUE:
    # voltage_sent: Voltage reading of last pulse
    # current_read: Current reading of last pulse
    # voltageTrace: Array of last 10 voltage_sent
    # currentTrace: Array of last 10 current_sent
    # resistanceHistory: Array of last 1000 resistances
    # dates: Last 100 timestamps. Each maps to resistance measurement: last 10 to traces, last one to current measurement

    def acquireData(self, data_queue, period, stop_recording):
        while not stop_recording.is_set():
            _, voltage_data = self.wb.sendPulse(1, 1, period)

            voltage_sent = voltage_data[0][1]
            voltage_read = voltage_data[0][0]

            voltage_sent = voltage_sent * self.wb.clamp.getState()['secondaryScaleFactor']
            current_read = voltage_read * self.wb.clamp.getState()['primaryScaleFactor']
            
            resistances, transient_present = self.wb.calculateResistance(voltage_sent, current_read, 1)
            megasurement = resistances[0] / 1e6
            date = datetime.datetime.now()
            data_queue.put((voltage_sent, current_read, megasurement, transient_present, date))
          
    def updatePlotIndependent(self):
        if not self.data_queue.empty():
            print(self.data_queue.qsize())
            while not self.data_queue.empty():
                self.voltage, self.current, resistance, transientPresent, date = self.data_queue.get_nowait()
                print(self.data_queue.qsize())
                
                if len(self.resistanceHistory) >= 100:
                    self.resistanceHistory = self.resistanceHistory[-99:-1]
                if len(self.dates) >= 100:
                    self.dates = self.dates[-99:-1]
                if len(self.transientHistory) >= 100:
                    self.transientHistory = self.transientHistory[-99:-1]

                self.resistanceHistory.append(resistance)
                self.dates.append(date)
                self.transientHistory.append(transientPresent)

            self.line1.set_xdata(np.arange(len(self.voltage)))
            self.line1.set_ydata(self.voltage)
            self.line2.set_xdata(np.arange(len(self.current)))
            self.line2.set_ydata(self.current)

            self.line3.set_xdata(np.arange(len(self.resistanceHistory)))
            self.line3.set_ydata(self.resistanceHistory)

            self.ax[0].set_title(self.dates[-1].isoformat(' '))

            if self.transientHistory[-1]:
                self.line3.set_color('green')
            else:
                self.line3.set_color('red')
            
            plt.pause(0.001)
        else:
            pass

machine = SimpleDevice()

try:
    while True:
        machine.on_event('')
        machine.updatePlotIndependent()
        print(machine.state)
except KeyboardInterrupt:
    machine.wb.__del__()
    raise("Ctrl- C, Terminating")
# Every state returns the next state
# While loop runs outside state machine
# Has resistance increased by 10% Pull bath test out, will cause resistance to increase and call transition.