import os
import shutil

from rich.console import Console
from rich.prompt import Prompt


def initialize_env() -> None:
    console = Console()
    dirname, filename = os.path.split(os.path.realpath(__file__))
    ghoshell_root = os.path.dirname(os.path.dirname(dirname))
    demo_path = ghoshell_root + "/demo"
    cwd = os.getcwd()
    console.print(f"ready to initialize ghoshell demo environment")
    value = Prompt.ask(
        f"please confirm: copy ghoshell config and runtime files to {cwd}",
        console=console,
        default="yes",
    )
    if value == "yes":
        shutil.copytree(demo_path, cwd + "/hello")
        console.print("done!")
    console.print("quit")
    exit(0)


