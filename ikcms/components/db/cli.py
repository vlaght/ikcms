#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ikcms.cli.base import Cli

class GeneratorCli(Cli):
    name = 'generator'

    def command_run(self, *names):
        app = self.create_app()
        app.db.generate(names)
