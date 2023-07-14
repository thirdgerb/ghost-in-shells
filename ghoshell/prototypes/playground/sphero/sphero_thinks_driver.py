from typing import List

import yaml

from ghoshell.framework.ghost import GhostBootstrapper
from ghoshell.ghost import Ghost, ThinkDriver, ThinkMeta, Think, MindsetNotFoundException
from ghoshell.prototypes.playground.sphero.mode_learn import SpheroLearningModeThink
from ghoshell.prototypes.playground.sphero.mode_runtime import SpheroRuntimeModeThink
from ghoshell.prototypes.playground.sphero.mode_simple import SpheroSimpleCommandModeThink
from ghoshell.prototypes.playground.sphero.sphero_ghost_configs import SpheroGhostConfig
from ghoshell.prototypes.playground.sphero.sphero_ghost_core import SpheroGhostCore, SpheroCommandsCache


class SpheroGhostBootstrapper(GhostBootstrapper):

    def __init__(self, relative_config_path: str = "sphero/config.yaml"):
        self.relative_config_path = relative_config_path

    def bootstrap(self, ghost: Ghost):
        config_filename = ghost.config_path.rstrip("/") + "/" + self.relative_config_path.lstrip("/")
        with open(config_filename) as f:
            config_data = yaml.safe_load(f)
            config = SpheroGhostConfig(**config_data)
            driver = SpheroThinkDriver(ghost.runtime_path, config)
            ghost.mindset.register_driver(driver)
            for meta in driver.to_metas():
                ghost.mindset.register_meta(meta)


class SpheroThinkDriver(ThinkDriver):

    def __init__(self, runtime_path: str, config: SpheroGhostConfig):
        self.app_runtime_path = runtime_path
        self.config = config
        self._cached_commands: SpheroCommandsCache = SpheroCommandsCache()
        self._core = SpheroGhostCore(self.app_runtime_path, config)

    def driver_name(self) -> str:
        return self.config.driver_name

    def from_meta(self, meta: ThinkMeta) -> "Think":
        match meta.id:
            case self.config.simple_mode.name:
                return SpheroSimpleCommandModeThink(self._core)
            case self.config.learn_mode.name:
                return SpheroLearningModeThink(self._core)
            case self.config.runtime_mode.name:
                return SpheroRuntimeModeThink(self._core)
            case _:
                raise MindsetNotFoundException(f"think {meta.id} not found")

    def to_metas(self) -> List[ThinkMeta]:
        result = []
        modes = [
            self.config.simple_mode.name,
            self.config.learn_mode.name,
            self.config.runtime_mode.name,
        ]
        for think_name in modes:
            result.append(ThinkMeta(
                id=think_name,
                kind=self.driver_name(),
            ))
        return result
