from ghoshell.framework.reactions.commands import *
from ghoshell.framework.reactions.llm_tools import LLMToolReaction, LLMToolIntention

cancel_cmd = CancelCmdReaction()
restart_cmd = RestartCmdReaction()
quit_cmd = QuitCmdReaction()
task_cmd = TaskCmdReaction()
process_cmd = ProcessCmdReaction()
instance_count_cmd = InstanceCountCmdReaction()
thought_cmd = ThoughtCmdReaction()
redirect_cmd = RedirectCmdReaction()

system_cmds = {
    "cancel": cancel_cmd,
    "restart": restart_cmd,
    "quit": quit_cmd,
    "task": task_cmd,
    "process": process_cmd,
    "thought": thought_cmd,
}

__all__ = [
    "system_cmds",

    "cancel_cmd", "restart_cmd", "quit_cmd", "task_cmd",
    "process_cmd", "instance_count_cmd", "thought_cmd", "redirect_cmd",

    "CommandReaction", "Command", "CommandOutput",
    "LLMToolReaction", "LLMToolIntention",
]
