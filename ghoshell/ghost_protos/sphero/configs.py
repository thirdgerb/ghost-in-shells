import random
import string
from typing import List

from pydantic import BaseModel

from ghoshell.ghost_protos.sphero.messages import commands_instruction


class SpheroMainModeConfig(BaseModel):
    """
    主模式
    """
    name: str = "sphero/main_mode"

    welcome: str = "welcome"

    instruction: str = """
我是球形机器人 SpheroGPT, 可以理解用户的指令, 并转化为自己的行动. 

我有三种运行模式: 
* 简单命令模式: 
"""


class SpheroSimpleCommandModeConfig(BaseModel):
    """
    简单命令模式.
    """
    name: str = "sphero/simple_command_mode"
    desc: str = "todo"
    on_activate: str = "进入单一命令模式, 请给我下达指令"
    unknown_order: str = "无法理解的命令"

    debug: bool = True

    instruction: str = f"""
我是球形机器人 SpheroGPT. 

当前是简单命令模式, 我需要理解用户的命令, 转化为自己的行动指令. 

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

    invalid_mark: str = "no"

    def prompt(self, instruction: str, command: str, sep: str | None = None):
        if sep is None:
            sep = "".join(random.sample(string.ascii_letters, 3))
        return self.prompt_temp.format(
            instruction=instruction,
            command=command,
            sep=sep
        )


class SpheroLearningModeConfig(BaseModel):
    """
    多轮对话学习模式的配置.
    """

    name: str = "sphero/conversational_mode"

    on_activate: str = "进入学习模式"

    desc: str = "todo"

    debug: bool = True

    instruction: str = """
我是球形机器人 SpheroGPT. 

当前是学习模式, 用户会通过多轮对话来告知我需要执行的复杂指令, 我可以对指令进行测试, 或作为技能保存. 
我需要一直引导用户进行下一步的对话, 要求给出指令, 直到用户决定结束对话为止.

每一轮对话我都需要把自己当前的想法以 yaml object 形式输出. 输出可用的字段如下: 

* reply: str, 必填, 本轮我对用户回复的话
* direction: str | None, 本轮对话中得到的新指令, 用自然语言来表达, 会记录到指令集中. 如果对话内容和指令无关, 则字段可以缺省.
* run: str | None, 我认为用户想要我立刻执行的指令, 用自然语言表示, 通常是测试中需要我立刻执行的命令, 它不会记录到完整指令中.
* test: bool, 默认值是 false, 我会立刻执行所有的指令. 
* title: str, 用来表示当前技能的名称. 当用户要求我记忆技能时, 如果 title 字段为空, 我需要主动提问要求用户告诉我命令名. 
* save: bool, 默认值是 false, 如果用户想要我保存当前技能时 save 为 true
* finished: bool, 默认值是 false, 用来标记当前对话是否已经结束.

举个例子, 当用户说 `测试一下` 时, 我可以输出为: 

```yaml
reply: 好的!
test: true
```

当用户说 `然后用 100 的速度向右走两秒`, 我可以输出为: 
```yaml
reply: 好的, 然后呢? 
direction: 用 100 的速度向右走两秒
```

当用户说 `可以了, 先到这里吧`, 我可以输出为:

```yaml
reply: 好的, 结束学习模式
finished: true
```

"""

    prompt_temp: str = """
# instruction

{instruction}

当前是第 {n} 轮对话, 目前我已经记录的指令是: 

{commands}

用户本轮对我说的是: 

{direction}

我本轮的输出的 yaml 是 (不需要 ``` 等符号括起来): 
"""

    def turn_prompt(self, n: int, commands: List[str], direction: str) -> str:
        commands_text = "无"
        if len(commands) > 0:
            commands_text = "\n- ".join(commands)

        return self.prompt_temp.format(
            instruction=self.instruction,
            n=n,
            commands=commands_text,
            direction=direction,
        )


class SpheroThinkConfig(BaseModel):
    """
    Sphero 控制界面的各种配置.
    """
    main_mode: SpheroMainModeConfig = SpheroMainModeConfig
    simple_command_mode: SpheroSimpleCommandModeConfig = SpheroSimpleCommandModeConfig()
    conversational_mode: SpheroLearningModeConfig = SpheroLearningModeConfig()
