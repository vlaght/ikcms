from iktomi.cli.base import Cli as _Cli

class Cli(_Cli):
    name = None

    def __init__(self, App, Cfg):
        assert self.name
        self.App = App
        self.Cfg = Cfg

    def create_cfg(self, custom_cfg_path=None, **kwargs):
        cfg = self.Cfg()
        cfg.update_from_py(custom_cfg_path)
        cfg.update(kwargs)
        return cfg

    def create_app(self, **kwargs):
        cfg = self.create_cfg(**kwargs)
        return self.App(cfg)


