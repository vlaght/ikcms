import sqlalchemy as sa
from iktomi.utils import cached_property

__all__ = (
    'M2M',
    'I18nM2M',
)

class M2M:

    order_field_name = 'order'

    def __init__(self, mapper1, mapper_name2, ordered=False, tablename=None):
        self.mapper1 = mapper1
        self.registry = mapper1.registry
        self.db_id = mapper1.db_id
        self.mapper_name1 = mapper1.name
        self.mapper_name2 = mapper_name2
        self.ordered = ordered
        self.tablename = tablename or self.get_tablename()

    def create_tables(self):
        columns = [
            sa.Column(
                self.local_field_name,
                self.mapper1.c['id'].type,
                sa.ForeignKey(self.mapper1.table.c.id, ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                self.remote_field_name,
                self.mapper2.c['id'].type,
                sa.ForeignKey(self.mapper2.table.c.id, ondelete="CASCADE"),
                nullable=False,
            ),
        ]
        if self.ordered:
            columns.append(
                sa.Column('order', sa.Integer, nullable=False, default=0)
            )
        return sa.Table(
            self.tablename,
            self.registry.metadata[self.db_id],
            *columns
        )

    def get_tablename(self):
        return "{}_{}".format(self.mapper_name1, self.mapper_name2)

    @cached_property
    def table(self):
        return self.registry.metadata[self.db_id].tables[self.tablename]

    @cached_property
    def mapper2(self):
        return self.registry[self.db_id][self.mapper_name2]

    @cached_property
    def m(self):
        return self.mapper2

    @cached_property
    def local_field_name(self):
        return '{}_id'.format(self.mapper1.name.lower())

    @cached_property
    def remote_field_name(self):
        return '{}_id'.format(self.mapper2.name.lower())

    @cached_property
    def local_field(self):
        return self.table.c[self.local_field_name]

    @cached_property
    def remote_field(self):
        return self.table.c[self.remote_field_name]

    @cached_property
    def order_field(self):
        return self.table.c[self.order_field_name]

    async def load(self, session, item_ids):
        result = {}
        for row in await session.execute(self.select_query(item_ids)):
            result.setdefault(row[self.local_field], []) \
                .append(row[self.remote_field])
        return result

    async def store(self, session, item_id, value):
        await session.execute(self.delete_query(item_id))
        for num, rel_id in enumerate(value):
            order = self.ordered and (num+1) or None
            await session.execute(
                self.insert_query(item_id, rel_id, order=order))

    async def delete(self, session, item_id):
        await session.execute(self.delete_query(item_id))

    def select_query(self, item_ids):
        s = sa.sql.select([self.local_field, self.remote_field]) \
            .where(self.local_field.in_(item_ids))
        if self.ordered:
            s = s.order_by(self.order_field)
        return s

    def delete_query(self, local_id):
        return sa.sql.delete(self.table).where(self.local_field == local_id)

    def insert_query(self, local_id, remote_id, order=None):
        values = {
            self.local_field_name: local_id,
            self.remote_field_name: remote_id,
        }
        if order:
            values[self.order_field_name] = order
        return sa.sql.insert(self.table).values(**values)


class I18nM2M(M2M):

    def __init__(self, mapper1, mapper_name2, ordered=False, tablename=None):
        super().__init__(
            mapper1,
            mapper_name2,
            ordered=ordered,
            tablename=tablename,
        )
        self.lang = mapper1.lang

    @property
    def get_tablename(self):
        return "{}_{}{}".format(
            self.mapper_name1, self.mapper_name2, self.lang.capitalize())

    @property
    def mapper1(self):
        return self.registry[self.db_id][self.lang][self.mapper_name1]

    @property
    def mapper2(self):
        return self.registry[self.db_id][self.lang][self.mapper_name2]


