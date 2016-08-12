import sqlalchemy as sa
from iktomi.utils import cached_property

from .query import Query, PubQuery
from . import exc
from . import relations


__all__ = [
    'Registry',
    'Core',
    'I18nMixin',
    'PublicationMixin',
    'Base',
    'I18n',
    'Pub',
    'I18nPub',
]


class Registry(dict):

    def __init__(self, metadata):
        self.metadata = metadata
        for key in metadata:
            self[key] = {}
        self.create_schema_mappers = []

    def create_schema(self):
        mappers = []
        for mapper in self.create_schema_mappers:
            mapper.create_table()

        for mapper in self.create_schema_mappers:
            for relation in mapper.relations.values():
                relation.create_tables()

    def set_id(self, id, mapper):
        id_parts = isinstance(id, str) and id.split('.') or id
        d = self
        id_parts, name = id_parts[:-1], id_parts[-1]
        for id_part in id_parts:
            d = d.setdefault(id_part, {})
        d[name] = mapper

    def get_id(self, id, mapper):
        id_parts = isinstance(id, str) and id.split('.') or id
        d = self
        id_parts, name = id_parts[:-1], id_parts[-1]
        for id_part in id_parts:
            d = d[id_part]
        return d[name]


class Core:

    name = None
    query_class = Query

    def __init__(self, registry, db_id):
        assert self.name
        self.registry = registry
        self.db_id = db_id

    @cached_property
    def id(self):
        return '.'.join([self.db_id, self.name])

    @property
    def tablename(self):
        return self.name

    @cached_property
    def table(self):
        return self.registry.metadata[self.db_id].tables[self.tablename]

    @cached_property
    def relations(self):
        return self.create_relations()

    def get_mapper(self, **kwargs):
        db_id = kwargs.get('db_id', self.db_id)
        name = kwargs.get('name', self.name)
        return self.registry[db_id][name]

    def create_table(self):
        return sa.Table(
            self.tablename,
            self.registry.metadata[self.db_id],
            *(self.create_system_columns() + self.create_columns())
        )

    def create_id_column(self):
        return sa.Column('id', sa.Integer, primary_key=True, autoincrement=True)

    def create_system_columns(self):
        return [self.create_id_column()]

    def create_columns(self):
        return []

    def create_relations(self):
        return {}

    @property
    def c(self):
        return dict(self.table.c, **self.relations)

    @property
    def table_keys(self):
        return set(self.table.c.keys())

    @property
    def relation_keys(self):
        return set(self.relations.keys())

    @property
    def allowed_keys(self):
        return self.table_keys.union(self.relation_keys)

    def query(self):
        return self.query_class(self)
 
    def div_keys(self, keys=None):
        if keys is None:
            keys = self.allowed_keys
        else:
            keys = set(keys)
            error_keys = keys - self.allowed_keys
            assert not error_keys, 'Unknown fields {}'.format(error_keys)
        table_keys = keys.intersection(self.table_keys)
        relation_keys = keys.intersection(self.relation_keys)
        return table_keys, relation_keys

    async def select_items(self, session, query, keys=None):
        ids = await self._select_ids(session, query)
        if ids:
            return await self._load_items(session, ids, keys)
        else:
            return []

    async def insert_item(self, session, values, keys=None):
        keys = keys or list(values.keys())
        assert set(keys).issubset(self.allowed_keys), \
            'Keys {} not allowed. Allowed keys={}'.format(
                set(keys).difference(self.allowed_keys), self.allowed_keys)
        table_keys, relation_keys = self.div_keys(keys)
        table_values = {key: values[key] for key in table_keys}
        relation_values = {key: values[key] for key in relation_keys}

        query = sa.sql.insert(self.table).values([table_values])
        result = await session.execute(query)
        item = dict(values)
        if values.get('id') is None:
            item['id'] = result.lastrowid
        # store relations
        for key in relation_keys:
            await self.relations[key].store(session, item['id'], values[key])
        return item

    async def update_item(self, session, query, item_id, values, keys=None):
        await self._exists_check(session, query, item_id)
        return await self.update_item_by_id(session, item_id, values, keys)

    async def update_item_by_id(self, session, item_id, values, keys=None):
        keys = keys or list(values.keys())
        table_keys, relation_keys = self.div_keys(keys)
        table_values = {key: values[key] for key in table_keys}
        relation_values = {key: values[key] for key in relation_keys}
        query = sa.sql.update(self.table).values(**table_values)
        query = query.where(self.c['id']==item_id)
        result = await session.execute(query)
        item_id = values.get('id', item_id)
        for key, value in relation_values.items():
            await self.relations[key].store(session, item_id, value)
        return dict(values, id=item_id)

    async def delete_item(self, session, query, item_id):
        await self._exists_check(session, query, item_id)
        await self.delete_item_by_id(session, item_id)

    async def delete_item_by_id(self, session, item_id):
        query = sa.sql.delete(self.table).where(self.c['id']==item_id)
        for key in self.relation_keys:
            await self.relations[key].delete(session, item_id)
        await session.execute(query)

    async def count_items(self, session, query):
        query = query.with_only_columns([sa.func.count(self.c['id'])])
        result = await session.execute(query)
        row = await result.fetchone()
        return row[0]

    async def _select_ids(self, session, query):
        rows = list(await session.execute(query))
        return [row[self.c['id']] for row in rows]

    async def _load_items(self, session, ids, keys=None):
        table_keys, relation_keys = self.div_keys(keys)
        table_keys.add('id')
        query = sa.sql.select([self.c[key] for key in table_keys])
        if len(ids) == 1:
            query = query.where(self.c['id']==ids[0])
        else:
            query = query.where(self.c['id'].in_(ids))
        rows = list(await session.execute(query))
        items = [dict(row) for row in rows]
        item_by_id = {item['id']: item for item in items}
        sorted_items = [item_by_id[id] for id in ids]\
        # load relations
        for key in relation_keys:
            result = await self.relations[key].load(session, item_by_id.keys())
            for id, value in result.items():
                item_by_id[id][key] = value
        return sorted_items

    async def _exists_check(self, session, query, item_id):
        ids = await self._select_ids(session, query.filter_by(id=item_id))
        if len(ids) == 0:
            raise exc.ItemNotFoundError(item_id)
        if len(ids) > 1:
            raise exc.OrmError('There are many items with id={}'.format(item_id))

    #factory
    @classmethod
    def create_mappers(cls, registry, **kwargs):
        return [cls(registry, **kwargs)]

    @classmethod
    def register_mappers(cls, registry, mappers, create_schema=True):
        for mapper in mappers:
            registry.set_id(mapper.id, mapper)
            if create_schema:
                registry.create_schema_mappers.append(mapper)

    @classmethod
    def create(cls, registry, create_schema=True, **kwargs):
        mappers = cls.create_mappers(registry, **kwargs)
        cls.register_mappers(registry, mappers, create_schema)
        return mappers

    @classmethod
    def from_model(cls, registry, models, name=None):
        for model in models:
            mapper_cls = type('ModelMapper', (cls,), {
                'name': name or model.__name__,
                'model': model,
                'create_relations': lambda self: get_model_relations(self),
            })

            mapper_cls.create(
                registry,
                db_id=get_model_db_id(registry, model),
                create_schema=False,
            )


class I18nMixin:

    STATE_ABSENT = 'absent'
    STATE_NORMAL = 'normal'

    langs = ['ru', 'en']
    common_keys = []

    def __init__(self, registry, lang, **kwargs):
        assert lang in self.langs
        super().__init__(registry, **kwargs)
        self.lang = lang

    @cached_property
    def id(self):
        return '.'.join([self.db_id, self.lang, self.name])

    # schema
    def create_id_column(self):
        if self.lang==self.langs[0]:
            return sa.Column(
                'id', sa.Integer, primary_key=True, autoincrement=True)
        else:
            return sa.Column(
                'id',
                sa.Integer,
                sa.ForeignKey(
                    self.get_mapper(lang=self.langs[0]).c['id'],
                    ondelete='cascade',
                ),
                primary_key=True,
                autoincrement=False,
            )

    def create_state_column(self):
        return sa.Column(
            'state',
            sa.Enum(*self.get_states()),
            nullable=False,
        )

    def create_system_columns(self):
        return [
            self.create_id_column(),
            self.create_state_column(),
        ]

    @property
    def tablename(self):
        return '{}{}'.format(self.name, self.lang.capitalize())

    #i18n methods
    def get_mapper(self, **kwargs):
        db_id = kwargs.get('db_id', self.db_id)
        lang = kwargs.get('lang', self.lang)
        name = kwargs.get('name', self.name)
        return self.registry[db_id][lang][name]

    def get_states(self):
        states = getattr(super(), 'get_states', lambda: set())()
        states.add(self.STATE_NORMAL)
        states.add(self.STATE_ABSENT)
        return states

    def query(self):
        return self.i18n_base_query().where(self.c['state']!=self.STATE_ABSENT)

    def absent_query(self):
        return self.i18n_base_query().filter_by(state=self.STATE_ABSENT)

    async def insert_item(self, session, values, keys=None):
        results = {}
        values = dict(values)
        for lang in self.langs:
            mapper = self.i18n_mappers[lang]
            if lang == self.lang:
                lang_values = dict(values)
                self.set_normal_state(lang_values)
                lang_keys = keys
            else:
                lang_values = dict(values)
                self.set_absent_state(lang_values)
                lang_keys = set(self.common_keys).union({'id', 'state'})
            insert_item = mapper.i18n_base_insert_item
            results[lang] = await insert_item(session, lang_values, lang_keys)
            values['id'] = results[lang]['id']
        return results[self.lang]

    async def update_item_by_id(self, session, item_id, values, keys=None):
        assert 'id' not in values or values['id'] == item_id,\
            'Changing item_id not permitted'
        if keys is None:
            common_keys = set(self.common_keys)
        else:
            common_keys = set(self.common_keys).intersection(keys)
        for lang in self.langs:
            mapper = self.i18n_mappers[lang]
            update_item = mapper.i18n_base_update_item_by_id
            if lang==self.lang:
                result = await update_item(session, item_id, values, keys)
            else:
                await update_item(
                    session,
                    item_id,
                    values,
                    common_keys,
                )
        return result

    async def delete_item_by_id(self, session, item_id):
        for lang in self.langs[::-1]:
            mapper = self.i18n_mappers[lang]
            await mapper.i18n_base_delete_item_by_id(session, item_id)

    def set_normal_state(self, values):
        values['state'] = self.STATE_NORMAL

    def set_absent_state(self, values):
        values['state'] = self.STATE_ABSENT

    def i18n_base_query(self):
        return super().query()

    @cached_property
    def i18n_mappers(self):
        return {lang: self.get_mapper(lang=lang) for lang in self.langs}

    async def i18n_base_insert_item(self, session, values, keys=None):
        return await super().insert_item(session, values, keys)

    async def i18n_base_update_item_by_id(self, session, item_id, values,
            keys=None):
        return await super().update_item_by_id(session, item_id, values, keys)

    async def i18n_base_delete_item_by_id(self, session, item_id):
        return await super().delete_item_by_id(session, item_id)

    async def i18n_get_version(self, session, item_id, keys=None):
        query = self.i18n_mappers[self.lang].i18n_base_query().id(item_id)
        await self._exists_check(session, query, item_id)
        items = await query.select_items(session, keys)
        return items[0]

    async def i18n_create_version(self, session, item_id):
        query = self.absent_query()
        values = {}
        self.set_normal_state(values)
        await self.update_item(session, query, item_id, values, keys=['state'])

    #factory
    @classmethod
    def create_mappers(cls, registry, **kwargs):
        return [cls(registry, lang=lang, **kwargs) for lang in cls.langs]


class PublicationMixin:

    query_class = PubQuery

    STATE_PRIVATE = 'private'
    STATE_PUBLIC = 'public'

    STATE_NORMAL = STATE_PRIVATE

    db_ids = ['admin', 'front']

    def query(self):
        return super().query().where(self.c['state']!=self.PRIVATE)

    def public_query(self):
        return super().query().filter_by(state=self.PUBLIC)

    def get_states(self):
        states = getattr(super(), 'get_states', lambda: set())()
        states.add(self.STATE_PRIVATE)
        states.add(self.STATE_PUBLIC)
        return states

    # schema
    def create_state_column(self):
        return sa.Column(
            'state',
            sa.Enum(*self.get_states()),
            nullable=False,
        )

    def create_system_columns(self):
        return [
            self.create_id_column(),
            self.create_state_column(),
        ]

    # pub methods
    def pub_base_query(self):
        return super().query()

    def query(self):
        return self.pub_base_query()

    def public_query(self):
        return self.pub_base_query().filter_by(state=self.STATE_PUBLIC)

    @cached_property
    def pub_mappers(self):
        return [self.get_mapper(db_id=db_id) for db_id in self.db_ids]

    async def insert_item(self, session, values, keys=None):
        values = dict(values)
        insert_item = self.pub_mappers[0].pub_base_insert_item
        self.set_private_state(values)
        item = await insert_item(session, values, keys=keys)
        values = {'id': item['id']}
        self.set_private_state(values)
        insert_item = self.pub_mappers[1].pub_base_insert_item
        await insert_item(session, values, keys={'id', 'state'})
        return item

    async def delete_item(self, session, query, item_id):
        await self._exists_check(session, query, item_id)
        for mapper in self.pub_mappers:
            await mapper.pub_base_delete_item(
                session, mapper.pub_base_query(), item_id)

    async def publish(self, session, query, item_id):
        assert self.db_id == self.db_ids[0]
        await self._exists_check(session, query, item_id)
        admin_mapper = self.pub_mappers[0]
        items = await admin_mapper.select_items(session, query)
        values = {}
        self.set_public_state(values)
        await admin_mapper.update_item(session, query, item_id, values)
        values = items[0]
        self.set_public_state(values)
        front_mapper = self.pub_mappers[1]
        await front_mapper.update_item(
            session,
            front_mapper.query(),
            item_id,
            values,
        )

    def set_private_state(self, values):
        values['state'] = self.STATE_PRIVATE

    def set_public_state(self, values):
        values['state'] = self.STATE_PUBLIC

    async def pub_base_insert_item(self, session, values, keys=None):
        return await super().insert_item(session, values, keys)

    async def pub_base_delete_item(self, session, query, item_id):
        return await super().delete_item(session, query, item_id)

    #factory
    @classmethod
    def create_mappers(cls, registry, **kwargs):
        return [cls(registry, db_id=db_id, **kwargs) for db_id in cls.db_ids]

    @classmethod
    def create_internals(cls, mappers, **kwargs):
        child_internals = [
            super().create_internals(mappers, db_id=db_id, **kwargs) \
            for db_id in cls.db_ids
        ]
        internals = []
        for child_internal in zip(*child_internals):
            for db_id in cls_db_ids:
                internals.append(
                    cls.internal_pub_class(
                        cls.db_ids,
                        child_internal,
                        db_id,
                        STATE_PRIVATE=cls.STATE_PRIVATE,
                        STATE_PUBLIC=cls.STATE_PUBLIC,
                    ),
                )
        return internals


class MarkDeletedMixin:

    STATE_NORMAL = 'normal'
    STATE_DELETED = 'deleted'

    async def delete_item_by_id(self, session, item_id):
        for mapper in self.internal_core.internal_mappers:
            mapper.update_item_by_id(
                session,
                item_id,
                {'state': self.DELETED_STATE},
                ['state'],
            )

    @classmethod
    def get_states(cls):
        states = getattr(super(), 'get_states', lambda: {})()
        states.add(STATE_NORMAL)
        states.add(STATE_DELETED)
        return states


class Base(Core):
    pass

class I18n(I18nMixin, Base):
    pass

class Pub(PublicationMixin, Base):
    pass

class I18nPub(PublicationMixin, I18nMixin, Base):
    pass


class I18nPubMD(
    PublicationMixin,
    I18nMixin,
    MarkDeletedMixin,
    Core,
):
        pass


def get_model_db_id(registry, model):
    model_meta = model.__table__.metadata
    for db_id, meta in registry.metadata.items():
        if meta == model_meta:
            return db_id


def get_model_relations(mapper):
    relations_dict = {}
    for name in dir(mapper.model):
        attr = getattr(mapper.model, name)
        if isinstance(attr, sa.orm.attributes.InstrumentedAttribute):
            prop = attr.property
            if isinstance(prop, sa.orm.ColumnProperty):
                pass
            elif isinstance(prop, sa.orm.RelationshipProperty):
                if prop.secondaryjoin is None:
                    pass
                else:
                    local1, remote1 = prop.local_remote_pairs[0]
                    local2, remote2 = prop.local_remote_pairs[1]
                    order_field = remote1.table.c.get('order')
                    # argument is class
                    remote_name = getattr(prop.argument, '__name__', None)
                    # argument is classname
                    if remote_name is None:
                        remote_name = getattr(prop.argument, 'arg', None)
                    relations_dict[prop.key] = relations.M2M(
                        mapper,
                        remote_name,
                        ordered='order' in remote1.table.c,
                    )
                return {}
    return relations_dict

