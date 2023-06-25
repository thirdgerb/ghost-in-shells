from __future__ import annotations

import math
from abc import ABCMeta, abstractmethod
from typing import ClassVar, List, Dict, Type

from pydantic import Field, BaseModel
from spherov2.types import Color

from ghoshell.prototypes.sphero.sphero_kernel import SpheroKernel, SpheroRunnable, SpheroCmdStatus

xx = math.sin(30)


class SpheroCommand(BaseModel, SpheroRunnable, metaclass=ABCMeta):
    """
    Sphero 指令的抽象. 用于 DSL
    """

    method: ClassVar[str] = ""

    @classmethod
    def name(cls) -> str:
        return cls.method

    @classmethod
    @abstractmethod
    def desc(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def yaml_desc(cls) -> str:
        """
        对 yaml 格式的自我描述.
        """
        return """
各种指令可能会用到的标准参数有: 

* speed: int 类型, 定义滚动的速度, 范围是 0 到 255, 0 表示停止. 默认值是 100
* heading: int 类型, 定义滚动的方向, 范围是 -360 到 360, 对应圆形的角度. 正前方是 0, 正后方是 180, 向左是 270, 向右是 90. 
* duration: float 类型, 定义滚动的时间, 单位是秒. 默认值是 1. 为负数表示一直持续
* angle: int 类型. 是一个转动的角度, 会变更我的正面指向. 360 表示 360度, 是一个整圆.
 
以下是现有的指令: 

"""

    def on_stop(self, duration: float, interrupt: str) -> str:
        if interrupt:
            return f"{duration} 秒后中断, 原因是 `{interrupt}`"
        return f"{duration}秒后完成."

    @classmethod
    def read(cls, data: Dict) -> SpheroCommand | None:
        if data.get("method", "") == cls.method:
            return cls(**data)
        return None

    def to_command_data(self) -> Dict:
        data = self.dict()
        data["method"] = self.method
        return data


class Roll(SpheroCommand):
    """
    最基本的滚动命令.
    """

    method = "roll"
    heading: int = Field(default=0, description="滚动的朝向, 360表示360度. 默认是 0")
    speed: int = Field(default=100, description="定义滚动的速度, 范围是 0 到 255, 0 表示停止.  默认值是 100")
    duration: float = Field(default=1, description="定义滚动的时间, 单位是秒. 默认值是 1. 为负数表示一直持续")

    @classmethod
    def desc(cls) -> str:
        return "控制身体滚动, 遇到碰撞时会停止. 不会改变面朝的方向."

    @classmethod
    def yaml_desc(cls) -> str:
        return """
* roll: 控制我的身体滚动. 参数有 speed, heading, duration
"""

    #         return """
    # * roll: 控制我的身体滚动.
    #   * speed: int 类型, 定义滚动的速度, 范围是 0 到 255, 0 表示停止. 默认值是 100
    #   * heading: int 类型, 定义滚动的方向, 范围是 -360 到 360, 对应圆形的角度. 正前方是 0, 正后方是 180, 向左是 270, 向右是 90.
    #   * duration: float 类型, 定义滚动的时间, 单位是秒. 默认值是 1. 为负数表示一直持续
    # """

    def runtime_plan(self) -> str:
        return f"以{self.speed}的速度, {self.heading}的角度滚动 {self.duration}秒"

    def run_frame(self, kernel: SpheroKernel, status: SpheroCmdStatus, at: float):
        if not self.duration < 0 and status.start_at + self.duration < at:
            kernel.api.stop_roll()
            kernel.api.set_front_led(Color(0, 0, 0))
            kernel.api.set_back_led(Color(0, 0, 0))
            kernel.api.clear_matrix()
            return False
        if status.ran_frames_count == 0:
            kernel.api.set_front_led(Color(0, 200, 0))
            kernel.api.set_back_led(Color(0, 0, 0))
            heading = kernel.toward(self.heading)
            kernel.api.set_speed(self.speed)
            kernel.api.set_heading(heading)
            # kernel.api.roll(self.speed, heading, self.duration)
        return True


class Spin(SpheroCommand):
    """
    旋转的命令, 需要变更朝向. 
    """
    method = "spin"

    angle: int = Field(default=90, description="转动的角度, 360 表示 360度. 正数表示顺时针旋转, 负数是逆时针旋转.")
    duration: float = Field(default=1, description="定义转动的时间. 默认值是 1. 单位是秒.")

    @classmethod
    def desc(cls) -> str:
        return "原地旋转, 改变面朝的角度"

    @classmethod
    def yaml_desc(cls) -> str:
        return """
* spin: 原地转动. 注意, 会改变朝向. 参数有 angle, duration
"""

    #         return """
    # * spin: 原地转动
    #   * angle: int 类型. 是一个转动的角度, 会变更我的正面指向. 360 表示 360度, 是一个整圆. 注意, 会变更我面向的角度.
    #   * duration: float 类型, 定义转动的时间. 默认值是 1. 单位是秒.
    # """

    def runtime_plan(self) -> str:
        return f"在{self.duration}秒内, 旋转 {self.angle} 度."

    def run_frame(self, kernel: SpheroKernel, status: SpheroCmdStatus, at: float):
        if status.ran_frames_count == 0:
            kernel.api.set_front_led(Color(0, 200, 0))
            kernel.api.spin(self.angle, self.duration)
            print("spin +++", at, status.start_at, self.duration)
            return True
        print("spin +++", at, status.start_at, self.duration)
        # 变更角度.
        kernel.front_angle = kernel.toward(self.angle)
        kernel.api.set_front_led(Color(0, 0, 0))
        return False


class LambdaSay(SpheroCommand):
    method = "lambda_say"
    func: str = Field(description="用 python lambda 函数返回要说的话. 比如 `lambda: '你好啊!'`")

    @classmethod
    def desc(cls) -> str:
        return """用声音模块说话, 可以运行一些计算逻辑, 比如计算运行距离: `lambda: "我滚动了{l}单位距离".format(l=100*3)` """

    @classmethod
    def yaml_desc(cls) -> str:
        return """
    * say: 用我的声音模块说话. 参数如下
        * func: 用 python lambda 函数返回要说的话. 比如 `lambda: "你好啊!"` 
    """

    def runtime_info(self, duration: float, interrupt: str) -> str:
        return self._get_text()

    def runtime_plan(self) -> str:
        text = self._get_text()
        return f"说 `{text}`"

    def _get_text(self) -> str:
        fn = eval(self.func)
        return fn()

    def run_frame(self, kernel: SpheroKernel, status: SpheroCmdStatus, at: float):
        if status.ran_frames_count == 0:
            kernel.api.stop_roll()
            text = self._get_text()
            kernel.api.set_main_led(Color(0, 0, 200))
            kernel.speak(text)
        kernel.api.clear_matrix()
        return False


class Say(SpheroCommand):
    """
    说话
    """

    method = "say"
    content: str = Field(description="要说的话.")

    @classmethod
    def desc(cls) -> str:
        return "用我的声音模块说话.比如 say(text=\"something\") "

    @classmethod
    def yaml_desc(cls) -> str:
        return """
* say: 用我的声音模块说话. 参数如下: 
    * text: 要说的话的内容. 
"""

    def runtime_info(self, duration: float, interrupt: str) -> str:
        return self.content

    def runtime_plan(self) -> str:
        return f"说 `{self.content}`"

    def run_frame(self, kernel: SpheroKernel, status: SpheroCmdStatus, at: float):
        if status.ran_frames_count == 0:
            kernel.api.stop_roll()
            kernel.api.set_main_led(Color(0, 0, 200))
            kernel.speak(self.content)
        kernel.api.clear_matrix()
        return False


class Stop(SpheroCommand):
    method = "stop"
    duration: int = Field(default=1, description="执行时间, 单位是秒")

    @classmethod
    def desc(cls) -> str:
        return "停止所有动作."

    @classmethod
    def yaml_desc(cls) -> str:
        return """
* stop: 强行停止转动. 
"""

    def runtime_plan(self) -> str:
        return f"在 {self.duration} 秒内停止动作."

    def run_frame(self, kernel: SpheroKernel, status: SpheroCmdStatus, at: float):
        if status.ran_frames_count == 0:
            kernel.api.set_front_led(Color(200, 0, 0))
            kernel.api.set_back_led(Color(200, 0, 0))
            kernel.api.stop_roll()
        in_duration = status.start_at + self.duration > at
        if not in_duration:
            kernel.api.set_front_led(Color(0, 0, 0))
            kernel.api.set_back_led(Color(0, 0, 0))
            kernel.api.clear_matrix()
        return in_duration


class Loop(SpheroCommand):
    """
    循环执行命令.
    """

    method = "loop"
    direction: str = Field(description="用自然语言描述需要循环执行的命令. 比如 `画正方形`")
    times: int = Field(default=1, description="循环执行的次数")
    # 需要执行的 commands 命令.
    commands: List[Dict] = Field(default_factory=lambda: [], description="不需要这个参数")

    @classmethod
    def desc(cls) -> str:
        return "循环执行一段自然语言描述的命令, 会自动解析成原子命令."

    @classmethod
    def yaml_desc(cls) -> str:
        return """
* loop: 循环执行一段指令. 参数如下:
    * times: int 类型, 表示循环执行的次数. 
    * direction: str 类型, 用自然语言描述需要循环执行的命令. 比如 `画正方形`
"""

    def runtime_plan(self) -> str:
        return f"循环执行命令 `{self.direction}` 共{self.times}次. "

    # def on_stop(self, stop_at: float) -> str:
    #     duration = stop_at - status.start_at
    #     return f"运行耗时 {self._loop_count} 次, 在{duration}秒后停止."

    def run_frame(self, kernel: SpheroKernel, status: SpheroCmdStatus, at: float) -> bool:
        is_finished = status.loop_count >= self.times
        if is_finished:
            return False
        status.loop_count += 1
        cmds = command_data_to_commands(self.commands)
        stages = [SpheroCmdStatus(cmd, logging=False) for cmd in cmds]
        kernel.insert_stages(stages)
        return True


# class RoundRoll(SpheroCommand):
#     """
#     以圆弧的形式滚动.
#     """
#
#     method = "round_roll"
#
#     speed: int
#     angle: int
#     duration: float
#
#     @classmethod
#     def yaml_desc(cls) -> str:
#         return """
# * round_roll: 从当前位置出发, 会按照圆形的弧线进行滚动. 不适合用来走出直线.
#     * speed: int 类型, 范围是 0 ~ 255, 表示滚动的速度. 默认是 50.
#     * angle: int 类型, 负数表示逆时针旋转, 正数为顺时针旋转. 表示滚动时要经过的角度. 比如 360 表示会沿圆弧滚动回起点.
#     * duration: float 类型, 单位是秒. 表示完成滚动的时间.
# """
#
#     def plan_desc(self) -> str:
#         return f"以{self.speed} 的速度, 在 {self.duration} 秒内完成 {self.angle} 度的圆弧"
#
#     def _run_frame(self, kernel: SpheroKernel, at: float) -> bool:
#         in_duration = self._start_at + self.duration > at
#         if not in_duration:
#             kernel.api.stop_roll()
#             kernel.api.set_front_led(Color(0, 0, 0))
#             return False
#
#         if self._ran_frames_count == 0:
#             kernel.api.set_front_led(Color(0, 200, 0))
#
#         passed = at - self._start_at
#         angle = round(self.angle * passed / self.duration)
#         heading = kernel.toward(angle)
#         kernel.api.set_heading(heading)
#         kernel.api.set_speed(self.speed)
#         # 不改变朝向.
#         return in_duration


class LambdaRoll(SpheroCommand):
    """
    高级命令形式, 可以用 python lambda 定义滚动时的速度与角度
    """

    method = "lambda_roll"

    speed: str = Field(
        description="接受一个 lambda 函数, 以 float 类型的 t 为参数 (表示经过时间, 单位是秒). "
                    "返回值是 int 类型, 表示速度, 范围是 -255 ~ 255. 例如 `lambda t: 100`, 表示速度恒定为 100"
    )
    heading: str = Field(
        description="接受一个 lambda 函数, 以 float 类型的 t 为参数 (表示经过时间, 单位是秒)."
                    " 返回值是 int 类型, 表示角度. 例如 `lambda t: 10`, 表示滚动指向固定为 10."

    )
    duration: float = Field(default=1, description="指令持续的时间, 单位是秒. 如果为负, 表示一直执行.")

    @classmethod
    def desc(cls) -> str:
        return "允许使用 python lambda 函数来定义滚动轨迹的方法. 可以使用 python 的 math 库." \
               "对于直线轨迹不该用 lambda_roll, 还是 roll + spin 组合使用更合理."

    @classmethod
    def yaml_desc(cls) -> str:
        return """
* lambda_roll: 允许使用 python lambda 函数来定义滚动轨迹的方法. 可以使用 python 的 math 库. 对于直线轨迹不该用 lambda_roll, 还是 roll + spin 组合使用更合理.  
    * speed: str 类型, 接受一个 lambda 函数, 以 float 类型的 t 为参数 (表示经过时间, 单位是秒), 返回值是 int 类型, 表示速度, 范围是 -255 ~ 255. 例如 `lambda t: 100`, 表示速度恒定为 100
    * heading: str 类型, 接受一个 lambda 函数, 以 float 类型的 t 为参数 (表示经过时间, 单位是秒), 返回值是 int 类型, 表示角度. 例如 `lambda t: 10`, 表示滚动指向固定为 10.
    * duration: float 类型, 指令持续的时间, 单位是秒
"""

    def runtime_plan(self) -> str:
        return f"在 {self.duration} 秒内, 以时间 t 为变量," \
               f"运行速度按函数 `{self.speed}`, 朝向按函数 `{self.heading}` 来滚动."

    def run_frame(self, kernel: SpheroKernel, status: SpheroCmdStatus, at: float) -> bool:
        in_duration = self.duration < 0 or (status.start_at + self.duration > at)
        if not in_duration:
            kernel.api.stop_roll()
            kernel.api.set_front_led(Color(0, 0, 0))
            return False

        if status.ran_frames_count == 0:
            kernel.api.set_front_led(Color(0, 200, 0))

        t = at - status.start_at
        speed_fn = eval(self.speed)
        heading_fn = eval(self.heading)
        speed = speed_fn(t)
        heading = heading_fn(t)
        toward = kernel.toward(heading)
        kernel.api.set_heading(toward)
        kernel.api.set_speed(speed)
        return in_duration


class Ability(SpheroCommand):
    """
    使用一个已知的技能运动.
    """

    method = "ability_roll"

    ability_name: str = Field(description="技能的名字")

    commands: List[Dict] = Field(default_factory=lambda: [], description="不需要这个参数")

    @classmethod
    def desc(cls) -> str:
        return "使用一个已有的技能. 所谓技能, 是系统已经掌握的一组指令."

    @classmethod
    def yaml_desc(cls) -> str:
        return """
* ability_roll: 使用一个已有的技能. 所谓技能, 是系统已经掌握的一组指令. 
    * name: str 类型, 表示技能的名字.
"""

    def runtime_plan(self) -> str:
        return f"运行技能 `{self.ability_name}`."

    def run_frame(self, kernel: SpheroKernel, status: SpheroCmdStatus, at: float) -> bool:
        if status.loop_count > 0:
            return False
        status.loop_count += 1
        cmds = command_data_to_commands(self.commands)
        stages = [SpheroCmdStatus(cmd, logging=False) for cmd in cmds]
        kernel.insert_stages(stages)
        return True


defined_commands: [Type[SpheroCommand]] = {cmd.method: cmd for cmd in [
    Roll,
    Spin,
    Stop,
    Say,
    Loop,
    LambdaSay,
    # RoundRoll,
    LambdaRoll,
    Ability,
]}


def loop_check(command_data: Dict) -> Loop | None:
    return Loop.read(command_data)


def ability_check(command_data: Dict) -> Ability | None:
    return Ability.read(command_data)


def command_data_to_commands(commands: List[Dict]) -> List[SpheroCommand]:
    """
    将消息解析成一个个的命令对象.
    """
    result = []
    for message_data in commands:
        method = message_data.get("method", "")
        if method in defined_commands:
            wrapped = defined_commands[method].read(message_data)
            if wrapped is not None:
                result.append(wrapped)
    return result


def commands_yaml_instruction() -> str:
    """
    所有命令的描述的集合.
    """
    desc = []
    for key in sorted(defined_commands.keys()):
        cmd = defined_commands[key]
        desc.append(cmd.yaml_desc())
    return "\n".join(desc)
