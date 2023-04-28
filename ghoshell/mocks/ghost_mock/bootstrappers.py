from ghoshell.ghost import *
from ghoshell.ghost_fmk import Bootstrapper, GhostConfig
from ghoshell.ghost_fmk.intentions import FocusOnCommandHandler
from ghoshell.mocks.ghost_mock.think_mock import HelloWorldThink


class RegisterThinkDemosBootstrapper(Bootstrapper):

    def bootstrap(self, ghost: Ghost):
        # thinks
        helloworld = HelloWorldThink()

        # register
        ghost.mindset.register_think(helloworld)

        # change config
        config = ghost.container.force_fetch(GhostConfig)
        config.root_url = helloworld.url()


class RegisterFocusDriverBootstrapper(Bootstrapper):

    def bootstrap(self, ghost: Ghost):
        focus = ghost.focus

        # register command driver
        command_driver = FocusOnCommandHandler("/")
        focus.register(command_driver)
