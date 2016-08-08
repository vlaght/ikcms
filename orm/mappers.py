import sqlalchemy as sa
from iktomi.utils import cached_property

from .query import Query, PubQuery
from . import exc


__all__ = [
    'Registry',
    'CoreImpl',
    'I18nImpl',
    'PubImpl',
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


class BaseImpl:

    async def select_items(self, session, query, keys=None):
        raise NotImplementedError

    async def insert_item(self, session, values, keys=None):
        raise NotImplementedError

    async def update_item(self, session, query, item_id, values, keys=None):
        raise NotImplementedError

    async def delete_item(self, session, query, item_id):
        raise NotImplementedError

    async def count_items(self, session, query):
        raise NotImplementedError



class CoreImpl(BaseImpl):

    def __init__(self, table, relations):
        self.table = table
        self.relations = relations
        self.c = dict(self.table.c, **self.relations)
        self.table_keys = set(self.table.c.keys())
        self.relation_keys = set(self.relations.keys())
        self.allowed_keys = self.table_keys.union(self.relation_keys)

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
            await self.relations[key].store(session, [item])
        return item

    async def update_item(self, session, query, item_id, values, keys=None):
        keys = keys or list(values.keys())
        table_keys, relation_keys = self.div_keys(keys)
        table_values = {key: values[key] for key in table_keys}
        relation_values = {key: values[key] for key in relation_keys}
        await self._exists_check(session, query, item_id)
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
            items = await self.relations[key].load(session, sorted_items)
        return sorted_items

    async def _exists_check(self, session, query, item_id):
        ids = await self._select_ids(session, query.filter_by(id=item_id))
        if len(ids) == 0:
            raise exc.ItemNotFoundError(item_id)
        if len(ids) > 1:
            raise exc.OrmError('There are many items with id={}'.format(item_id))



class I18nImpl(BaseImpl):

    STATE_NORMAL = 'normal'
    STATE_ABSENT = 'absent'

    def __init__(self, langs, mappers, lang, child_impl,
            common_keys=None, STATE_NORMAL=None, STATE_ABSENT=None):
        assert len(langs) == len(mappers)
        assert lang in langs
        self.langs = langs
        self.mappers = dict(zip(langs, mappers))
        self.lang = lang
        self.child_impl = child_impl
        self.common_keys = set(common_keys) or set()
        self.STATE_NORMAL = STATE_NORMAL or self.STATE_NORMAL
        self.STATE_ABSENT = STATE_ABSENT or self.STATE_ABSENT

    async def select_items(self, session, query, keys=None):
        return await self.child_impl.select_items(session, query, keys=keys)

    async def insert_item(self, session, values, keys=None):
        results = {}
        values = dict(values)
        for lang in self.langs:
            mapper = self.mappers[lang]
            if lang == self.lang:
                lang_values = dict(values)
                self.set_normal_state(lang_values)
                lang_keys = keys
            else:
                lang_values = dict(values)
                self.set_absent_state(lang_values)
                lang_keys = set(self.common_keys).union({'id', 'state'})
            impl = mapper.i18n_impl.child_impl
            results[lang] = await impl.insert_item(
                session, lang_values, keys=lang_keys)
            values['id'] = results[lang]['id']
        return results[self.lang]


    async def update_item(self, session, query, item_id, values, keys=None):
        assert 'id' not in values or values['id'] == item_id,\
            'Changing item_id not permitted'
        if keys is None:
            common_keys = self.common_keys
        else:
            common_keys = self.common_keys.intersection(keys)
        for lang in self.langs:
            mapper = self.mappers[lang]
            update_item = mapper.i18n_impl.child_impl.update_item
            if lang==self.lang:
                result = await update_item(session, query, item_id, values, keys)
            else:
                await update_item(
                    session,
                    mapper.i18n_base_query(),
                    item_id,
                    values,
                    common_keys,
                )
        return result

    async def delete_item(self, session, query, item_id):
        await self.child_impl._exists_check(session, query, item_id) #XXX
        for lang in self.langs[::-1]:
            mapper = self.mappers[lang]
            impl = mapper.i18n_impl.child_impl
            await impl.delete_item(session, mapper.i18n_base_query(), item_id)


    async def count_items(self, session, query):
        return await self.child_impl.count_items(session, query)

    def set_normal_state(self, values):
        values['state'] = self.STATE_NORMAL

    def set_absent_state(self, values):
        values['state'] = self.STATE_ABSENT

    async def get_version(self, session, item_id, keys=None):
        query = self.mappers[self.lang].i18n_base_query().id(item_id)
        items = await query.select_items(session, keys)
        return items[0]

    async def create_version(self, session, item_id):
        mapper = self.mappers[self.lang]
        query = mapper.absent_query()
        values = {}
        self.set_normal_state(values)
        items = await mapper.i18n_impl.child_impl.update_item(
            session, query, item_id, values, keys=['state'])


class PubImpl(BaseImpl):

    state_private = 'private'
    state_public = 'public'

    def __init__(self, db_ids, mappers, db_id, child_impl):
        assert len(db_ids) == len(mappers) == 2
        assert db_id in db_ids
        self.mappers = dict(zip(db_ids, mappers))
        self.db_ids =db_ids
        self.db_id = db_id
        self.child_impl = child_impl

    async def select_items(self, session, query,keys=None):
        return await self.child_impl.select_items(session, query, keys=keys)

    async def insert_item(self, session, values, keys=None):
        values = dict(values)
        impl = self.mappers[self.db_ids[0]].pub_impl.child_impl
        self.set_private_state(values)
        item = await impl.insert_item(session, values, keys=keys)
        values = {'id': item['id']}
        self.set_private_state(values)
        impl = self.mappers[self.db_ids[1]].pub_impl.child_impl
        await impl.insert_item(session, values, keys={'id', 'state'})
        return item

    async def update_item(self, session, query, item_id, values, keys=None):
        return await self.child_impl.update_item(
            session, query, item_id, values, keys=None)

    async def delete_item(self, session, query, item_id):
        await self.child_impl._exists_check(session, query, item_id) #XXX
        for db_id in self.db_ids:
            mapper = self.mappers[db_id]
            await mapper.pub_impl.child_impl.delete_item(
                session, mapper.pub_base_query(), item_id)

    async def count_items(self, session, query):
        return await self.child_impl.count_items(session, query)

    async def publish(self, session, query, item_id):
        assert self.db_id == self.db_ids[0]
        await self.child_impl._exists_check(session, query, item_id) #XXX
        admin_mapper = self.mappers[self.db_ids[0]]
        items = await admin_mapper.select_items(session, query)
        values = {}
        self.set_public_state(values)
        await admin_mapper.update_item(session, query, item_id, values)
        values = items[0]
        self.set_public_state(values)
        front_mapper = self.mappers[self.db_ids[1]]
        await front_mapper.update_item(
            session,
            front_mapper.query(),
            item_id,
            values,
        )

    def set_private_state(self, values):
        values['state'] = self.state_private

    def set_public_state(self, values):
        values['state'] = self.state_public


class Core:

    core_impl_class = CoreImpl
    name = None
    query_class = Query

    def __init__(self, registry, db_id):
        assert self.name
        self.registry = registry
        self.db_id = db_id

    def get_mapper(self, **kwargs):
        db_id = kwargs.get('db_id', self.db_id)
        name = kwargs.get('name', self.name)
        return self.registry[db_id][name]

    def query(self):
        return self.query_class(self)

    #schema
    @cached_property
    def table(self):
        return self.registry.metadata[self.db_id].tables[self.tablename]

    @cached_property
    def relations(self):
        return self.create_relations()

    @property
    def tablename(self):
        return self.name

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

    # core impl
    @cached_property
    def core_impl(self):
        return self.core_impl_class(self.table, self.relations)

    @property
    def impl(self):
        return self.core_impl

    @property
    def c(self):
        return self.core_impl.c

    @property
    def table_keys(self):
        return self.core_impl.table_keys

    @property
    def relation_keys(self):
        return self.core_impl.relation_keys

    @property
    def allowed_keys(self):
        return self.core_impl.allowed_keys

    def div_keys(self, keys=None):
        return self.core_impl.div_keys(keys)

    async def select_items(self, session, query, keys=None):
        return await self.impl.select_items(session, query, keys)

    async def insert_item(self, session, values, keys=None):
        return await self.impl.insert_item(session, values, keys)

    async def update_item(self, session, query, item_id, values, keys=None):
        return await self.impl.update_item(
            session, query, item_id, values, keys)

    async def delete_item(self, session, query, item_id):
        return await self.impl.delete_item(session, query, item_id)

    async def count_items(self, session, query):
        return await self.impl.count_items(session, query)

    #factory
    @classmethod
    def create_mappers(cls, registry, **kwargs):
        return [cls(registry, **kwargs)]

    @classmethod
    def register_mappers(cls, registry, mappers, create_schema=True):
        for mapper in mappers:
            registry[mapper.db_id][mapper.name] = mapper
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
                'create_realtions': lambda self: get_model_relations(self.model),
            })

            mapper_cls.create(
                registry,
                db_id=get_model_db_id(registry, model),
                create_schema=False,
            )


class I18nMixin:

    STATE_ABSENT = 'absent'
    STATE_NORMAL = 'normal'

    i18n_impl_class = I18nImpl
    langs = ['ru', 'en']
    common_keys = []

    def __init__(self, registry, lang, **kwargs):
        assert lang in self.langs
        super().__init__(registry, **kwargs)
        self.lang = lang

    def get_mapper(self, **kwargs):
        db_id = kwargs.get('db_id', self.db_id)
        lang = kwargs.get('lang', self.lang)
        name = kwargs.get('name', self.name)
        return self.registry[db_id][lang][name]

    def i18n_base_query(self):
        return super().query()

    def query(self):
        return self.i18n_base_query().where(self.c['state']!=self.STATE_ABSENT)

    def absent_query(self):
        return self.i18n_base_query().filter_by(state=self.STATE_ABSENT)

    def get_states(self):
        states = getattr(super(), 'get_states', lambda: set())()
        states.add(self.STATE_NORMAL)
        states.add(self.STATE_ABSENT)
        return states

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

    # i18n impl
    @cached_property
    def i18n_impl(self):
        return self.i18n_impl_class(
            self.langs,
            self.i18n_mappers,
            self.lang,
            super().impl,
            common_keys=self.common_keys,
            STATE_ABSENT=self.STATE_ABSENT,
            STATE_NORMAL=self.STATE_NORMAL,
        )

    @cached_property
    def i18n_mappers(self):
        return [self.get_mapper(lang=lang) for lang in self.langs]

    @property
    def impl(self):
        return self.i18n_impl

    async def get_lang_version(self, session, item_id):
        return await self.i18n_impl.get_version(session, item_id)

    async def create_lang_version(self, session, item_id):
        return await self.i18n_impl.create_version(session, item_id)

    #factory
    @classmethod
    def create_mappers(cls, registry, **kwargs):
        return [cls(registry, lang=lang, **kwargs) for lang in cls.langs]

    @classmethod
    def register_mappers(cls, registry, mappers, create_schema=True):
        for mapper in mappers:
            lang_registry = registry[mapper.db_id].setdefault(mapper.lang, {})
            lang_registry[mapper.name] = mapper
            if create_schema:
                registry.create_schema_mappers.append(mapper)



class PublicationMixin:

    query_class = PubQuery

    STATE_PRIVATE = 'private'
    STATE_PUBLIC = 'public'

    STATE_NORMAL = STATE_PRIVATE

    pub_impl_class = PubImpl
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

    # pub impl
    @cached_property
    def pub_impl(self):
        return self.pub_impl_class(
            self.db_ids,
            self.pub_mappers,
            self.db_id,
            super().impl,
        )

    @cached_property
    def pub_mappers(self):
        return [self.get_mapper(db_id=db_id) for db_id in self.db_ids]

    @property
    def impl(self):
        return self.pub_impl

    def pub_base_query(self):
        return super().query()

    def query(self):
        return self.pub_base_query()

    def public_query(self):
        return self.i18n_base_query().filter_by(state=self.STATE_PUBLIC)

    def publish(self, session, query, item_id):
        return self.pub_impl.publish(session, query, item_id)

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

    async def delete_item(self, session, query, item_id):
        for mapper in self.internal_core.internal_mappers:
            mapper.update_item(
                session,
                query,
                item_id,
                {'state': self.DELETED_STATE},
            )

    @classmethod
    def get_states(cls):
        states = getattr(super(), 'get_states', lambda: {})()
        states.add(STATE_NORMAL)
        states.add(STATE_DELETED)
        return states


class M2MRelation:

    def __init__(self, local_field,
                 rel_local_field, rel_remote_field,
                 remote_field,
                 order_field=None):
        self.local_field = local_field
        self.rel_local_field = rel_local_field
        self.rel_remote_field = rel_remote_field
        self.remote_field = remote_field
        self.local_table = local_field.table
        self.rel_table = rel_local_field.table
        self.remote_table = remote_field.table
        self.order_field = order_field

    async def load(self, conn, ids):
        result = {}
        for row in await conn.execute(self.select_query(ids)):
            result.setdefault(row[self.rel_local_field], []).\
                append(row[self.rel_remote_field])
        return result

    async def store(self, conn, id, value):
        await conn.execute(self.delete_query(id))
        for num, rel_id in enumerate(value):
            order = self.order_field and (num+1) or None
            await conn.execute(self.insert_query(id, rel_id, order=order))

    async def delete(self, conn, id):
        await conn.execute(self.delete_query(id))

    def select_query(self, ids):
        s = sa.sql.select([self.rel_local_field, self.rel_remote_field]) \
            .where(self.rel_local_field.in_(ids))
        if self.order_field:
            s = s.order_by(self.order_field)
        return s

    def delete_query(self, local_id):
        return sa.sql.delete(self.rel_table) \
            .where(self.rel_local_field == local_id)

    def insert_query(self, local_id, remote_id, order=None):
        values = {
            self.rel_local_field.key: local_id,
            self.rel_remote_field.key: remote_id,
        }
        if order:
            values[self.order_field.key] = order
        return sa.sql.insert(self.rel_table).values(**values)


class Base(Core):
    pass

class I18n(I18nMixin, Base):
    pass

class Pub(PublicationMixin, Base):
    pass

class I18nPub(PublicationMixin, I18nMixin, Base):
    pass


class I18nPubMarkDeleted(
    PublicationMixin,
    I18nMixin,
    MarkDeletedMixin,
    Base,
    ):
        pass


def get_model_db_id(registry, model):
    model_meta = model.__table__.metadata
    for db_id, meta in registry.metadata.items():
        if meta == model_meta:
            return db_id


def get_model_relations(model):
    relations = {}
    for name in dir(model):
        attr = getattr(model, name)
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
                    relations[prop.key] = M2MRelation(
                        local1, remote1, remote2, local2
                    )

                return {}
    return relations
