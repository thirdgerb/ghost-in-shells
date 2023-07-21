from typing import Dict, Iterator

import yaml

from ghoshell.framework.ghost import GhostBootstrapper
from ghoshell.ghost import Ghost, ThinkDriver, Meta, Think, MindNotImplementedError
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
            ghost.mindset.register_meta_driver(driver)


class SpheroThinkDriver(ThinkDriver):

    def __init__(self, runtime_path: str, config: SpheroGhostConfig):
        self.app_runtime_path = runtime_path
        self.config = config
        self._cached_commands: SpheroCommandsCache = SpheroCommandsCache()
        self._core = SpheroGhostCore(self.app_runtime_path, config)

    def meta_kind(self) -> str:
        return self.config.driver_name

    def from_meta(self, meta: Meta) -> "Think":
        if meta.id == self.config.simple_mode.name:
            return SpheroSimpleCommandModeThink(self._core)
        if meta.id == self.config.learn_mode.name:
            return SpheroLearningModeThink(self._core)
        if meta.id == self.config.runtime_mode.name:
            return SpheroRuntimeModeThink(self._core)
        raise MindNotImplementedError(f"think {meta.id} not found")

    def preload_metas(self) -> Iterator[Meta]:
        result = []
        modes = [
            self.config.simple_mode.name,
            self.config.learn_mode.name,
            self.config.runtime_mode.name,
        ]
        for think_name in modes:
            result.append(Meta(
                id=think_name,
                kind=self.meta_kind(),
            ))
        return result

    def meta_config_json_schema(self) -> Dict:
        return {}
