from __future__ import absolute_import
import logging

from sqlalchemy.dialects import registry
import ikcms.components.db.sqla

from .query import SphinxQuery


registry.register('sphinxql', 'ikcms.components.sphinx.dialect', 'Dialect')


class Component(ikcms.components.db.sqla.Component):
    name = 'sphinx'
    query_class = SphinxQuery
    xmlpipes = {}

    DEFAULT_SPHINX_URI = 'sphinxql://127.0.0.1:9306/?charset=utf8'
    DEFAULT_SPHINX_PARAMS = {
        'pool_size': 10,
        'max_overflow': 50,
        'pool_recycle': 3600,
    }

    @classmethod
    def create(cls, app):
        uri = getattr(app.cfg, 'SPHINX_URI', cls.DEFAULT_SPHINX_URI)
        params = getattr(app.cfg, 'SPHINX_PARAMS', cls.DEFAULT_SPHINX_PARAMS)
        engine = cls.create_engine('sphinx', uri, params)
        engine.logger = logging.getLogger('sqlalchemy.engine.[sphinx]')
        engines = {'sphinx': engine}
        models = {'sphinx': cls.get_models('sphinx')}
        return cls(app, engines, models)


component = Component.create_cls
