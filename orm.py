from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm import ColumnProperty, RelationshipProperty
from sqlalchemy import sql, func


class ItemNotFound(Exception):
    pass


def model_to_mapper(model, mapper_cls):
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
    return Mapper(model.__table__, relations)


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

    async def select_by_query(self, conn, query, keys=None):
        ids = []
        for row in await conn.execute(query):
            ids.append(row[self.table.c.id])
        return await self.select_by_ids(conn, ids, keys)

    async def select_by_ids(self, conn, ids, keys=None):
        table_keys, relation_keys = self.div_keys(keys)
        table_keys.add('id')
        q = sql.select([self.table.c[key] for key in table_keys])
        q = q.where(self.table.c.id.in_(ids))
        item_by_id = {}
        for row in await conn.execute(q):
            item = dict(row)
            item_by_id[row['id']] = item

        items = []
        for id in ids:
            if id not in item_by_id:
                raise ItemNotFound(id)
            items.append(item_by_id[id])
        # load relations
        for key in relation_keys:
            rows = await self.relations[key].load(conn, ids)
            for id, value in rows.items():
                item_by_id[id][key] = value
        return items

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

    async def update(self, conn, item, keys=None):
        assert 'id' in item
        item = item.copy()
        table_keys, relation_keys = self.div_keys(keys)
        table_values = {key: item[key] for key in table_keys}
        relation_values = {key: item[key] for key in relation_keys}

        q = sql.update(self.table).values(**table_values)
        q = q.where(self.table.c.id==item['id'])
        result = await conn.execute(q)
        if result.rowcount != 1:
            raise ItemNotFound(item['id'])
        for key in self.relation_keys:
            relation = self.relations[key]
            await relation.store(conn, item['id'], item[key])
        return item

    async def delete(self, conn, id):
        q = sql.delete(self.table).where(self.table.c.id==id)
        result = await conn.execute(q)
        if result.rowcount != 1:
            raise ItemNotFound(id)
        for key in self.relation_keys:
            relation = self.relations[key]
            await relation.delete(conn, id, item[key])


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


