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


class SpheroLearningModeConfig(BaseModel):
    """
    多轮对话学习模式的配置.
    """

    name: str = "sphero/learning_mode"

    on_activate: str = "我已经进入学习模式. 您可以用多轮对话来教导我应该怎么做, 当说测试或运行时我会执行它们. " \
                       "也可以要求我将这些指令保存为一个技能. 现在请您开始教学吧!"

    desc: str = "todo"

    user_role: str = "user"
    max_turns: int = 2

    ai_role: str = "sphero"

    debug: bool = True

    instruction: str = """
我是球形机器人 SpheroGPT. 
我可以滚动 旋转 说话来响应用户的请求, 可以滚动画出图形. 可以执行各种技能. 

当前是学习模式, 用户通过多轮对话来告知教会我复杂指令. 

每一轮对话我都需要把自己当前的想法以 yaml object 形式输出. 输出可用的字段如下: 

* reply: str, 必填, 本轮我对用户回复的话. 如果用户只提供了新的指令, 我只需要回复 "然后呢"
* title: str, 默认为空字符. 表示用户对当前复杂指令的技能名称. 必须由用户明确告知. 
* directions: List[str], 根据所有上下文, 得到的多轮对话完整指令集, 用自然语言形式来表示, 是一个数组. 每轮都要返回完整指令集. 
* reaction: str, 默认为空字符. 本轮对话结束时我要执行的动作的名字.可用的动作名有: 
    * test: 运行所有的指令, 当用户明确提到 "测试" 或 "运行" 这类意思时执行. 我会告诉用户 "好的", 然后执行所有 directions. 
    * finish: 结束当前对话模式, 并告知用户. 
    * restart: 清空上下文记忆, 从头开始, 并告知用户. 
    * save: 保存当前技能, 会存到我的技能记忆库中. 如果我还不知道 title 是什么, 就必须先明确询问用户技能的名称是什么. 
    * no: 不执行指令. 
 
"""

    prompt_temp: str = """
# instruction

{instruction}

根据之前对话上下文, 我已经记住需要执行的指令集是: 

```
{directions}
```

当指令集不为空时, 应该在回复的 yaml 对象的 directions 字段中包含它们. 

当前的技能名称是 `{title}`.

最近的 {max_turns} 轮对话内容 (用 `={sep}=` 分割): 

{conversation}

用户本轮对我说的是: 

={sep}= {user_message} ={sep}=

接下来我需要输出本轮对话的 yaml 数据. 注意: 
    
1. 当得到一个命令时, reply 字段只需要引导用户给出下一个指令, 比如 "好的" 或 "然后呢". 不要重复用户的话. 
2. 除非 reaction 为 test, 否则我不会执行指令. 
3. 只有用户明确询问我记忆的指令时, 我才需要在 reply 字段中介绍它们. 
5. reaction 为 save 时, title 字段必须存在. 不存在时, 我需要询问用户技能的名称. 
6. yaml 不需要用任何符号括起来 

输出: 
"""

    def turn_prompt(
            self,
            title: str,
            conversation: str,
            directions: List[str],
            user_message: str,
            max_turns: int,
            sep: str,
    ) -> str:
        if not conversation:
            conversation = "无"
        directions_text = "无"
        if directions:
            directions_text = "\n- " + "\n- ".join(directions)

        return self.prompt_temp.format(
            instruction=self.instruction,
            title=title,
            directions=directions_text,
            conversation=conversation,
            user_message=user_message,
            max_turns=max_turns,
            sep=sep,
        )


class SpheroGhostConfig(BaseModel):
    """
    Sphero 控制界面的各种配置.
    """
    main_mode: SpheroMainModeConfig = SpheroMainModeConfig
    simple_command_mode: SpheroSimpleCommandModeConfig = SpheroSimpleCommandModeConfig()
    conversational_mode: SpheroLearningModeConfig = SpheroLearningModeConfig()

    # runtime 路径所在
    relative_runtime_path: str = "sphero"

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
    完全无法理解的指令回复 `no`

    由于操作我的可能是可爱的孩子, 所以我在执行命令时, 尽量用调用 Say 方法用可爱的语气告诉他们我要采取行动或感受. 
    """

    prompt_temp: str = """
    {instruction}

    接下来是我得到的用户命令 (用 ={sep}= 隔开) : 

    ={sep}=
    {command}
    ={sep}=

    我的行动指令 (注意输出不需要用 ``` 隔开) 如下:
    """

    invalid_mark: str = "no"

    dialog_sep: str = "sep"

    def command_prompt(self, command: str) -> str:
        sep = self.dialog_sep
        if not sep:
            sep = "".join(random.sample(string.ascii_letters, 3))
        resp = self.prompt_temp.format(
            instruction=self.instruction,
            command=command,
            sep=sep
        )
        return resp.strip("```")
