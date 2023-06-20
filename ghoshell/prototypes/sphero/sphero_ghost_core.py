import os
from typing import Dict, List, Tuple

import yaml
from pydantic import BaseModel, Field

from ghoshell.ghost import Context, Thought, CtxTool
from ghoshell.llms import OpenAIChatCompletion, OpenAIChatMsg, OpenAIChatChoice
from ghoshell.prototypes.sphero.sphero_commands import Say, commands_instruction, loop_check, ability_check
from ghoshell.prototypes.sphero.sphero_ghost_configs import SpheroGhostConfig, LearningModeOutput
from ghoshell.prototypes.sphero.sphero_messages import SpheroCommandMessage


class SpheroCommandsCache(BaseModel):
    """
    做一个假的本地 cache, 方便测试时重复使用指令但不用每次都去 prompt.
    """

    abilities: List[str] = Field(default_factory=lambda: [])
    # 命令的索引.
    indexes: Dict[str, List[Dict]] = Field(default_factory=lambda: {})


class SpheroGhostCore:

    def __init__(self, runtime_path: str, config: SpheroGhostConfig):
        self.app_runtime_path = runtime_path
        self.config = config
        self._cached_commands: SpheroCommandsCache = SpheroCommandsCache()
        self._load_commands()

    def _load_commands(self):
        filename = self._cached_commands_file()
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                yaml.safe_dump(dict(), f)
        with open(filename) as f:
            data = yaml.safe_load(f)
            self._cached_commands = SpheroCommandsCache(**data)

    def _cached_commands_file(self) -> str:
        return "/".join([
            self.app_runtime_path.rstrip("/"),
            self.config.relative_runtime_path.strip("/"),
            "/commands.yaml",
        ])

    @classmethod
    def unpack_learning_mode_resp(cls, msg: OpenAIChatChoice) -> LearningModeOutput:
        """
        理解学习模式的输出.
        """
        yaml_str = cls._unpack_yaml_in_text(msg.as_chat_msg().content)
        if yaml_str.startswith("yaml"):
            yaml_str = yaml_str[4:]
        data = yaml.safe_load(yaml_str)
        return LearningModeOutput(**data)

    @classmethod
    def get_prompter(cls, ctx: Context) -> OpenAIChatCompletion:
        return ctx.container.force_fetch(OpenAIChatCompletion)

    @classmethod
    def say(cls, ctx: Context, this: Thought, text: str) -> None:
        msg = SpheroCommandMessage.new(Say(text=text))
        ctx.send_at(this).output(msg)

    def cache_command(self, command_name: str, commands: List[Dict], is_ability: bool) -> None:
        self._cached_commands.indexes[command_name] = commands.copy()
        if is_ability:
            self._cached_commands.abilities.append(command_name)
            self._cached_commands.abilities = list(set(self._cached_commands.abilities))
        self._save_cached()

    def ability_names(self) -> str:
        return "|".join(self._cached_commands.abilities)

    def parse_direction(
            self,
            ctx: Context,
            direction: str,
            prompter: OpenAIChatCompletion,
            from_user: bool = False,
    ) -> Tuple[List[Dict], bool]:  # 返回加工过的消息, 和 解析失败的信息.
        """
        理解一个指令, 并将它解析为 SpheroCommandMessage
        """
        if self.config.use_command_cache and direction in self._cached_commands.indexes:
            command_data = self._cached_commands.indexes[direction].copy()
            return command_data, True
        else:
            stage = CtxTool.current_think_stage(ctx)
            abilities = self.ability_names()
            prompt = self.config.format_parse_command_instruction(
                commands_instruction(),
                abilities,
                stage.desc(ctx),
            )
            session_id = ctx.input.trace.session_id
            chat_context = [
                OpenAIChatMsg(
                    role=OpenAIChatMsg.ROLE_SYSTEM,
                    content=prompt,
                ),
                OpenAIChatMsg(
                    role=OpenAIChatMsg.ROLE_ASSISTANT,
                    name="ghost",
                    content=f"命令是: {direction}",
                ),
                OpenAIChatMsg(
                    role=OpenAIChatMsg.ROLE_ASSISTANT,
                    name="ghost",
                    content=f"yaml 输出为:",
                )
            ]
            resp = prompter.chat_completion(
                session_id,
                chat_context,
                config_name=self.config.use_llm_config,
            )
            if not resp:
                return [], False

            content = resp.as_chat_msg().content
            if content.startswith(self.config.invalid_command_mark):
                return [], False
            commands = self._unpack_commands_in_direction(content)
            result = []
            for cmd in commands:
                loop = loop_check(cmd)
                if loop is None:
                    loop = ability_check(cmd)
                if loop is not None:
                    # 递归解析.
                    commands, ok = self.parse_direction(
                        ctx,
                        loop.direction,
                        prompter,
                        from_user,
                    )
                    if not ok:
                        return [], False
                    loop.commands = commands
                    result.append(loop.to_command_data())
                else:
                    result.append(cmd)
            if self.config.use_command_cache:
                self._cached_commands.indexes[direction] = result.copy()
            self._save_cached()
            return result, True

    def _save_cached(self):
        filename = self._cached_commands_file()
        with open(filename, 'w') as f:
            yaml.safe_dump(self._cached_commands.dict(), f, allow_unicode=True)

    @classmethod
    def _unpack_commands_in_direction(cls, text: str) -> List[Dict]:
        """
        解析 llm 通过 yaml 形式返回的 commands.
        """
        text = cls._unpack_yaml_in_text(text)
        command_data = yaml.safe_load(text)
        if isinstance(command_data, str):
            return [Say(text=command_data).dict()]
        if not isinstance(command_data, list):
            raise RuntimeError(f"invalid ghost response: {text}")
        return command_data

    @classmethod
    def _unpack_yaml_in_text(cls, text: str) -> str:
        if text.startswith("`") or text.endswith("`"):
            text.strip("`")
        sections = text.split("```")
        if len(sections) == 3:
            text = sections[1]
        return text
