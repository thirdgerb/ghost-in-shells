from __future__ import annotations

import os
from typing import Dict, Iterator

import yaml

from ghoshell.framework.ghost import GhostBootstrapper
from ghoshell.ghost import ThinkDriver, Ghost
from ghoshell.meta import Meta, MC
from ghoshell.prototypes.playground.werewolf.configs import WerewolfGameConfig
from ghoshell.prototypes.playground.werewolf.think import WEREWOLF_GAME_KIND, WerewolfGameThink


# from ghoshell.framework.ghost import


class WerewolfGameDriver(ThinkDriver):

    def __init__(self, config_dir: str):
        self.config_dir = config_dir

    def preload_metas(self) -> Iterator[Meta]:
        for root, ds, fs in os.walk(self.config_dir):
            for fullname in fs:
                filename = self.config_dir.rstrip("/") + "/" + fullname
                if not filename.endswith(".yaml"):
                    continue
                yield self._get_meta_by_filename(filename)

    def _get_meta_by_filename(self, filename) -> Meta:
        with open(filename) as f:
            data = yaml.safe_load(f)
            meta = Meta(
                id=data.get("think"),
                kind=self.meta_kind(),
                config=data,
            )
            return meta

    def meta_kind(self) -> str:
        return WEREWOLF_GAME_KIND

    def meta_config_json_schema(self) -> Dict:
        return WerewolfGameConfig.model_json_schema()

    def from_meta(self, meta: Meta) -> MC:
        config = WerewolfGameConfig(**meta.config)
        return WerewolfGameThink(config)


class WerewolfGameBootstrapper(GhostBootstrapper):

    def __init__(self, relative_config_dir: str = "werewolf"):
        self.relative_config_dir = relative_config_dir

    def bootstrap(self, ghost: Ghost):
        config_dir = ghost.config_path.rstrip("/") + "/" + self.relative_config_dir.lstrip("/")
        driver = WerewolfGameDriver(config_dir)
        ghost.mindset.register_meta_driver(driver)
