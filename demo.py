#!/usr/bin/env python
from ghoshell.ghost_fmk.mocks import GhostMock
from ghoshell.shell_protos import ConsoleShell


def main():
    shell = ConsoleShell(GhostMock())
    shell.run_as_app()


if __name__ == "__main__":
    main()
