from statemachine import State, StateMachine

class ConnorSMP(StateMachine):
    #waiting_for_payment = State(initial=False)
    #processing = State()
    #shipping = State()
    #completed = State()

    #add_to_order = waiting_for_payment.to(waiting_for_payment)
    #receive_payment = (
    #    #waiting_for_payment.to(processing, cond="payments_enough")
    #    waiting_for_payment.to(waiting_for_payment, unless="payments_enough")
    #)
    #process_order = processing.to(shipping, cond="payment_received")
    #ship_order = shipping.to(completed)

    capture = State(initial=True)
    hunt = State()
    seal = State()
    breakIn = State()
    wholeCell = State()
    clean = State()
    abort = State(final=True)

    captureTransition = (capture.to(hunt, cond='captureUserConfirms') | capture.to(clean, unless='captureUserConfirms'))
    huntTransitions = (hunt.to(seal, cond="huntSuccess") | hunt.to(clean, cond='huntMovedTooFar') | hunt.to(abort, cond='huntResistanceTooLow') | hunt.to.itself())
    sealTransitions = (seal.to(breakIn, cond='gigasealPresent') | seal.to(clean, cond='sealTimeExpired') | seal.to.itself())
    breakInTransitions = (breakIn.to(wholeCell, cond='transientPresent') | breakIn.to(clean, cond='breakInAttemptsTimeout')  | breakIn.to.itself())
    wholeCellComplete = wholeCell.to(clean)
    cleanComplete = clean.to(capture)
    #oldtonew = capture.to(waiting_for_payment)

    captureT = capture.to(hunt)
    huntT = hunt.to(seal)
    sealT = seal.to(breakIn)
    biT = breakIn.to(wholeCell)
    wholeCellT = wholeCell.to(clean)
    cleanT = clean.to(abort)

    def __init__(self):
        self.order_total = 0
        self.payments = []
        #self.payment_received = False
        super(ConnorSMP, self).__init__()
        #self.add_to_order(4)

    def payments_enough(self, amount):
        return sum(self.payments) + amount >= self.order_total

    def before_add_to_order(self, amount):
        self.order_total += amount
        return self.order_total

    def before_receive_payment(self, amount):
        self.payments.append(amount)
        return self.payments

    def after_receive_payment(self):
        self.payment_received = True

    def on_enter_waiting_for_payment(self):
        self.payment_received = False

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

sm = ConnorSMP()
