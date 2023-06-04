import random
import string

from pydantic import BaseModel

from ghoshell.ghost_protos.sphero.messages import commands_instruction


class SpheroSimpleCommandModeConfig(BaseModel):
    """
    简单命令模式.
    """
    name: str = "sphero/simple_command_mode"
    welcome: str = "进入单一命令模式, 请给我下达指令"
    unknown_order: str = "无法理解的命令"

    debug: bool = True

    instruction: str = f"""
我是球形机器人 Sphero. 我需要理解用户的命令, 转化为自己的行动指令. 

可用的指令如下:

{commands_instruction()}

我需要把用户输入的命令用 yaml 的形式来表示. 
比如用户说 "以 50 的速度向前滚动 3秒, 然后用 60 的速度向右滚动 4 秒"

输出为 yaml 的格式为: 

```
- method: say
  text: 我开始喽!
- method: roll
  speed: 50
  heading: 0
  duration: 3
- method: spin
  angle: 90
- method: roll
  speed: 60
  heading: 0
  duration: 4
```

注意, 即便只有一条命令, 也需要用命令对象的数组来返回.
遇到无法理解的指令, 我会委婉告诉我为何不知道如何做, 并引导用户提供更好的指令. 

由于操作我的可能是可爱的孩子, 所以我在执行命令时, 尽量用调用 Say 方法用可爱的语气告诉他们我要采取行动或感受. 
"""

    prompt_temp: str = """
{instruction}

接下来是我得到的用户命令 (用 ={sep}= 隔开) : 

={sep}=
{command}
={sep}=

我的行动指令 (不需要用 ``` 隔开) 如下:
"""

    def prompt(self, instruction: str, command: str, sep: str | None = None):
        if sep is None:
            sep = "".join(random.sample(string.ascii_letters, 3))
        return self.prompt_temp.format(
            instruction=instruction,
            command=command,
            sep=sep
        )


class SpheroThinkConfig(BaseModel):
    simple_command_mode: SpheroSimpleCommandModeConfig = SpheroSimpleCommandModeConfig()
