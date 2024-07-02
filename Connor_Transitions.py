from transitions import Machine

class ConnorTransitionMachine: 

    states = ['capture', 'hunt', 'seal', 'breakIn', 'wholeCell', 'clean', 'abort']

    def __init__(self):
        self.machine = Machine(model=self, states=ConnorTransitionMachine.states, initial='capture')

        self.machine.add_transition(trigger='captureUserConfirms', source='capture', dest='hunt')
        #self.machine.add_transition('captureUserCancels', 'capture', 'clean')
        self.machine.add_transition('huntSuccess', 'hunt', 'seal', unless='huntResistanceTooLow')
        self.machine.add_transition('huntSuccess', 'hunt', 'abort', conditions=['huntResistanceTooLow'])
        self.machine.add_transition('cleanPipette', '*', 'clean')

        self.machine.add_transition('gigasealPresent', 'seal', 'breakIn')
        
        self.machine.add_transition('transientPresent', 'breakIn', 'wholeCell')
        self.machine.add_transition('startNewCell', 'clean', 'capture')

    def capture_loop(self):
        print("hji")
        while self.machine.get_state == 'capture':
            print("capture!")

sm = ConnorTransitionMachine().machine
print(sm.get_state)
sm.on_enter_capture('capture_loop')