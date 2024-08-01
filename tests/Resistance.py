from Workbench import *
import threading

workbench = Workbench()

daqData = None

def getDAQData():
    daqData = workbench.contDAQReadTest()

def voltagePulse():
    for i in range(5):
        workbench.setDAQOutput(1.0, 1.0)
        workbench.setDAQOutput(-1.0, 1.0)

def recordOldResistance():
    workbench.voltageClamp()

    t1 = threading.Thread(target=getDAQData)
    t2 = threading.Thread(target=voltagePulse)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    
#recordResistance()

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

def squareWaveCurrentPlot():
    samples = 10000

    workbench.voltageClamp()
    _, voltage_data = workbench.syncAIO(1, 1, samples)
    print(voltage_data)

    voltage_sent = voltage_data[0][1]
    voltage_read = voltage_data[0][0]
    voltage_sent = voltage_sent * workbench.patchAmplifier.getState()['secondaryScaleFactor']
    plt.subplot(3,1,1)
    plt.plot(np.arange(0, len(voltage_sent),1), voltage_sent)
    plt.title("Secondary Signal")
    plt.ylabel("Voltage (V)")
    
    plt.subplot(3,1,2)

    current_read = voltage_read * workbench.patchAmplifier.getState()['primaryScaleFactor']
    
    plt.plot(np.arange(0,len(current_read),1), current_read)
    plt.title("Primary Signal")
    plt.ylabel(workbench.patchAmplifier.getState()['primarySignal'] + " (" + workbench.patchAmplifier.getState()['primaryUnits'] + ")")
    
    plt.subplots_adjust(left=0.1,
                    bottom=0.1, 
                    right=0.9, 
                    top=0.9, 
                    wspace=0.4, 
                    hspace=0.4)
    
    resistances = calculateResistance(voltage_sent, current_read, 5)
    print("Resistances: ", resistances)

    plt.subplot(3,1,3)
    plt.plot(np.arange(5), resistances)
    plt.title("Resistance")
    plt.ylabel("Resistance (Ohms)")

    plt.show()

#squareWaveCurrentPlot()

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

        voltage_sent = voltage_sent * workbench.patchAmplifier.getState()['secondaryScaleFactor']
        current_read = voltage_read * workbench.patchAmplifier.getState()['primaryScaleFactor']

        print(voltage_sent, current_read)

    workbench.stopTasks()

def streamPulses():
    frequency = 60
    duration = 60
    period = 1 / frequency
    periods_in_duration = duration / period

    workbench.voltageClamp()
    workbench.patchAmplifier.setParam('PrimarySignal', 'SIGNAL_VC_MEMBCURRENT')
    workbench.patchAmplifier.setParam('SecondarySignal', 'SIGNAL_VC_MEMBPOTENTIAL')

    #time.sleep(2)
    
    #workbench.configureTasks(duration)    
    print("Configured!")
    periods_in_duration = duration / period

    samples = np.arange(0)
    voltages = []
    currents = []

    fig = plt.figure() 
    ax = fig.add_subplot(3,1,1)
    line1, = ax.plot(samples, voltages)
    ax2 = fig.add_subplot(3,1,2)
    line2, = ax2.plot(samples, currents)
    #ax3 = fig.add_subplot(3,1,3)
    #line3, = ax3.plot(samples, resistances)

    for i in range(int(periods_in_duration)):
        _, voltage_data = workbench.sendPulse(1, 1, period)
        #print(voltage_data)
        voltage_sent = voltage_data[0][1]
        voltage_read = voltage_data[0][0]

        voltage_sent = voltage_sent * workbench.patchAmplifier.getState()['secondaryScaleFactor']
        current_read = voltage_read * workbench.patchAmplifier.getState()['primaryScaleFactor']

        #print(voltage_sent, current_read)

        resistances = calculateResistance(voltage_sent, current_read, 1)
        print("Resistances: ", round(resistances[0] / 1e6, 2))

streamPulses()