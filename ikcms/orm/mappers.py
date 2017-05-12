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
        super().__init__()
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

    def set_mapper(self, path, mapper):
        if isinstance(path, str):
            parts = path.split('.')
        elif isinstance(path, [list, tuple]):
            parts = path
        #XXX
        parts, name = parts[:-1], parts[-1]
        d = self
        for part in parts:
            d = d.setdefault(part, {})
        d[name] = mapper

    def get_mapper(self, path):
        if isinstance(path, str):
            parts = path.split('.')
        elif isinstance(path, [list, tuple]):
            parts = path
        #XXX
        parts, name = parts[:-1], parts[-1]
        d = self
        for part in parts:
            d = d[part]
        return d[name]


    @classmethod
    def from_db_ids(cls, db_ids):
        return cls({db_id: sa.MetaData() for db_id in db_ids})


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

    async def schema_initialize(self, session):
        pass

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

    async def select_first_item(self, session, query, keys=None):
        items = await self.select_items(session, query.limit(1), keys)
        return items and items[0] or None

    async def insert_item(self, session, values, keys=None):
        keys = keys or list(values.keys())
        assert set(keys).issubset(self.allowed_keys), \
            'Keys {} not allowed. Allowed keys={}'.format(
                set(keys).difference(self.allowed_keys), self.allowed_keys)
        table_keys, relation_keys = self.div_keys(keys)
        table_values = {key: values[key] for key in table_keys}
        relation_values = {key: values[key] for key in relation_keys}

        # set defaults, aio engine don't do it
        for key, column in self.table.c.items():
            if key not in table_values and column.default is not None:
                if column.default.is_callable:
                    table_values[key] = column.default.arg(self)
                else:
                    table_values[key] = column.default.arg
        query = sa.sql.insert(self.table).values(table_values)
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
        query = query.where(self.c['id'] == item_id)
        result = await session.execute(query)
        item_id = values.get('id', item_id)
        for key, value in relation_values.items():
            await self.relations[key].store(session, item_id, value)
        return dict(values, id=item_id)

    async def delete_item(self, session, query, item_id):
        await self._exists_check(session, query, item_id)
        await self.delete_item_by_id(session, item_id)

    async def delete_item_by_id(self, session, item_id):
        query = sa.sql.delete(self.table).where(self.c['id'] == item_id)
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
            query = query.where(self.c['id'] == ids[0])
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
            registry.set_mapper(mapper.id, mapper)
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

    async def fill(self, session, query, data, str_path):
        paths = str_path.split('.')
        if isinstance(data, dict):
            data = [data]
        while paths:
            tp = self._get_list_type(data)
            if tp == list:
                tmp_data = []
                for item in data:
                    tmp_data += item
                data = tmp_data
            elif tp == dict:
                path = paths.pop(0)
                prev_data = data
                data = [x[path] for x in data]
            else:
                raise TypeError(tp)

        tp = self._get_list_type(data)
        if tp == list:
            await self._fill_lists(session, query, data)
        else:
            await self._fill_dicts(session, query, prev_data, path)

    def _get_list_type(self, items_list):
        data = [item for item in items_list if item]
        tps = set([type(item) for item in items_list])
        if len(tps) > 1:
            raise TypeError(tps)
        return tps.pop()

    async def _fill_lists(self, session, query, data):
        ids = set()
        for items_list in data:
            ids.update(items_list)
        items = await query.id(ids).select_items(session)
        items_by_id = {item['id']: item for item in items}
        for items_list in data:
            items = [items_by_id[x] for x in items_list]
            items_list.clear()
            items_list.extend(items)

    async def _fill_dicts(self, session, query, data, key):
        ids = set()
        for items_dict in data:
            ids.add(items_dict[key])
        items = await query.id(ids).select_items(session)
        items_by_id = {id: item for item in items}
        for items_dict in data:
            items_dict[key] = items_by_id[items_dict[key]]


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
        if self.lang == self.langs[0]:
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
        return self.i18n_base_query().where(self.c['state'] != self.STATE_ABSENT)

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
                if keys is None:
                    common_keys = set(self.common_keys)
                else:
                    common_keys = set(self.common_keys).intersection(keys)
                lang_keys = common_keys.union({'id', 'state'})
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
            if lang == self.lang:
                result = await update_item(session, item_id, values, keys)
            elif common_keys:
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

    def private_query(self):
        return self.pub_base_query().filter_by(state=self.STATE_PRIVATE)

    def public_query(self):
        return self.pub_base_query().filter_by(state=self.STATE_PUBLIC)

    @cached_property
    def pub_mappers(self):
        return [self.get_mapper(db_id=db_id) for db_id in self.db_ids]

    async def insert_item(self, session, values, keys=None):
        assert self.db_id == self.db_ids[0], \
            'Insert denied for "{}" mapper'.format(self.db_id)
        values = dict(values)
        insert_item = self.pub_base_insert_item
        self.set_private_state(values)
        item = await insert_item(session, values, keys=keys)
        values = {'id': item['id']}
        self.set_private_state(values)
        insert_item = self.pub_mappers[1].pub_base_insert_item
        await insert_item(session, values, keys={'id', 'state'})
        return item

    async def delete_item(self, session, query, item_id):
        assert self.db_id == self.db_ids[0], \
            'Delete denied for "{}" mapper'.format(self.db_id)
        await super().delete_item(session, query, item_id)

    async def delete_item_by_id(self, session, item_id):
        for mapper in self.pub_mappers:
            await mapper.pub_base_delete_item_by_id(session, item_id)

    async def pub_base_delete_item_by_id(self, session, item_id):
        await super().delete_item_by_id(session, item_id)

    async def publish(self, session, query, item_id):
        assert self.db_id == self.db_ids[0], \
            'Publish denied for "{}" mapper'.format(self.db_id)
        assert self.db_id == self.db_ids[0]
        await self._exists_check(session, query, item_id)
        admin_mapper = self.pub_mappers[0]
        items = await admin_mapper.select_items(session, query.id(item_id))
        admin_item = items[0]
        assert admin_item['state'] == 'private', \
            'Item id="{}" is not private'.format(admin_item['id'])
        values = admin_item
        self.set_public_state(admin_item)
        await admin_mapper.update_item_by_id(session, item_id, values, ['state'])
        front_mapper = self.pub_mappers[1]
        await front_mapper.update_item_by_id(
            session,
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
        result = []
        for db_id in cls.db_ids:
            mappers = super().create_mappers(registry, db_id=db_id, **kwargs)
            result.extend(mappers)
        return result


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
        states.add(cls.STATE_NORMAL)
        states.add(cls.STATE_DELETED)
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

