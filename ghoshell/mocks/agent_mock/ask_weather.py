from pydantic import BaseModel, Field

from ghoshell.ghost import Context, Operator
from ghoshell.llms.thinks import agent_func_decorator, AgentThought


class AskWeatherArgs(BaseModel):
    """
    询问天气作为一个 think, 这里提供
    """
    city: str = Field(description="城市名称", default="")
    date: str = Field(description="询问天气时的日期", default="today")


@agent_func_decorator(name="do_ask_weather", desc="运行查询天气, 会立刻返回结果.", args_type=AskWeatherArgs)
def do_ask_weather(ctx: Context, this: AgentThought, arguments: AskWeatherArgs) -> Operator:
    this.say(ctx, f"查询结果: {arguments.city} 在 {arguments.date} 的天气是晴转多云, 气温 20 度")
    return ctx.mind(this).repeat()
