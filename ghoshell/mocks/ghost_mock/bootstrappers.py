from ghoshell.framework.ghost import GhostBootstrapper
from ghoshell.ghost import *
from ghoshell.mocks.ghost_mock.think_mock import HelloWorldThink


class RegisterThinkDemosBootstrapper(GhostBootstrapper):

    def bootstrap(self, ghost: Ghost):
        # thinks
        helloworld = HelloWorldThink()

        # register
        ghost.mindset.register_think(helloworld)
