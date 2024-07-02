from Workbench import *
import threading
import queue
from matplotlib.animation import FuncAnimation

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
    # Look 18% and 28% of the way thru
    for i in range(periods_in_data): # five periods, change this later
        voltage_high = voltage_sent[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.9 * sample_per_iter)]
        voltage_low =  voltage_sent[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.4 * sample_per_iter)]
        current_high = current_read[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.9 * sample_per_iter)]
        current_low =  current_read[i*sample_per_iter:(i+1)*sample_per_iter-1][int(0.4 * sample_per_iter)]

        resistance = (voltage_high - voltage_low) / (current_high - current_low)
        resistances.append(abs(resistance))

    return resistances

def streamPulses2():
    frequency = 60
    duration = 60
    period = 1 / frequency
    periods_in_duration = duration / period

    workbench.voltageClamp()
    workbench.clamp.setParam('PrimarySignal', 'SIGNAL_VC_MEMBCURRENT')
    workbench.clamp.setParam('SecondarySignal', 'SIGNAL_VC_MEMBPOTENTIAL')

    #time.sleep(2)
    
    #workbench.configureTasks(duration)    
    print("Configured!")
    periods_in_duration = duration / period

    data_queue = queue.Queue()
    stop_event = threading.Event()

    acquisition_thread = threading.Thread(target=acquireData2, args=(data_queue, periods_in_duration, period, stop_event))
    acquisition_thread.start()

    fig, ax = plt.subplots(3, 1)
    x = np.zeros(1)
    line1, = ax[0].plot(x, np.zeros(1))
    line2, = ax[1].plot(x, np.zeros(1))
    ax[0].set_xlim([0,180])
    
    ax[1].set_xlim([0,180])
    ax[1].set_ylim([-5e-9, 5e-9])

    animation = FuncAnimation(fig, update_plot2, fargs=(data_queue, line1, line2), interval=1000/60)

    plt.show()

    stop_event.set()
    acquisition_thread.join()

    
def update_plot2(frame, data_queue, line1, line2):
    try:
        while not data_queue.empty():
            voltage, current = data_queue.get_nowait()
            line1.set_xdata(np.arange(len(voltage)))
            line1.set_ydata(voltage)
            line2.set_xdata(np.arange(len(current)))
            line2.set_ydata(current)
    except queue.Empty:
        pass
    return line1, line2

def acquireData2(data_queue, periods_in_duration, period, stop_recording):
    #for i in range(int(periods_in_duration)):
    while not stop_recording.is_set():
        _, voltage_data = workbench.sendPulse(1, 1, period)
        #print(voltage_data)
        voltage_sent = voltage_data[0][1]
        voltage_read = voltage_data[0][0]

        voltage_sent = voltage_sent * workbench.clamp.getState()['secondaryScaleFactor']
        current_read = voltage_read * workbench.clamp.getState()['primaryScaleFactor']

        #print(voltage_sent, current_read)

        resistances = calculateResistance(voltage_sent, current_read, 1)
        print("Resistances 2: ", round(resistances[0] / 1e6, 2))

        data_queue.put((voltage_sent, current_read))

def updateFigure(fig, lines, newDataArr):
    for i in range(len(lines)):
        lines[i].set_ydata(newDataArr[i])
    fig.canvas.draw()
    fig.canvas.flush_events()

streamPulses2()