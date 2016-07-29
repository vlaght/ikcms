from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm import ColumnProperty
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy import sql
from sqlalchemy.sql.base import _generative
from sqlalchemy import func

from . import exc


__all__ = [
    'Registry',
    'InternalCore',
    'InternalI18n',
    'InternalPublication',
    'Core',
    'I18n',
    'Publication',
    'Mapper',
    'I18nMapper',
    'PubMapper',
    'I18nPubMapper',
]

class Query(sql.Select):

    def __init__(self, mapper, *args, **kwargs):
        self.mapper = mapper
        super().__init__([self.mapper.c['id']], *args, **kwargs)

    def id(self, *ids):
        if len(ids) == 1:
            return self.where(self.mapper.c['id']==ids[0])
        else:
            return self.where(self.mapper.c['id'].in_(ids))

    def filter_by(self, **kwargs):
        q = self
        for key, value in kwargs.items():
            q = q.where(self.mapper.c[key]==value)
        return q

    async def select_items(self, session, keys=None):
        return await self.mapper.select_items(
            session,
            self,
            keys=keys,
        )

    async def insert_item(self, session, values, keys=None):
        return await self.mapper.insert_item(
                session,
                self,
                values=values,
                keys=keys,
        )

    async def update_item(self, session, item_id, values, keys=None):
        return await self.mapper.update_item(
            session,
            self,
            item_id=item_id,
            values=values,
            keys=keys,
        )

    async def delete_item(self, session, item_id):
        return await self.mapper.delete_item(
                session,
                self,
                item_id,
        )

    async def count_items(self, session):
        return await self.mapper.count_items(
            session,
            self,
        )


class Registry(dict):

    def __init__(self, metadata):
        self.metadata = metadata
        for key in metadata:
            self[key] = {}


class InternalBase:

    async def select_items(self, session, query, keys=None):
        raise NotImplementedError

    async def insert_item(self, session, query, values, keys=None):
        raise NotImplementedError

    async def update_item(self, session, query, item_id, values, keys=None):
        raise NotImplementedError

    async def delete_item(self, session, query, item_id):
        raise NotImplementedError

    async def count_items(self, session, query):
        raise NotImplementedError



class InternalCore(InternalBase):

    def __init__(self, mappers, name, table, relations, db_id):
        self.mappers = mappers
        self.name = name
        self.table = table
        self.relations = relations
        self.db_id = db_id
        self.c = dict(self.table.c, **self.relations)
        self.table_keys = self.get_table_keys()
        self.relation_keys = self.get_relation_keys()
        assert not self.table_keys.intersection(self.relation_keys)
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

    def get_table_keys(self):
        return set(self.table.c.keys())

    def get_relation_keys(self):
        return set(self.relations.keys())

    async def select_items(self, session, query, keys=None):
        ids = await self._select_ids(session, query)
        if ids:
            return await self._load_items(session, ids, keys)
        else:
            return []

    async def insert_item(self, session, query, values, keys=None):
        keys = keys or list(values.keys())
        assert set(keys).issubset(self.allowed_keys)
        table_keys, relation_keys = self.div_keys(keys)
        table_values = {key: values[key] for key in table_keys}
        relation_values = {key: values[key] for key in relation_keys}

        query = sql.insert(self.table).values([table_values])
        result = await session.execute(query)
        item = dict(values, id=result.lastrowid)
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
        query = sql.update(self.table).values(**table_values)
        query = query.where(self.c['id']==item_id)
        result = await session.execute(query)
        item_id = values.get('id', item_id)
        for key, value in relation_values.items():
            await self.relations[key].store(session, item_id, value)
        return dict(values, id=item_id)

    async def delete_item(self, session, query, item_id):
        await self._exists_check(session, query, item_id)
        query = sql.delete(self.table).where(self.c['id']==item_id)
        for key in self.relation_keys:
            await self.relations[key].delete(session, item_id)
        await session.execute(query)

    async def count_items(self, session, query):
        query = query.with_only_columns([sql.func.count(self.c['id'])])
        result = await session.execute(query)
        row = await result.fetchone()
        return row[0]

    async def _select_ids(self, session, query):
        rows = list(await session.execute(query))
        return [row[self.c['id']] for row in rows]

    async def _load_items(self, session, ids, keys=None):
        table_keys, relation_keys = self.div_keys(keys)
        table_keys.add('id')
        query = sql.select([self.c[key] for key in table_keys])
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



class InternalI18n(InternalBase):

    def __init__(self, langs, internal_mappers, lang):
        assert len(internal_mappers) == len(langs)
        assert lang in langs
        self.langs = langs
        self.internal_mappers = dict(zip(langs, internal_mappers))
        self.lang = lang
        self.internal = self.internal_mappers[lang]

    async def select_items(self, session, query,keys=None):
        return await self.internal.select_items(session, query, keys=keys)

    async def insert_item(self, session, query, values, keys=None):
        for lang in self.langs:
            await self.internal_mappers[lang].insert_item(
                session, query, values, keys=keys)

    async def update_item(self, session, query, item_id, values, keys=None):
        return await self.internal.update_item(
            session, query, item_id, values, keys=None)

    async def delete_item(self, session, query, item_id):
        for lang in self.langs:
            await self.internal_mappers[lang].delete_item(
                session, query, item_id)

    async def count_items(self, session, query):
        return await self.internal.count_items(session, query)


class InternalPublication(InternalBase):

    def __init__(self, db_ids, internal_mappers, db_id):
        assert len(db_ids) == len(internal_mappers) == 2
        assert db_id in db_ids
        self.db_ids = db_ids
        self.internal_mappers = dict(zip(db_ids, internal_mappers))
        self.db_id = db_id
        self.internal = self.internal_mappers[db_id]

    async def select_items(self, session, query,keys=None):
        return await self.internal.select_items(session, query, keys=keys)

    async def insert_item(self, session, query, values, keys=None):
        for db_id in [self.src_db_id, self.dest_db_id]:
            await self.internal_mappers[db_id].insert_item(
                session, query, values, keys=keys)

    async def update_item(self, session, query, item_id, values, keys=None):
        return await self.internal.update_item(
            session, query, item_id, values, keys=None)

    async def delete_item(self, session, query, item_id):
        for lang in self.langs:
            await self.internal_mappers[lang].delete_item(
                session, query, item_id)

    async def count_items(self, session, query):
        return await self.internal.count_items(session, query)

    async def publish(self, session, query, item_id):
        pass



class Core:

    internal_core_class = InternalCore
    internal_core_props = [
        'db_id',
        'table',
        'relations',
        'table_keys',
        'relation_keys',
        'c',
        'div_keys',
        'allowed_keys',
        'select_items',
        'insert_item',
        'update_item',
        'delete_item',
        'count_items',
    ]
    name = None
    query_class = Query

    def __init__(self, registry, internal):
        assert self.name
        self.registry = registry
        self.internal_core = internal
        for prop in self.internal_core_props:
            setattr(self, prop, getattr(internal, prop))

    def query(self):
        return self.query_class(self)

    @classmethod
    def create_table(cls, registry, **kwargs):
        raise NotImplementedError

    @classmethod
    def create_relations(cls, registry, **kwargs):
        return {}

    @classmethod
    def create_internals(cls, registry, **kwargs):
        table = cls.create_table(registry, **kwargs)
        relations = cls.create_relations(registry, **kwargs)
        return [cls.internal_core_class(
            registry,
            cls.name,
            table,
            relations,
            kwargs['db_id'],
        )]

    @classmethod
    def register_mappers(cls, registry, mappers):
        for mapper in mappers:
            registry[mapper.db_id][mapper.name] = mapper

    @classmethod
    def create(cls, registry, **kwargs):
        internals = cls.create_internals(registry, **kwargs)
        mappers = [cls(registry, internal) for internal in internals]
        cls.register_mappers(registry, mappers)

    @classmethod
    def from_model(cls, registry, name, models):
        mapper_cls = type('ModelMapper', (cls,), {
            'name': name,
            'create_table': classmethod(lambda cls, registry, **kwargs: \
                get_model_table(kwargs['model'])
            ),
            'create_relations': classmethod(lambda cls, registry, **kwargs: \
                get_model_relations(kwargs['model'])
            ),

        })
        for model in models:
            mapper_cls.create(
                registry,
                model=model,
                db_id=get_model_db_id(registry, model),
            )


class I18nMixin:

    internal_i18n_class = InternalI18n
    internal_i18n_props = [
        'lang',
    ]
    langs = ['ru', 'en']

    def __init__(self, mappers, internal):
        super().__init__(mappers, internal.internal)
        self.internal_i18n = internal
        for prop in self.internal_i18n_props:
            setattr(self, prop, getattr(internal, prop))

    @classmethod
    def create_internals(cls, mappers, **kwargs):
        assert 'lang' not in kwargs
        child_internals = [
            super().create_internals(mappers, lang=lang, **kwargs)
            for lang in cls.langs
        ]
        internals = []
        for child_internal in zip(*child_internals):
            for lang in cls.langs:
                internals.append(
                    cls.inernal_i18n_class(cls.langs, child_internal, lang),
                )
        return internals

    @classmethod
    def register_mappers(cls, mappers, new_mappers):
        for mapper in new_mappers:
            mappers[mapper.db_id][mapper.lang][mapper.name] = mapper


class PublicationMixin:

    db_ids = ['admin', 'front']

    internal_pub_class = InternalPublication
    internal_pub_props = [
        'publish',
    ]

    def __init__(self, mappers, internal):
        super().__init__(mappers, internal.internal)
        self.internal_pub = internal
        for prop in self.internal_pub_props:
            setattr(self, prop, getattr(internal, prop))

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
                    cls.inernal_pub_class(cls.db_ids, child_internal, db_id),
                )
        return internals




#class I18n:
#
#    langs = ['ru', 'en']
#    common_keys = []
#
#    def __init__(self, mappers, **kwargs):
#        self.lang = kwargs.pop('lang')
#        super().__init__(mappers, **kwargs)
#
#    @classmethod
#    def create(cls, mappers, **kwargs):
#        for lang in cls.langs:
#            mappers[self.db_id][lang] = cls(mapper, **kwargs)
#
#    async def insert(self, conn, item):
#        cur_lang_item = item
#        other_lang_item = {key: value for key, value in item.items() \
#            if key in self.common_keys}
#
#        for lang in self.langs:
#            lang_item = (lang == self.lang) and cur_lang_item or other_lang_item
#
#            result = await super(I18n, self.mappers[self.db_id][lang]).\
#                insert(conn, lang_item)
#            if lang == self.langs[0]:
#                cur_lang_item['id'] = result['id']
#                other_lang_item['id'] = result['id']
#        return cur_lang_item
#
#
#    async def delete(self, conn, id, query=None):
#        for lang in self.langs[1:]:
#            await super(I18n, self.mappers[self.db_id][lang]).delete(conn, id)
#        await super(I18n, self.mappers[self.db_id][self.langs[0]]).\
#            delete(conn, id)
#



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
        s = sql.select([self.rel_local_field, self.rel_remote_field]) \
            .where(self.rel_local_field.in_(ids))
        if self.order_field:
            s = s.order_by(self.order_field)
        return s

    def delete_query(self, local_id):
        return sql.delete(self.rel_table) \
            .where(self.rel_local_field == local_id)

    def insert_query(self, local_id, remote_id, order=None):
        values = {
            self.rel_local_field.key: local_id,
            self.rel_remote_field.key: remote_id,
        }
        if order:
            values[self.order_field.key] = order
        return sql.insert(self.rel_table).values(**values)


class Base(Core):
    pass

class I18n(I18nMixin, Base):
    pass

class Pub(PublicationMixin, Base):
    pass

class I18nPub(PublicationMixin, I18nMixin, Base):
    pass



def get_model_db_id(registry, model):
    model_meta = model.__table__.metadata
    for db_id, meta in registry.metadata.items():
        if meta == model_meta:
            return db_id

def get_model_table(model):
    return model.__table__

def get_model_relations(model):
    relations = {}
    for name in dir(model):
        attr = getattr(model, name)
        if isinstance(attr, InstrumentedAttribute):
            prop = attr.property
            if isinstance(prop, ColumnProperty):
                pass
            elif isinstance(prop, RelationshipProperty):
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
