# import yaml
#
# from ghoshell.ghost import Ghost
# from ghoshell.ghost_fmk import Bootstrapper
# from ghoshell.prototypes.sphero.sphero_ghost_configs import SpheroGhostConfig
# from ghoshell.prototypes.sphero.sphero_thinks import SpheroThinkDriver
#
#
# class SpheroGhostBootstrapper(Bootstrapper):
#
#     def __init__(self, relative_config_path: str = "sphero/config.yaml"):
#         self.relative_config_path = relative_config_path
#
#     def bootstrap(self, ghost: Ghost):
#         config_filename = ghost.config_path.rstrip("/") + "/" + self.relative_config_path.lstrip("/")
#         with open(config_filename) as f:
#             config_data = yaml.safe_load(f)
#             config = SpheroGhostConfig(**config_data)
#             driver = SpheroThinkDriver(ghost.runtime_path, config)
#             ghost.mindset.register_driver(driver)
#             for meta in driver.to_metas():
#                 ghost.mindset.register_meta(meta)
