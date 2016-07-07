from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm import ColumnProperty, RelationshipProperty
from sqlalchemy import sql, func


class ItemNotFound(Exception):
    pass


def model_to_mapper(model, mapper_cls, db_id=None):
    db_id = db_id or mapper_cls.db_id
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
    return mapper_cls(model.__table__, relations, db_id=db_id)


class Mapper:

    db_id = 'main'

    def __init__(self, table, relations, db_id=None):
        self.db_id = db_id or self.db_id
        self.table = table
        self.relations = relations
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

    def query(self):
        return sql.select([self.table.c.id])

    async def select(self, conn, ids=None, query=None, keys=None):
        db_ids = await self._select_ids(conn, ids=ids, query=query)
        if ids is not None:
            db_ids = ids
        # load items form db
        return  await self._select_items(conn, db_ids, keys=keys)

    async def insert(self, conn, item):
        assert set(item).issubset(self.allowed_keys)
        item = item.copy()
        table_keys, relation_keys = self.div_keys(item.keys())

        table_values = {key: item[key] for key in table_keys}
        relation_values = {key: item[key] for key in relation_keys}

        q = sql.insert(self.table).values([table_values])
        result = await conn.execute(q)
        item['id'] = result.lastrowid
        # store relations
        for key, value in relation_values.items():
            relation = self.relations[key]
            await relation.store(conn, id, value)
        return item

    async def update(self, conn, item_id, item, query=None, keys=None):
        item = item.copy()
        table_keys, relation_keys = self.div_keys(keys)
        table_values = {key: item[key] for key in table_keys}
        relation_values = {key: item[key] for key in relation_keys}

        await self._select_ids(conn, ids=[item_id], query=query)
        q = sql.update(self.table).values(**table_values)
        q = q.where(self.table.c.id==item_id)
        result = await conn.execute(q)
        if result.rowcount != 1:
            raise ItemNotFound(item_id)
        for key, value in relation_values.items():
            relation = self.relations[key]
            await relation.store(conn, item_id, value)
        item['id'] = item_id
        return item

    async def delete(self, conn, id, query=None):
        db_ids = await self._select_ids(conn, ids=[id], query=query)
        q = sql.delete(self.table).where(self.table.c.id==db_ids[0])
        result = await conn.execute(q)
        if result.rowcount != 1:
            raise ItemNotFound(id)
        for key in self.relation_keys:
            relation = self.relations[key]
            await relation.delete(conn, id)

    async def count(self, conn, query):
        query = query.with_only_columns([sql.func.count(self.table.c.id)])
        result = await conn.execute(query)
        row = await result.fetchone()
        return row[0]

    async def _select_ids(self, conn, ids=None, query=None):
         # load ids from db
        if query is None:
            query = self.query()
        if ids:
            query = query.where(self.table.c.id.in_(ids))
        db_ids = []
        for row in await conn.execute(query):
            db_ids.append(row[self.table.c.id])
        # all id found check
        if ids:
            notfound = set(ids).difference(set(db_ids))
            if notfound:
                raise ItemNotFound(*list(notfound))
        return db_ids

    async def _select_items(self, conn, ids, keys=None):
        table_keys, relation_keys = self.div_keys(keys)
        table_keys.add('id')
        q = sql.select([self.table.c[key] for key in table_keys])
        item_by_id = {}
        for row in await conn.execute(q):
            item_by_id[row['id']] = dict(row)
        # sort and check items
        items = [item_by_id[id] for id in ids]
        notfound = set(ids).difference(set(item_by_id.keys()))
        if notfound:
            raise ItemNotFound(*list(notfound))
        # load relations
        for key in relation_keys:
            rows = await self.relations[key].load(conn, ids)
            for id, value in rows.items():
                item_by_id[id][key] = value
        return items


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


