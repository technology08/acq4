class State(object):
    """
    We define a state object which provides some utility functions for the
    individual states within the state machine.
    """

    def __init__(self):
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
    def on_event(self, event):

        cleared = input("Has capture pipette acquired a cell? (y/n) ")
        #if event == 'user_cleared':
        if cleared == 'y':
            return HuntState()
        elif cleared == 'n':
            return CleanState()
        else:
            return self
    
class HuntState(State):
    def on_event(self, event):
        if event == 'pin_entered':
            return CleanState()

        return self
    
class SealState(State):
    def on_event(self, event):
        if event == 'pin_entered':
            return CleanState()

        return self
    
class BreakInState(State):
    def on_event(self, event):
        if event == 'pin_entered':
            return CleanState()

        # define our loop here
        return self
    
class WholeCellState(State):
    def on_event(self, event):
        if event == 'pin_entered':
            return CleanState()

        return self

class CleanState(State):
    def on_event(self, event):
        if event == 'device_locked':
            return CaptureState()

        return self
    
class SimpleDevice(object):
    """ 
    A simple state machine that mimics the functionality of a device from a 
    high level.
    """

    def __init__(self):
        """ Initialize the components. """

        # Start with a default state.
        self.state = CaptureState()

    def on_event(self, event):
        """
        This is the bread and butter of the state machine. Incoming events are
        delegated to the given states which then handle the event. The result is
        then assigned as the new state.
        """

        # The next state will be the result of the on_event function.
        self.state = self.state.on_event(event)


# Every state returns the next state
# While loop runs outside state machine
# Has resistance increased by 10% Pull bath test out, will cause resistance to increase and call transition.