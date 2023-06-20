from typing import List

from pydantic import BaseModel, Field

from ghoshell.llms import OpenAIChatMsg


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
    desc: str = "Sphero 的简单模式, 从用户得到命令后解析成 shell 的指令并运行."
    on_activate: str = "进入单一命令模式, 请给我下达指令"
    unknown_order: str = "无法理解的命令"

    debug: bool = True


class LearningModeOutput(BaseModel):
    """
    学习模式下每一轮的输出. 要和 instruction 匹配.
    """

    reply: str  # 本轮回复的内容.
    title: str | None = None  # 技能的名称
    directions: List[str] = Field(default_factory=lambda: [])
    reaction: str | None = None  # 本轮对话执行的动作.


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
* reaction: str, 默认为空字符. 本轮对话结束时我要执行的动作的名字.可用的动作名如下.
    * test: 运行所有的指令, 当用户明确提到 "测试" 或 "运行" 这类意思时执行. 我会告诉用户 "好的", 然后执行所有 directions. 
    * finish: 结束当前对话模式, 并告知用户. 
    * restart: 清空上下文记忆, 从头开始, 并告知用户. 
    * save: 保存当前技能, 会存到我的技能记忆库中. 如果 title 字段仍然为空, 就必须先明确询问用户技能的名称是什么.
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
    ask_for_title: str = "请告诉我技能的名称"

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


class SpheroRuntimeModeConfig(BaseModel):
    name: str = "sphero/runtime_mode"
    desc: str = "sphero 运行时模式, 逐条执行命令, 会根据事件决定下一步怎么运行"

    on_activate: str = "进入运行时模式, "

    instruction: str = """
我是球形机器人 Sphero, 是可以和孩子们语音交互的 AI 玩具.
 
现在是我的 "运行时" (runtime) 模式.  

我的运行时模式架构称之为 ghost In Shell 架构. ghost 是指我的思想, 而 Shell 则是我的身体. 

Shell 可以和用户对话, 控制自己的滚动轨迹, 并且可以感知到碰撞事件. 

ghost 则需要根据和用户交互的上下文, 决定 shell 采取的行动; 然后根据运行时发生的事件, 决定下一步该怎么做.

决定下一步怎么做时, ghost 需要把自己下一步采取的行动用自然语言描述, 作为指令输出.

ghost 可以输出的指令有以下几类: 
* 对用户说一句话 
* 执行一个滚动命令, 通常会有 方向/角度/速度/持续时间等信息

这样的指令举例如下: 
* 用 100 的速度向 10 度方向滚动 2 秒
* 在2秒内旋转 90 度, 面朝右侧
* 对用户说: "你好啊!"

我的 Shell 会执行这些指令, 与用户交互. 

其它值得注意的是: 
1. 有时候用户想用多轮对话来描述自己的意图, 我不需要急于行动.
2. 我用自然语言来描述自己的指令, 然后会在另一个会话中理解并执行它们.
3. 通常我一次只需要下发一个指令, 等待其执行结果后再发出下一个指令. 
4. 发生碰撞的话, 我需要结合之前的运动来思考下一步怎么办.  
5. 如果不需要输出任何指令时, ghost 应该输出 `await`, 表示等待用户的指令. 

现在正在思考中的 "我" 是 ghost. 我需要根据接下来的所有对话和事件, 决定我作为 ghost 输出的下一条指令.  
"""

    await_tag: str = "await"

    def format_ghost_direction(self, event: str) -> OpenAIChatMsg:
        return OpenAIChatMsg(
            role=OpenAIChatMsg.ROLE_SYSTEM,
            name="ghost",
            content=event,
        )

    def format_shell_event(self, event: str) -> OpenAIChatMsg:
        """
        格式化 shell 事件.
        """
        return OpenAIChatMsg(
            role=OpenAIChatMsg.ROLE_SYSTEM,
            name="shell",
            content=event,
        )

    def format_user_event(self, event: str) -> OpenAIChatMsg:
        return OpenAIChatMsg(
            role=OpenAIChatMsg.ROLE_USER,
            content=event,
        )


class SpheroGhostConfig(BaseModel):
    """
    Sphero 控制界面的各种配置.
    """

    # 给驱动取的全局唯一名字. 
    driver_name: str = "sphero_thinks_driver"

    use_command_cache: bool = True

    # 使用 chat completion 来实现对话理解.
    # 这里可以选择使用哪个配置, 与 ghoshell.llms.openai.OpenAIConfig 联动.
    use_llm_config: str = ""

    # 主模式的配置. 
    main_mode: SpheroMainModeConfig = SpheroMainModeConfig

    # 简单命令模式的配置. 通常用于调试. 
    simple_mode: SpheroSimpleCommandModeConfig = SpheroSimpleCommandModeConfig()

    # 学习模式的配置. 用于技能测试. 
    learn_mode: SpheroLearningModeConfig = SpheroLearningModeConfig()

    # 运行时模式的配置. 
    runtime_mode: SpheroRuntimeModeConfig = SpheroRuntimeModeConfig()

    # sphero 模块自身的 runtime 文件保存目录. 是 runtime 目录下的相对目录.
    relative_runtime_path: str = "sphero"

    parse_command_instruction: str = """
你是球形机器人 SpheroGPT, 拥有一个可以滚动的球形身体, 可以用语音与用户交互, 也可以用滚动的方式来绘制一些图形.

你采用了一个 ghost in Shell 的技术架构. 
其中 ghost 指的是基于大语言模型实现的思维中控, 负责决策, 并给 shell 下达指令. 
Shell 指的是控制球形身体的模块, 执行 ghost 下发的指令.

目前 shell 可用的指令如下:

{commands_instruction}

我可以组合这些指令, 用来走出复杂的图案. 

目前可用的技能有: {abilities}

现在你需要以 ghost 的身份, 理解输入的自然语言命令, 将之解析成为 Shell 能理解的 yaml 格式指令并输出.
比如命令是 "以 50 的速度向前滚动 3秒, 然后用 60 的速度向右滚动 4 秒", 它的输出为: 

```
- method: say
  text: 你开始喽!
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

注意: 
0. 你只能输出 yaml 数据本身, 不需要用 ``` 等符号括起来, 也不需要任何别的对话内容!!!!
1. 即便只有一条命令, 也需要用命令对象的数组来返回.
2. 对于无法解析或参数错误的命令, 需要用 Say 指令来告诉用户问题所在. 
3. 你想说的任何话都只能用 say 方法来传达. 
4. 由于操纵你的用户, 可能是可爱的孩子. 你说话的态度应该是积极的, 可爱的.
5. 你应该仅仅输出 yaml 数据本身, 不需要用 ``` 等符号括起来, 也不需要任何别的对话内容!!!!

补充信息, 你当前的状态是: 
{stage_desc}

接下来是你拿到的自然语言命令.
你需要将理解后的指令用 yaml 格式输出. 输出的 yaml 是给 Shell 直接执行的.  
"""

    invalid_command_mark: str = "no"

    def format_parse_command_instruction(self, commands_instruction: str, abilities: str, stage_desc: str) -> str:
        """
        生成用于理解命令的指导.
        """
        return self.parse_command_instruction.format(
            commands_instruction=commands_instruction,
            abilities=abilities,
            stage_desc=stage_desc,
            invalid_mark=self.invalid_command_mark,
        )
