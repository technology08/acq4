from Workbench import Workbench
from statemachine import StateMachine, State
from statemachine.contrib.diagram import DotGraphMachine

class ConnorStateMachine(StateMachine):
    #wb = Workbench()

    capture = State(initial=True)
    hunt = State()
    seal = State()
    breakIn = State()
    wholeCell = State()
    clean = State()
    abort = State(final=True)

    #captureSuccess = capture.to(hunt)
    #captureFail = capture.to(clean)
    #captureProcess = capture.to.itself()
    captureTransition = (capture.to(hunt, cond='captureUserConfirms') | capture.to(clean, unless='captureUserConfirms'))
    huntTransitions = (hunt.to(seal, cond="huntSuccess") | hunt.to(clean, cond='huntMovedTooFar') | hunt.to(abort, cond='huntResistanceTooLow') | hunt.to.itself())
    sealTransitions = (seal.to(breakIn, cond='gigasealPresent') | seal.to(clean, cond='sealTimeExpired') | seal.to.itself())
    breakInTransitions = (breakIn.to(wholeCell, cond='transientPresent') | breakIn.to(clean, cond='breakInAttemptsTimeout')  | breakIn.to.itself())
    wholeCellComplete = wholeCell.to(clean)
    cleanComplete = clean.to(capture)

    def __init__(self):
        
        super(ConnorStateMachine, self).__init__()
        #self.captureTransition()

    def on_enter_capture(self):
        print("Capture")
        #self.captureTransition()
        pass

    def entering_hunt(self):
        print("Hunting")
        pass

    def entering_seal(self):
        pass

    def entering_breakIn(self):
        pass

    def entering_wholeCell(self):
        pass

    def entering_clean(self):
        pass

    def captureUserConfirms(self):
        # Have user confirm if cell is captured properly
        return True

    def huntSuccess(self):
        # Calculate resistance, if resistance greater than threshold, return true
        pass #raise NotImplemented()
    
    def huntMovedTooFar(self):
        # Track z stage, if manipulator moves over 100 um, return true
        pass #raise NotImplemented()
    
    def huntResistanceTooLow(self):
        # If resistance way too low, something broke, abort
        pass #raise NotImplemented()
    
    def gigasealPresent(self):
        # If gigaseal, return True
        pass #raise NotImplemented()

    def sealTimeExpired(self):
        # if time > 20 seconds since beginning of seal, expire time
        pass #raise NotImplemented()

    def transientPresent(self):
        # if transient looks like a cell, then return true
        pass #raise NotImplemented()

    def breakInAttemptsTimeout(self):
        # too many break in attempts, return true
        pass#raise NotImplemented()
    
sm = ConnorStateMachine()
print(sm.current_state.name)
#sm.capture()
#graph = DotGraphMachine(ConnorStateMachine)
#dot = graph()
#dot.write_png("sm.png")

#class StateMachine:
#
#    def __init__(self):
#        self.wb = Workbench()
#        self.state = 'init'
#
#    def startCaptureState(self):
#        # Run capture state
#        self.state = 'capture'
#        pass
#
#    def startHuntState(self):
#        # Run hunt state
#        self.state = 'hunt'
#        pass
#
#    def startSealState(self):
#        # Run seal state
#        self.state = 'seal'
#        pass
#
#    def startBreakInState(self):
#        # Run break in state
#        self.state = 'breakin'
#        pass
#
#    def startWholeCellState(self):
#        # Run whole cell state
#        self.state = 'wholecell'
#        pass
#
#    def startCleanPipetteState(self):
#        # Run clean pipette state
#        self.state = 'clean'
#        pass