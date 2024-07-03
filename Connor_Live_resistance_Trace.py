from Workbench import *
import threading
import queue
from matplotlib.animation import FuncAnimation
from scipy.integrate import quad

workbench = Workbench()

def streamSmartSquareWave():
    duration = 10
    workbench.voltageClamp()
    workbench.configureTasks(duration)    

    # 10 Hz, how many cycles? 1 / 10 Hz -> 0.1 seconds. In 10 seconds, 100 pulses. 
    frequency = 10
    period = 1 / frequency 
    periods_in_duration = duration / period
    for i in range(int(periods_in_duration)):
        voltage_data = workbench.sendOnePulse(1, 1, duration)

        voltage_sent = voltage_data[0][1]
        voltage_read = voltage_data[0][0]

        voltage_sent = voltage_sent * workbench.clamp.getState()['secondaryScaleFactor']
        current_read = voltage_read * workbench.clamp.getState()['primaryScaleFactor']

        print(voltage_sent, current_read)

    workbench.stopTasks()

def calculateResistance(voltage_sent, current_read, periods_in_data):
    samples = len(current_read)
    sample_per_iter = int(samples / periods_in_data)
    resistances = []
    transient_present = False
    # Look 18% and 28% of the way thru
    for i in range(periods_in_data): # five periods, change this later
        voltage_high = arrayAverage(voltage_sent[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.8 * sample_per_iter):int(0.9 * sample_per_iter)])
        voltage_low  = arrayAverage(voltage_sent[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.3 * sample_per_iter):int(0.4 * sample_per_iter)])
        current_high = arrayAverage(current_read[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.8 * sample_per_iter):int(0.9 * sample_per_iter)])
        current_low  = arrayAverage(current_read[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.3 * sample_per_iter):int(0.4 * sample_per_iter)])

        if abs((max(current_read) - min(current_read)) / (current_high - current_low)) > 2 and (max(current_read) - current_high > 1e-9):
            transient_present = True

        resistance = (voltage_high - voltage_low) / (current_high - current_low)
        resistances.append(abs(resistance))

    return resistances, transient_present

def calculateCapacitance(voltage_sent, current_read, periods_in_data):
    samples = len(current_read)
    sample_per_iter = int(samples / periods_in_data)
    capacitances = []
    # Look 18% and 28% of the way thru
    for i in range(periods_in_data): # five periods, change this later
        current_read_period = current_read[i*sample_per_iter:(i+1)*sample_per_iter-1]
        max_current_idx = current_read_period.argmax(axis=0)
        spike = current_read_period[max_current_idx-5:max_current_idx+10]
        print(spike[0], spike[-1])

        voltage_high = voltage_sent[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.9 * sample_per_iter)]
        voltage_low =  voltage_sent[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.4 * sample_per_iter)]
        current_high = current_read[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.9 * sample_per_iter)]
        current_low =  current_read[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.4 * sample_per_iter)]

        resistance = (voltage_high - voltage_low) / (current_high - current_low)
        #resistances.append(abs(resistance))

    #return resistances

def streamPulses2():
    frequency = 60
    duration = 60
    period = 1 / frequency
    periods_in_duration = duration / period

    workbench.voltageClamp()
    workbench.clamp.setParam('PrimarySignal', 'SIGNAL_VC_MEMBCURRENT')
    workbench.clamp.setParam('SecondarySignal', 'SIGNAL_VC_MEMBPOTENTIAL')

    print("Configured!")
    periods_in_duration = duration / period

    data_queue = queue.Queue()
    stop_event = threading.Event()

    acquisition_thread = threading.Thread(target=acquireData2, args=(data_queue, periods_in_duration, period, stop_event))
    acquisition_thread.start()

    fig, ax = plt.subplots(2, 1)
    x = np.zeros(1)

    voltageTraceLines = []
    currentTraceLines = []
    for i in range(5):
        voltageTLine, = ax[0].plot(x, np.zeros(1), color='gray')
        voltageTraceLines.append(voltageTLine)
    line1, = ax[0].plot(x, np.zeros(1))
    for i in range(5):
        currentTLine, = ax[1].plot(x, np.zeros(1), color='gray')
        currentTraceLines.append(currentTLine)
    line2, = ax[1].plot(x, np.zeros(1))
   
    ax[0].set_xlim([-20, 400])
    ax[0].set_ylim([-0.01, 0.05])
    ax[1].set_xlim([-20, 400])
    ax[1].set_ylim([-1E-9, 5e-9])

    animation = FuncAnimation(fig, update_plot2, fargs=(data_queue, line1, line2, voltageTraceLines, currentTraceLines), interval=1000/60)

    plt.show()

    stop_event.set()
    acquisition_thread.join()
    
def update_plot2(frame, data_queue, line1, line2, voltageTraceLines, currentTraceLines):
    try:
        while not data_queue.empty():
            voltage, current, voltageTrace, currentTrace = data_queue.get_nowait()
            line1.set_xdata(np.arange(len(voltage)))
            line1.set_ydata(voltage)
            line2.set_xdata(np.arange(len(current)))
            line2.set_ydata(current)
            if len(voltageTrace) >= 5:
                for i in range(5):
                    voltageTraceLines[i].set_xdata(np.arange(len(voltageTrace[i])))
                    voltageTraceLines[i].set_ydata(voltageTrace[i])
                    currentTraceLines[i].set_xdata(np.arange(len(currentTrace[i])))
                    currentTraceLines[i].set_ydata(currentTrace[i])
    except queue.Empty:
        pass

    return line1, line2, voltageTraceLines, currentTraceLines

def acquireData2(data_queue, periods_in_duration, period, stop_recording):
    #for i in range(int(periods_in_duration)):
    voltageTrace = []
    currentTrace = []
    
    while not stop_recording.is_set():
        _, voltage_data = workbench.sendPulse(1, 1, period)
        #print(voltage_data)
        voltage_sent = voltage_data[0][1]
        voltage_read = voltage_data[0][0]

        voltage_sent = voltage_sent * workbench.clamp.getState()['secondaryScaleFactor']
        current_read = voltage_read * workbench.clamp.getState()['primaryScaleFactor']

        if len(voltageTrace) >= 11:
            voltageTrace = voltageTrace[-10:-1]
        if len(currentTrace) >= 11:
            currentTrace = currentTrace[-10:-1]

        voltageTrace.append(voltage_sent)
        currentTrace.append(current_read)

        resistances, transient_present = calculateResistance(voltage_sent, current_read, 1)
        print("Resistances 2: ", round(resistances[0] / 1e6, 2), transient_present)
        #calculateCapacitance(voltage_sent, current_read, 1)

        data_queue.put((voltage_sent, current_read, voltageTrace, currentTrace))

def updateFigure(fig, lines, newDataArr):
    for i in range(len(lines)):
        lines[i].set_ydata(newDataArr[i])
    fig.canvas.draw()
    fig.canvas.flush_events()

streamPulses2()